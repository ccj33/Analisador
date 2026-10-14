from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from tender_intel.domain.types import AuthorityTier, EventType


@dataclass(frozen=True)
class DocumentElement:
    id: str
    document_id: str
    kind: str
    text: str
    section_path: tuple[str, ...]
    start: int
    end: int
    page: int | None = None
    extractor: str = "text"


@dataclass(frozen=True)
class SourceDocument:
    id: str
    path: str
    authority: AuthorityTier
    event: EventType
    sha256: str
    text: str
    elements: tuple[DocumentElement, ...]
    extractor: str = "text"
    needs_ocr_pages: tuple[int, ...] = ()


@dataclass
class TenderPackage:
    id: str
    title: str
    documents: list[SourceDocument] = field(default_factory=list)

    def element(self, element_id: str) -> DocumentElement | None:
        for document in self.documents:
            for element in document.elements:
                if element.id == element_id:
                    return element
        return None

    def full_text(self) -> str:
        return "\n\n".join(document.text for document in self.documents)


def hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def read_sha256(path: Path) -> str:
    return hash_bytes(path.read_bytes())
