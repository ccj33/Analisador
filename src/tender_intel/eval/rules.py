from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from tender_intel.domain.ast import node_to_dict
from tender_intel.domain.rules import NormativeRule

ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
NUMBER_WORDS = {
    1: ("um ", "uma ", "único", "única"),
    2: ("dois", "duas"),
    3: ("três",),
}
MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def compare_rules(annotated: list[NormativeRule], compiled: list[NormativeRule]) -> dict[str, Any]:
    """Mede o compilador contra a anotação, regra a regra.

    O pareamento é pelo conjunto de fatos que a regra consulta, não pelo id,
    porque o anotador e o compilador não combinam nomes em chamada real.
    """
    pending = list(compiled)
    rows = []
    for gold in annotated:
        match = _take(pending, lambda rule: _expr(rule) == _expr(gold))
        if match is None:
            match = _take(pending, lambda rule: _facts(rule) == _facts(gold))
        if match is None:
            rows.append(_row(gold, None, "OMITTED"))
            continue
        outcome = "MATCH" if _expr(match) == _expr(gold) else "DIFFERENT_LOGIC"
        rows.append(_row(gold, match, outcome))
    for extra in pending:
        rows.append(_row(None, extra, "INVENTED"))

    counts = {name: sum(1 for row in rows if row["outcome"] == name) for name in ("MATCH", "DIFFERENT_LOGIC", "OMITTED", "INVENTED")}
    by_type: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_type.setdefault(row["type"], {"MATCH": 0, "DIFFERENT_LOGIC": 0, "OMITTED": 0, "INVENTED": 0})
        bucket[row["outcome"]] += 1
    ok = counts["OMITTED"] == 0 and counts["INVENTED"] == 0 and counts["DIFFERENT_LOGIC"] == 0
    ok = ok and all(row["evidence_overlap"] and not row["values_missing_from_evidence"] for row in rows if row["outcome"] == "MATCH")
    return {"ok": ok, "counts": counts, "by_type": by_type, "rules": rows}


def values_missing_from_evidence(rule: NormativeRule) -> list[str]:
    """Número ou data que a regra usa tem de aparecer na citação."""
    quotes = " ".join(span.quote for span in rule.evidence)
    missing = []
    for value in _literals(node_to_dict(rule.expression)):
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            if not any(form in quotes for form in _number_forms(value)):
                missing.append(str(value))
        elif isinstance(value, str) and ISO_DATE.match(value):
            year, month, day = (int(part) for part in ISO_DATE.match(value).groups())
            forms = {
                date(year, month, day).strftime("%d/%m/%Y"),
                f"{day}/{month}/{year}",
                value[:10],
                f"{day:02d} de {MONTHS[month - 1]} de {year}",
                f"{day} de {MONTHS[month - 1]} de {year}",
            }
            if not any(form in quotes for form in forms):
                missing.append(value)
    return missing


def _number_forms(value: int | float) -> set[str]:
    """16000000 aparece no edital como 16.000.000,00."""
    forms = {str(value)}
    forms |= set(NUMBER_WORDS.get(value, ()))
    if float(value).is_integer():
        grouped = f"{int(value):,}".replace(",", ".")
        forms |= {grouped, f"{grouped},00"}
    return forms


def _row(gold: NormativeRule | None, got: NormativeRule | None, outcome: str) -> dict[str, Any]:
    reference = gold or got
    overlap = False
    if gold is not None and got is not None:
        overlap = bool({span.element_id for span in gold.evidence} & {span.element_id for span in got.evidence})
    return {
        "outcome": outcome,
        "type": f"{reference.layer.value}/{reference.actor}",
        "annotated_id": gold.id if gold else None,
        "compiled_id": got.id if got else None,
        "facts": sorted(_facts(reference)),
        "evidence_overlap": overlap,
        "values_missing_from_evidence": values_missing_from_evidence(got) if got else [],
    }


def _take(rules: list[NormativeRule], predicate) -> NormativeRule | None:
    for index, rule in enumerate(rules):
        if predicate(rule):
            return rules.pop(index)
    return None


def _expr(rule: NormativeRule) -> str:
    return json.dumps(node_to_dict(rule.expression), sort_keys=True)


def _facts(rule: NormativeRule) -> frozenset[str]:
    keys: set[str] = set()
    _walk(node_to_dict(rule.expression), keys, None)
    return frozenset(keys)


def _walk(node: Any, keys: set[str], literals: list | None) -> None:
    if isinstance(node, dict):
        if "fact" in node and len(node) == 1:
            keys.add(node["fact"])
        if node.get("op") == "FACT":
            keys.add(node["key"])
        if "literal" in node and len(node) == 1 and literals is not None:
            literals.append(node["literal"])
        for value in node.values():
            _walk(value, keys, literals)
    elif isinstance(node, list):
        for value in node:
            _walk(value, keys, literals)


def _literals(node: dict[str, Any]) -> list[Any]:
    found: list[Any] = []
    _walk(node, set(), found)
    return found
