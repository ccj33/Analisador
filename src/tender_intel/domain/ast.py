from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FactRef:
    key: str


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class All:
    args: tuple[Any, ...]


@dataclass(frozen=True)
class AnyOf:
    args: tuple[Any, ...]


@dataclass(frozen=True)
class Not:
    arg: Any


@dataclass(frozen=True)
class Unless:
    body: Any
    exception: Any


@dataclass(frozen=True)
class Compare:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Exists:
    collection: FactRef
    where: Any | None = None


@dataclass(frozen=True)
class Count:
    collection: FactRef
    where: Any | None = None
    op: str = "GTE"
    n: int = 1


@dataclass(frozen=True)
class NodeResult:
    status: str
    reason: str
    blocking_facts: tuple[str, ...] = field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)


COMPARE_OPS = {"EQ", "NEQ", "GT", "GTE", "LT", "LTE"}


def node_from_dict(data: dict[str, Any]) -> Any:
    op = data["op"]
    if op == "ALL":
        return All(tuple(node_from_dict(a) for a in data["args"]))
    if op == "ANY":
        return AnyOf(tuple(node_from_dict(a) for a in data["args"]))
    if op == "NOT":
        return Not(node_from_dict(data["arg"]))
    if op == "UNLESS":
        return Unless(node_from_dict(data["body"]), node_from_dict(data["exception"]))
    if op in COMPARE_OPS:
        return Compare(op, _side(data["left"]), _side(data["right"]))
    if op == "EXISTS":
        return Exists(FactRef(data["collection"]["fact"]), node_from_dict(data["where"]) if data.get("where") else None)
    if op == "COUNT":
        return Count(
            FactRef(data["collection"]["fact"]),
            node_from_dict(data["where"]) if data.get("where") else None,
            data.get("compare_op", "GTE"),
            int(data.get("n", 1)),
        )
    if op == "FACT":
        return FactRef(data["key"])
    raise ValueError(f"operador AST desconhecido: {op}")


def _side(data: dict[str, Any]) -> Any:
    if "fact" in data:
        return FactRef(data["fact"])
    if "field" in data:
        return FactRef(data["field"])
    if "literal" in data:
        return Literal(data["literal"])
    raise ValueError(f"lado de comparação inválido: {data}")


def node_to_dict(node: Any) -> dict[str, Any]:
    if isinstance(node, All):
        return {"op": "ALL", "args": [node_to_dict(arg) for arg in node.args]}
    if isinstance(node, AnyOf):
        return {"op": "ANY", "args": [node_to_dict(arg) for arg in node.args]}
    if isinstance(node, Not):
        return {"op": "NOT", "arg": node_to_dict(node.arg)}
    if isinstance(node, Unless):
        return {"op": "UNLESS", "body": node_to_dict(node.body), "exception": node_to_dict(node.exception)}
    if isinstance(node, Compare):
        return {"op": node.op, "left": _side_to_dict(node.left), "right": _side_to_dict(node.right)}
    if isinstance(node, Exists):
        data: dict[str, Any] = {"op": "EXISTS", "collection": {"fact": node.collection.key}}
        if node.where is not None:
            data["where"] = node_to_dict(node.where)
        return data
    if isinstance(node, Count):
        data = {
            "op": "COUNT",
            "collection": {"fact": node.collection.key},
            "compare_op": node.op,
            "n": node.n,
        }
        if node.where is not None:
            data["where"] = node_to_dict(node.where)
        return data
    if isinstance(node, FactRef):
        return {"op": "FACT", "key": node.key}
    raise TypeError(f"nó AST não serializável: {type(node)}")


def _side_to_dict(side: Any) -> dict[str, Any]:
    if isinstance(side, FactRef):
        return {"fact": side.key}
    if isinstance(side, Literal):
        return {"literal": side.value}
    raise TypeError(f"lado não serializável: {type(side)}")


def render_human(node: Any) -> str:
    if isinstance(node, FactRef):
        return node.key
    if isinstance(node, Literal):
        return repr(node.value)
    if isinstance(node, All):
        return " e ".join(f"({render_human(a)})" for a in node.args)
    if isinstance(node, AnyOf):
        return " ou ".join(f"({render_human(a)})" for a in node.args)
    if isinstance(node, Not):
        return f"não ({render_human(node.arg)})"
    if isinstance(node, Unless):
        return f"{render_human(node.body)}, salvo se {render_human(node.exception)}"
    if isinstance(node, Compare):
        return f"{render_human(node.left)} {node.op} {render_human(node.right)}"
    if isinstance(node, Exists):
        clause = f" onde {render_human(node.where)}" if node.where else ""
        return f"existe em {node.collection.key}{clause}"
    if isinstance(node, Count):
        clause = f" onde {render_human(node.where)}" if node.where else ""
        return f"contagem de {node.collection.key}{clause} {node.op} {node.n}"
    return str(node)
