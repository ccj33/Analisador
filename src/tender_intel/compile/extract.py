from __future__ import annotations

import re

from tender_intel.compile.discover import discover
from tender_intel.domain.ast import All, AnyOf, Compare, Exists, FactRef, Literal
from tender_intel.domain.documents import DocumentElement, TenderPackage
from tender_intel.domain.evidence import EvidenceSpan
from tender_intel.domain.rules import NormativeRule
from tender_intel.domain.types import DecisionLayer
from tender_intel.ingest.parsers import TIME_RE

BRAZIL = re.compile(r"sediad[oa]s?\s+no\s+Brasil", re.IGNORECASE)
ICT_LINE = re.compile(r"institui\w+\s+cient[ií]ficas,\s+tecnol[oó]gicas\s+e\s+de\s+inova", re.IGNORECASE)
PRIVATE_ICT = re.compile(r"privad\w+.*ICT\s+p[uú]blica", re.IGNORECASE)
COORDINATOR = re.compile(r"coordenador.*doutor", re.IGNORECASE)
DIRECTORY = re.compile(r"Diret[oó]rio\s+de\s+Institui", re.IGNORECASE)
HOURS_48 = re.compile(r"48\s+horas", re.IGNORECASE)
MERIT = re.compile(r"m[eé]rito", re.IGNORECASE)
MIN_SCORE = re.compile(r"nota\s+m[ií]nima\s+de\s+(\d+)\s*%", re.IGNORECASE)
BRASILIA = re.compile(r"Bras[ií]lia", re.IGNORECASE)
UNCHANGED = re.compile(r"Permanecem\s+inalteradas", re.IGNORECASE)


def compile_rules(package: TenderPackage) -> list[NormativeRule]:
    """Extrai só o que o texto sustenta. Cláusula sem padrão reconhecido não vira regra."""
    elements = [element for document in package.documents for element in document.elements]
    rules: list[NormativeRule] = []

    brazil = _first(elements, lambda text: BRAZIL.search(text) and ICT_LINE.search(text))
    if brazil:
        rules.append(
            _rule(
                "REQ-GEO",
                "Instituição sediada no Brasil",
                "PROPONENT",
                Compare("EQ", FactRef("organization.country"), Literal("BR")),
                (_span("EV-GEO", brazil, _phrase(brazil.text, BRAZIL)),),
            )
        )

    private = _first(elements, lambda text: bool(PRIVATE_ICT.search(text)))
    if brazil and private:
        rules.append(
            _rule(
                "REQ-INST",
                "ICT pública ou privada associada a ICT pública",
                "PROPONENT",
                _institution_expression(),
                (
                    _span("EV-ICT", brazil, _phrase(brazil.text, ICT_LINE)),
                    _span("EV-PRIV", private),
                ),
                (_span("EV-OR", private, "quando associadas"),),
            )
        )
    elif brazil:
        rules.append(
            _rule(
                "REQ-INST",
                "Proponente é ICT",
                "PROPONENT",
                Compare("EQ", FactRef("organization.type"), Literal("ICT")),
                (_span("EV-ICT", brazil, _phrase(brazil.text, ICT_LINE)),),
            )
        )

    coordinator = _first(elements, lambda text: bool(COORDINATOR.search(text)))
    if coordinator:
        rules.append(
            _rule(
                "REQ-COORD",
                "Coordenador com doutorado",
                "COORDINATOR",
                Compare("EQ", FactRef("coordinator.has_phd"), Literal(True)),
                (_span("EV-PHD", coordinator),),
            )
        )

    directory = _first(elements, lambda text: bool(DIRECTORY.search(text) and HOURS_48.search(text)))
    if directory:
        rules.append(
            _rule(
                "REQ-DI",
                "Diretório de Instituições ativo há 48 horas",
                "PROPONENT",
                Compare("EQ", FactRef("organization.di_active_48h"), Literal(True)),
                (_span("EV-DI", directory, _phrase(directory.text, HOURS_48)),),
            )
        )

    deadline = _deadline_rule(package, elements)
    if deadline:
        rules.append(deadline)

    merit = _first(elements, lambda text: bool(MERIT.search(text) and MIN_SCORE.search(text)))
    if merit:
        score = int(MIN_SCORE.search(merit.text).group(1))
        rules.append(
            _rule(
                "REQ-MERIT",
                "Nota mínima de mérito por critério",
                "PROJECT",
                Compare("GTE", FactRef("project.merit_min_pct"), Literal(score)),
                (_span("EV-MERIT", merit, _phrase(merit.text, MIN_SCORE)),),
                layer=DecisionLayer.MERIT,
            )
        )
    return rules


def _deadline_rule(package: TenderPackage, elements: list[DocumentElement]) -> NormativeRule | None:
    draft = discover(package)
    effective = next((item for item in draft.deadlines if item.effective), None)
    if effective is None:
        return None
    element = package.element(effective.element_id)
    if element is None or not BRASILIA.search(element.text):
        return None
    clock = TIME_RE.search(element.text)
    if clock is None:
        return None
    literal = f"{effective.iso_date}T{int(clock.group(1)):02d}:{clock.group(2)}:00-03:00"
    relations = []
    for previous in draft.deadlines:
        if previous.effective:
            continue
        previous_element = package.element(previous.element_id)
        if previous_element:
            relations.append(_span("EV-OLD", previous_element, previous.quote))
    unchanged = _first(elements, lambda text: bool(UNCHANGED.search(text)))
    if unchanged:
        relations.append(_span("EV-SUP", unchanged, _phrase(unchanged.text, UNCHANGED)))
    return _rule(
        "REQ-DEADLINE",
        "Envio até o prazo vigente",
        "PROPONENT",
        Compare("LTE", FactRef("submission.sent_at"), Literal(literal)),
        (_span("EV-DL", element, effective.quote),),
        tuple(relations),
    )


def _institution_expression() -> AnyOf:
    public = All(
        (
            Compare("EQ", FactRef("organization.type"), Literal("ICT")),
            Compare("EQ", FactRef("organization.legal_nature"), Literal("PUBLIC")),
        )
    )
    private = All(
        (
            Compare("EQ", FactRef("organization.legal_nature"), Literal("PRIVATE")),
            Exists(
                FactRef("project.partners"),
                All(
                    (
                        Compare("EQ", FactRef("type"), Literal("ICT")),
                        Compare("EQ", FactRef("legal_nature"), Literal("PUBLIC")),
                    )
                ),
            ),
        )
    )
    return AnyOf((public, private))


def _rule(
    rule_id: str,
    title: str,
    actor: str,
    expression: object,
    evidence: tuple[EvidenceSpan, ...],
    relation_evidence: tuple[EvidenceSpan, ...] = (),
    layer: DecisionLayer = DecisionLayer.PRE_SUBMISSION,
) -> NormativeRule:
    return NormativeRule(rule_id, title, layer, actor, expression, evidence, relation_evidence)


def _span(span_id: str, element: DocumentElement, quote: str | None = None) -> EvidenceSpan:
    text = quote or element.text
    if " ".join(text.split()) not in " ".join(element.text.split()):
        raise ValueError(f"citação de {span_id} não está em {element.id}")
    return EvidenceSpan(span_id, element.id, text)


def _first(elements: list[DocumentElement], predicate) -> DocumentElement | None:
    return next((element for element in elements if predicate(element.text)), None)


def _phrase(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"padrão ausente em: {text}")
    return match.group(0)
