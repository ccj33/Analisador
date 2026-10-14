from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

ISO_DT = re.compile(r"^\d{4}-\d{2}-\d{2}T")

from tender_intel.domain.ast import All, AnyOf, Compare, Count, Exists, FactRef, Literal, NodeResult, Not, Unless
from tender_intel.domain.types import Status

BR_TZ = ZoneInfo("America/Sao_Paulo")


def solve(node: Any, facts: dict[str, Any]) -> NodeResult:
    conflicts = facts.get("_conflicts", set())
    if isinstance(node, All):
        results = [solve(arg, facts) for arg in node.args]
        return _combine(results, _kleene_and, "ALL")
    if isinstance(node, AnyOf):
        results = [solve(arg, facts) for arg in node.args]
        return _combine(results, _kleene_or, "ANY")
    if isinstance(node, Not):
        inner = solve(node.arg, facts)
        return NodeResult(_negate(inner.status), f"NOT {inner.reason}", inner.blocking_facts, inner.evidence_ids)
    if isinstance(node, Unless):
        return solve(All((node.body, Not(node.exception))), facts)
    if isinstance(node, Compare):
        return _compare(node, facts, conflicts)
    if isinstance(node, Exists):
        return _exists(node, facts, conflicts)
    if isinstance(node, Count):
        return _count(node, facts, conflicts)
    if isinstance(node, FactRef):
        if node.key in conflicts:
            return NodeResult(Status.CONFLICT.value, f"conflito em {node.key}", (node.key,))
        if node.key not in facts:
            return NodeResult(Status.UNKNOWN.value, f"fato ausente: {node.key}", (node.key,))
        value = facts[node.key]
        if value is True:
            return NodeResult(Status.SATISFIED.value, f"{node.key} é verdadeiro")
        if value is False:
            return NodeResult(Status.UNSATISFIED.value, f"{node.key} é falso", (node.key,))
        return NodeResult(Status.SATISFIED.value, f"{node.key} presente")
    raise TypeError(f"nó AST não suportado: {type(node)}")


def _compare(node: Compare, facts: dict[str, Any], conflicts: set[str]) -> NodeResult:
    left, left_status = _value(node.left, facts, conflicts)
    right, right_status = _value(node.right, facts, conflicts)
    if left_status is not None:
        return left_status
    if right_status is not None:
        return right_status
    ok = _apply_op(node.op, left, right)
    status = Status.SATISFIED if ok else Status.UNSATISFIED
    blocking = () if ok else _fact_keys(node.left, node.right)
    return NodeResult(status.value, f"{left!r} {node.op} {right!r} → {ok}", blocking)


def _exists(node: Exists, facts: dict[str, Any], conflicts: set[str]) -> NodeResult:
    items, status = _collection(node.collection.key, facts, conflicts)
    if status is not None:
        return status
    if not node.where:
        ok = len(items) > 0
        return NodeResult(
            (Status.SATISFIED if ok else Status.UNSATISFIED).value,
            f"EXISTS {node.collection.key} = {len(items)}",
            () if ok else (node.collection.key,),
        )
    matches = [item for item in items if _item_matches(item, node.where)]
    ok = len(matches) > 0
    return NodeResult(
        (Status.SATISFIED if ok else Status.UNSATISFIED).value,
        f"EXISTS {node.collection.key} matches={len(matches)}",
        () if ok else (node.collection.key,),
    )


def _count(node: Count, facts: dict[str, Any], conflicts: set[str]) -> NodeResult:
    items, status = _collection(node.collection.key, facts, conflicts)
    if status is not None:
        return status
    matches = [item for item in items if (node.where is None or _item_matches(item, node.where))]
    ok = _apply_op(node.op, len(matches), node.n)
    return NodeResult(
        (Status.SATISFIED if ok else Status.UNSATISFIED).value,
        f"COUNT {len(matches)} {node.op} {node.n}",
        () if ok else (node.collection.key,),
    )


def _value(side: Any, facts: dict[str, Any], conflicts: set[str]) -> tuple[Any, NodeResult | None]:
    if isinstance(side, Literal):
        return side.value, None
    if isinstance(side, FactRef):
        if side.key in conflicts:
            return None, NodeResult(Status.CONFLICT.value, f"conflito em {side.key}", (side.key,))
        if side.key not in facts:
            return None, NodeResult(Status.UNKNOWN.value, f"fato ausente: {side.key}", (side.key,))
        return facts[side.key], None
    raise TypeError(f"lado não suportado: {type(side)}")


def _collection(key: str, facts: dict[str, Any], conflicts: set[str]) -> tuple[list[Any], NodeResult | None]:
    if key in conflicts:
        return [], NodeResult(Status.CONFLICT.value, f"conflito em {key}", (key,))
    if key not in facts:
        return [], NodeResult(Status.UNKNOWN.value, f"coleção ausente: {key}", (key,))
    value = facts[key]
    if not isinstance(value, list):
        return [], NodeResult(Status.UNSATISFIED.value, f"{key} não é coleção", (key,))
    return value, None


def _item_matches(item: Any, where: Any) -> bool:
    if not isinstance(item, dict):
        return False
    scoped = dict(item)
    scoped["_conflicts"] = set()
    return solve(where, scoped).status == Status.SATISFIED.value


def _apply_op(op: str, left: Any, right: Any) -> bool:
    left_n = _maybe_datetime(left)
    right_n = _maybe_datetime(right)
    if op == "EQ":
        return left_n == right_n
    if op == "NEQ":
        return left_n != right_n
    if op == "GT":
        return left_n > right_n
    if op == "GTE":
        return left_n >= right_n
    if op == "LT":
        return left_n < right_n
    if op == "LTE":
        return left_n <= right_n
    raise ValueError(f"comparação desconhecida: {op}")


def _maybe_datetime(value: Any) -> Any:
    if isinstance(value, str) and ISO_DT.match(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BR_TZ)
        return parsed
    return value


def _fact_keys(*sides: Any) -> tuple[str, ...]:
    keys = []
    for side in sides:
        if isinstance(side, FactRef):
            keys.append(side.key)
    return tuple(keys)


def _negate(status: str) -> str:
    if status == Status.SATISFIED.value:
        return Status.UNSATISFIED.value
    if status == Status.UNSATISFIED.value:
        return Status.SATISFIED.value
    return status


def _kleene_and(statuses: list[str]) -> str:
    if any(s == Status.UNSATISFIED.value for s in statuses):
        return Status.UNSATISFIED.value
    if any(s == Status.CONFLICT.value for s in statuses):
        return Status.CONFLICT.value
    if any(s == Status.UNKNOWN.value for s in statuses):
        return Status.UNKNOWN.value
    if statuses and all(s == Status.NOT_APPLICABLE.value for s in statuses):
        return Status.NOT_APPLICABLE.value
    return Status.SATISFIED.value


def _kleene_or(statuses: list[str]) -> str:
    if any(s == Status.SATISFIED.value for s in statuses):
        return Status.SATISFIED.value
    if any(s == Status.CONFLICT.value for s in statuses):
        return Status.CONFLICT.value
    if any(s == Status.UNKNOWN.value for s in statuses):
        return Status.UNKNOWN.value
    if statuses and all(s == Status.NOT_APPLICABLE.value for s in statuses):
        return Status.NOT_APPLICABLE.value
    return Status.UNSATISFIED.value


def _combine(results: list[NodeResult], combiner, label: str) -> NodeResult:
    status = combiner([r.status for r in results])
    blocking = tuple(key for r in results for key in r.blocking_facts)
    reasons = "; ".join(r.reason for r in results)
    return NodeResult(status, f"{label}: {reasons}", blocking)
