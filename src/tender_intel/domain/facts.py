from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tender_intel.domain.types import FactSource, Status


@dataclass(frozen=True)
class FactAssertion:
    id: str
    entity_id: str
    key: str
    value: Any
    source_type: FactSource
    source_system: str = "manual"
    as_of: str | None = None
    valid_to: str | None = None
    verification_status: str = "UNVERIFIED"


@dataclass
class FactStore:
    assertions: list[FactAssertion] = field(default_factory=list)

    def current(self) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        conflicts: set[str] = set()
        by_key: dict[str, list[FactAssertion]] = {}
        for assertion in self.assertions:
            by_key.setdefault(assertion.key, []).append(assertion)
        for key, items in by_key.items():
            values = { _freeze(item.value) for item in items }
            if len(values) > 1:
                conflicts.add(key)
                continue
            resolved[key] = items[-1].value
        resolved["_conflicts"] = conflicts
        return resolved

    def status_for_key(self, key: str) -> Status | None:
        current = self.current()
        if key in current.get("_conflicts", set()):
            return Status.CONFLICT
        if key not in current:
            return Status.UNKNOWN
        return None


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def store_from_dict(data: dict[str, Any]) -> FactStore:
    assertions = []
    for raw in data.get("assertions", []):
        assertions.append(
            FactAssertion(
                id=raw["id"],
                entity_id=raw.get("entity_id", "org"),
                key=raw["key"],
                value=raw["value"],
                source_type=FactSource(raw.get("source_type", "USER_DECLARATION")),
                source_system=raw.get("source_system", "manual"),
                as_of=raw.get("as_of"),
                valid_to=raw.get("valid_to"),
                verification_status=raw.get("verification_status", "UNVERIFIED"),
            )
        )
    return FactStore(assertions)
