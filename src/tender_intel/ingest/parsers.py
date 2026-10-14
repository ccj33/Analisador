from __future__ import annotations

import re
from dataclasses import dataclass

from tender_intel.domain.documents import DocumentElement, TenderPackage

CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
MONEY_RE = re.compile(r"R\$\s*[\d.]+,\d{2}")
DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
TIME_RE = re.compile(r"\b(\d{1,2})h(\d{2})\b")
ITEM_RE = re.compile(r"^\d+(?:\.\d+)+")


@dataclass(frozen=True)
class ExtractedValue:
    kind: str
    value: str
    element_id: str
    quote: str


def extract_deterministic(package: TenderPackage) -> list[ExtractedValue]:
    found: list[ExtractedValue] = []
    for document in package.documents:
        for element in document.elements:
            found.extend(_from_element(element))
    return found


def _from_element(element: DocumentElement) -> list[ExtractedValue]:
    text = element.text
    values: list[ExtractedValue] = []
    for match in CNPJ_RE.finditer(text):
        values.append(ExtractedValue("cnpj", match.group(0), element.id, match.group(0)))
    for match in MONEY_RE.finditer(text):
        values.append(ExtractedValue("money", match.group(0), element.id, match.group(0)))
    for match in DATE_RE.finditer(text):
        iso = f"{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
        values.append(ExtractedValue("date", iso, element.id, match.group(0)))
    for match in TIME_RE.finditer(text):
        values.append(ExtractedValue("time", f"{int(match.group(1)):02d}:{match.group(2)}", element.id, match.group(0)))
    if ITEM_RE.match(text):
        values.append(ExtractedValue("item_id", text.split()[0], element.id, text.split()[0]))
    return values
