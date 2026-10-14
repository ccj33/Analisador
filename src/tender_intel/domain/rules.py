from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tender_intel.domain.ast import node_from_dict, node_to_dict
from tender_intel.domain.evidence import EvidenceSpan
from tender_intel.domain.types import DecisionLayer


@dataclass(frozen=True)
class NormativeRule:
    id: str
    title: str
    layer: DecisionLayer
    actor: str
    expression: Any
    evidence: tuple[EvidenceSpan, ...]
    relation_evidence: tuple[EvidenceSpan, ...]
    human_override: str | None = None


def rules_from_dict(data: dict[str, Any]) -> list[NormativeRule]:
    rules = []
    for raw in data.get("rules", []):
        evidence = tuple(
            EvidenceSpan(item["id"], item["element_id"], item["quote"])
            for item in raw.get("evidence", [])
        )
        relation_evidence = tuple(
            EvidenceSpan(item["id"], item["element_id"], item["quote"])
            for item in raw.get("relation_evidence", [])
        )
        rules.append(
            NormativeRule(
                id=raw["id"],
                title=raw["title"],
                layer=DecisionLayer(raw.get("layer", "PRE_SUBMISSION")),
                actor=raw.get("actor", "PROPONENT"),
                expression=node_from_dict(raw["expression"]),
                evidence=evidence,
                relation_evidence=relation_evidence,
                human_override=raw.get("human_override"),
            )
        )
    return rules


def rules_to_dict(rules: list[NormativeRule]) -> dict[str, Any]:
    payload = []
    for rule in rules:
        payload.append(
            {
                "id": rule.id,
                "title": rule.title,
                "layer": rule.layer.value,
                "actor": rule.actor,
                "expression": node_to_dict(rule.expression),
                "evidence": [
                    {"id": span.id, "element_id": span.element_id, "quote": span.quote} for span in rule.evidence
                ],
                "relation_evidence": [
                    {"id": span.id, "element_id": span.element_id, "quote": span.quote}
                    for span in rule.relation_evidence
                ],
            }
        )
    return {"rules": payload}
