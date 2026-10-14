from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Question:
    name: str
    kind: str
    instructions: str
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class Answer:
    name: str
    kind: str
    value: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(frozen=True)
class DecisionResult:
    answers: tuple[Answer, ...]
    provider: str
    model_version: str
    usage: dict[str, Any] = field(default_factory=dict)


class DecisionProvider(Protocol):
    def decide(self, state: dict[str, Any], questions: list[Question]) -> DecisionResult:
        ...


class AbstainProvider:
    """Padrão da v1: o produto funciona sem Jev."""

    model_version = "abstain-0"

    def decide(self, state: dict[str, Any], questions: list[Question]) -> DecisionResult:
        answers = []
        for question in questions:
            if question.kind == "noul":
                answers.append(Answer(question.name, "noul", "unclear", {"yes": 0.5, "no": 0.5}, 0.0))
                continue
            options = question.options or ("unclear",)
            fallback = "unclear" if "unclear" in options or "none" in options else options[0]
            if "none" in options and fallback == "unclear" and "unclear" not in options:
                fallback = "none"
            if "none" in options and "unclear" not in options:
                fallback = "none"
            probs = {option: (1.0 if option == fallback else 0.0) for option in options}
            answers.append(Answer(question.name, question.kind, fallback, probs, 0.0))
        return DecisionResult(tuple(answers), "abstain", self.model_version)


class JevProvider:
    """Adapter pinado. Sem credencial, recua para abstain — Jev não é caminho crítico."""

    model_version = "jev-1.13.0"

    def __init__(self, api_key: str | None = None, inner: DecisionProvider | None = None) -> None:
        self.api_key = api_key
        self.inner = inner or AbstainProvider()

    def decide(self, state: dict[str, Any], questions: list[Question]) -> DecisionResult:
        if not self.api_key:
            return self.inner.decide(state, questions)
        raise NotImplementedError("chamada HTTP Jev entra depois da calibração do gold set")
