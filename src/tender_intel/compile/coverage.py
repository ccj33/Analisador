from __future__ import annotations

from dataclasses import asdict, dataclass

from tender_intel.compile.discover import CompileDraft
from tender_intel.domain.documents import TenderPackage
from tender_intel.domain.rules import NormativeRule

CLAUSE_KINDS = ("item", "paragraph")

RULE = "RULE"
DISCOVERY = "DISCOVERY"
UNCLASSIFIED = "UNCLASSIFIED"


@dataclass(frozen=True)
class ClauseCoverage:
    element_id: str
    document_id: str
    kind: str
    section: str
    text: str
    status: str
    used_by: tuple[str, ...]


def clause_coverage(
    package: TenderPackage, rules: list[NormativeRule], draft: CompileDraft
) -> list[ClauseCoverage]:
    """Toda cláusula lida sai com destino. Cláusula sem destino aparece como UNCLASSIFIED, não some."""
    by_rule: dict[str, list[str]] = {}
    for rule in rules:
        for span in (*rule.evidence, *rule.relation_evidence):
            _add(by_rule, span.element_id, rule.id)
    by_discovery: dict[str, list[str]] = {}
    for item in draft.deadlines:
        _add(by_discovery, item.element_id, f"prazo {item.iso_date}")
    for item in draft.dependencies:
        _add(by_discovery, item.element_id, f"referência {item.target}")
    for item in draft.effects:
        _add(by_discovery, item.element_id, f"efeito {item.effect}")

    clauses = []
    for document in package.documents:
        for element in document.elements:
            if element.kind not in CLAUSE_KINDS:
                continue
            if element.id in by_rule:
                status, used_by = RULE, by_rule[element.id]
            elif element.id in by_discovery:
                status, used_by = DISCOVERY, by_discovery[element.id]
            else:
                status, used_by = UNCLASSIFIED, []
            clauses.append(
                ClauseCoverage(
                    element_id=element.id,
                    document_id=element.document_id,
                    kind=element.kind,
                    section=" > ".join(element.section_path),
                    text=element.text,
                    status=status,
                    used_by=tuple(used_by),
                )
            )
    return clauses


def coverage_counts(clauses: list[ClauseCoverage]) -> dict[str, int]:
    return {
        "clauses": len(clauses),
        "clauses_in_rules": sum(1 for item in clauses if item.status == RULE),
        "clauses_in_discovery": sum(1 for item in clauses if item.status == DISCOVERY),
        "clauses_unclassified": sum(1 for item in clauses if item.status == UNCLASSIFIED),
    }


def clauses_to_dict(clauses: list[ClauseCoverage]) -> list[dict]:
    return [{**asdict(item), "used_by": list(item.used_by)} for item in clauses]


def _add(index: dict[str, list[str]], element_id: str, label: str) -> None:
    labels = index.setdefault(element_id, [])
    if label not in labels:
        labels.append(label)
