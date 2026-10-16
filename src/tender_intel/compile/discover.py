from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from tender_intel.domain.documents import TenderPackage
from tender_intel.domain.types import EventType

MONTHS = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
DATE = r"(?P<d>\d{1,2})(?:/(?P<m>\d{1,2})/|\s+de\s+(?P<month>" + "|".join(MONTHS) + r")\s+de\s+)(?P<y>\d{4})"
# "Data limite para submissão das propostas 04/12/2026" (cronograma) ou "deverão ser enviadas até 30/11/2026".
# [^\d] impede pular para uma data depois de outra ("Lançamento 14/10/2026 ... submissão 04/12/2026").
SUBMISSION_DEADLINE = re.compile(
    r"limite\s+para\s+(?:a\s+)?(?:submiss|envi)\w*[^\d]{0,60}?" + DATE
    + r"|(?:submetid|submiss|enviad|envio)\w*[^\d]{0,30}?\bat[eé]\b[^\d]{0,30}?" + DATE.replace("?P<", "?P<b"),
    re.IGNORECASE,
)
EXTERNAL_REF = re.compile(
    r"conforme\s+(?:o\s+|a\s+)?(?P<manual>Manual[^.,;\n]+)"
    r"|nos termos d[aeo]\s+(?P<norma>[^.,;\n]+)"
    r"|vide\s+(?P<anexo>Anexo\s+[IVX\d]+)",
    re.IGNORECASE,
)
IMPUGNACAO = re.compile(r"impugna\w*\s+n[aã]o\s+suspende", re.IGNORECASE)
SUPERSEDING = {EventType.RETIFICACAO, EventType.ERRATA}


@dataclass(frozen=True)
class DeadlineHit:
    element_id: str
    document_id: str
    event: str
    iso_date: str
    quote: str
    effective: bool
    superseded_by: str | None


@dataclass(frozen=True)
class ExternalDependency:
    element_id: str
    quote: str
    target: str
    status: str


@dataclass(frozen=True)
class NormativeEffect:
    element_id: str
    effect: str
    quote: str


@dataclass(frozen=True)
class CompileDraft:
    deadlines: tuple[DeadlineHit, ...]
    dependencies: tuple[ExternalDependency, ...]
    effects: tuple[NormativeEffect, ...]
    needs_ocr: tuple[dict[str, object], ...]

    def to_dict(self) -> dict:
        return {
            "deadlines": [asdict(item) for item in self.deadlines],
            "dependencies": [asdict(item) for item in self.dependencies],
            "effects": [asdict(item) for item in self.effects],
            "needs_ocr": [dict(item) for item in self.needs_ocr],
        }


def discover(package: TenderPackage) -> CompileDraft:
    deadlines = _deadlines(package)
    return CompileDraft(
        deadlines=tuple(deadlines),
        dependencies=tuple(_dependencies(package)),
        effects=tuple(_effects(package)),
        needs_ocr=tuple(
            {"document_id": document.id, "pages": list(document.needs_ocr_pages)}
            for document in package.documents
            if document.needs_ocr_pages
        ),
    )


def _deadlines(package: TenderPackage) -> list[DeadlineHit]:
    """Só data que o texto liga ao fim da submissão. Data de lançamento, de impugnação ou de
    um desafio no anexo não é prazo."""
    hits: list[tuple] = []
    for document in package.documents:
        for element in document.elements:
            iso = submission_deadline(element.text)
            if iso:
                hits.append((document, element.id, iso, element.text))
    superseding = [item for item in hits if item[0].event in SUPERSEDING]
    effective_id = superseding[-1][1] if superseding else (hits[-1][1] if hits else None)
    drafted: list[DeadlineHit] = []
    for document, element_id, iso, quote in hits:
        effective = element_id == effective_id
        drafted.append(
            DeadlineHit(
                element_id=element_id,
                document_id=document.id,
                event=document.event.value,
                iso_date=iso,
                quote=quote,
                effective=effective,
                superseded_by=None if effective else effective_id,
            )
        )
    return drafted


def submission_deadline(text: str) -> str | None:
    match = SUBMISSION_DEADLINE.search(text)
    if match is None:
        return None
    parts = match.groupdict()
    day = parts["d"] or parts["bd"]
    year = parts["y"] or parts["by"]
    month_name = (parts["month"] or parts["bmonth"] or "").lower()
    month = int(parts["m"] or parts["bm"]) if (parts["m"] or parts["bm"]) else MONTHS.index(month_name) + 1
    return f"{year}-{month:02d}-{int(day):02d}"


def _dependencies(package: TenderPackage) -> list[ExternalDependency]:
    found: list[ExternalDependency] = []
    for document in package.documents:
        for element in document.elements:
            match = EXTERNAL_REF.search(element.text)
            if not match:
                continue
            target = next(group.strip() for group in match.groups() if group)
            elsewhere = any(
                other.id != document.id and target.lower() in f"{other.id} {other.path} {other.text}".lower()
                for other in package.documents
            )
            found.append(
                ExternalDependency(
                    element_id=element.id,
                    quote=element.text,
                    target=target,
                    status="LOADED" if elsewhere else "UNRESOLVED",
                )
            )
    return found


def _effects(package: TenderPackage) -> list[NormativeEffect]:
    effects: list[NormativeEffect] = []
    for document in package.documents:
        for element in document.elements:
            if IMPUGNACAO.search(element.text):
                effects.append(
                    NormativeEffect(element.id, "NAO_SUSPENDE_PRAZO", element.text)
                )
    return effects
