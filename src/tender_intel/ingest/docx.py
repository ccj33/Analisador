from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path

from tender_intel.domain.documents import DocumentElement
from tender_intel.ingest.clauses import Line, segment

EXTRACTOR = "docx-xml"
PARAGRAPH = re.compile(r"<w:p[ >].*?</w:p>|<w:p/>", re.DOTALL)
RUN_TEXT = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>|<w:tab/>|<w:br/>", re.DOTALL)


def read_docx(document_id: str, path: Path) -> tuple[str, tuple[DocumentElement, ...]]:
    """Lê os parágrafos do word/document.xml, incluindo células de tabela. Sem dependência externa."""
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    lines: list[Line] = []
    cursor = 0
    texts = []
    for block in PARAGRAPH.findall(xml):
        text = "".join(_run(match) for match in RUN_TEXT.finditer(block))
        text = " ".join(unescape(text).split())
        if not text:
            continue
        lines.append(Line(text, cursor, cursor + len(text)))
        texts.append(text)
        cursor += len(text) + 1
    # Parágrafo do Word já é unidade: não junta continuação.
    return "\n".join(texts), segment(document_id, lines, EXTRACTOR, join_continuations=False)


def _run(match: re.Match[str]) -> str:
    if match.group(0) == "<w:tab/>":
        return " "
    if match.group(0) == "<w:br/>":
        return " "
    return match.group(1)
