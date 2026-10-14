from __future__ import annotations

from dataclasses import dataclass

from tender_intel.domain.documents import TenderPackage


@dataclass(frozen=True)
class EvidenceSpan:
    id: str
    element_id: str
    quote: str


@dataclass(frozen=True)
class EvidenceCheck:
    evidence_id: str
    element_id: str
    found: bool
    reason: str


def normalize(text: str) -> str:
    return " ".join(text.split())


def check_span(package: TenderPackage, span: EvidenceSpan) -> EvidenceCheck:
    element = package.element(span.element_id)
    if element is None:
        return EvidenceCheck(span.id, span.element_id, False, "element_id ausente no grafo documental")
    quote = normalize(span.quote)
    haystack = normalize(element.text)
    if quote and quote in haystack:
        return EvidenceCheck(span.id, span.element_id, True, "substring encontrada no elemento")
    if quote and quote in normalize(package.full_text()):
        return EvidenceCheck(span.id, span.element_id, False, "quote existe no pacote, mas não neste element_id")
    return EvidenceCheck(span.id, span.element_id, False, "quote não é substring do documento")
