from __future__ import annotations

import json
import re
from pathlib import Path

from tender_intel.domain.documents import DocumentElement, SourceDocument, TenderPackage, read_sha256
from tender_intel.domain.types import AuthorityTier, EventType
from tender_intel.ingest.pdf import EXTRACTOR as PDF_EXTRACTOR
from tender_intel.ingest.pdf import read_pdf

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
ITEM_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")


def ingest_package(package_dir: Path) -> TenderPackage:
    manifest = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
    documents = []
    for index, item in enumerate(manifest["documents"], start=1):
        path = package_dir / item["path"]
        document_id = item.get("id", f"doc_{index:03d}")
        if path.suffix.lower() == ".pdf":
            text, elements, needs_ocr = read_pdf(document_id, path)
            extractor = PDF_EXTRACTOR
        else:
            text = path.read_text(encoding="utf-8")
            elements = _elements(document_id, text)
            needs_ocr = ()
            extractor = "text"
        documents.append(
            SourceDocument(
                id=document_id,
                path=str(path),
                authority=AuthorityTier(item["authority"]),
                event=EventType(item["event"]),
                sha256=read_sha256(path),
                text=text,
                elements=elements,
                extractor=extractor,
                needs_ocr_pages=needs_ocr,
            )
        )
    return TenderPackage(id=manifest["id"], title=manifest["title"], documents=documents)


def _elements(document_id: str, text: str) -> tuple[DocumentElement, ...]:
    elements: list[DocumentElement] = []
    section: list[str] = []
    cursor = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        start = cursor
        end = cursor + len(line)
        cursor = end + 1
        heading = HEADING_RE.match(line)
        item = ITEM_RE.match(line)
        if heading:
            section = [heading.group(2).strip()]
            kind = "heading"
            body = heading.group(2).strip()
        elif item:
            section = [*section[:-1], item.group(1)] if section else [item.group(1)]
            kind = "item"
            body = line.strip()
        elif line.strip():
            kind = "paragraph"
            body = line.strip()
        else:
            continue
        elements.append(
            DocumentElement(
                id=f"{document_id}.elm_{line_no:04d}",
                document_id=document_id,
                kind=kind,
                text=body,
                section_path=tuple(section),
                start=start,
                end=end,
            )
        )
    return tuple(elements)
