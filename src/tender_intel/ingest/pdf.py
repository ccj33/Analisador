from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from tender_intel.domain.documents import DocumentElement
from tender_intel.ingest.clauses import Line, drop_repeated, lines_of, segment

EXTRACTOR = "pypdf"


def read_pdf(document_id: str, path: Path) -> tuple[str, tuple[DocumentElement, ...], tuple[int, ...]]:
    """Lê a camada de texto. Página vazia vira needs_ocr, sem OCR automático."""
    reader = PdfReader(str(path))
    chunks: list[str] = []
    lines: list[Line] = []
    needs_ocr: list[int] = []
    cursor = 0
    for page_number, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        body = raw.strip()
        marker = f"## Página {page_number}"
        chunks.append(marker)
        chunks.append(body)
        block = f"{marker}\n{body}\n"
        if not body:
            needs_ocr.append(page_number)
        else:
            lines.extend(lines_of(body, page_number, cursor + len(marker) + 1))
        cursor += len(block)
    # Cláusula quebrada entre linhas ou páginas volta a ser uma só.
    return "\n".join(chunks), segment(document_id, drop_repeated(lines), EXTRACTOR), tuple(needs_ocr)


def write_text_pdf(path: Path, pages: list[list[str]]) -> None:
    """PDF mínimo em WinAnsi, só para testes da camada de texto."""
    objects = _pdf_objects(pages)
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in chunks))
        chunks.append(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_at = sum(len(part) for part in chunks)
    xref = [f"xref\n0 {len(objects) + 1}\n".encode(), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode())
    trailer = (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    path.write_bytes(b"".join(chunks + xref + [trailer]))


def _pdf_objects(pages: list[list[str]]) -> list[bytes]:
    font_number = 3 + len(pages) * 2
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(len(pages)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
    ]
    content_numbers = []
    page_objects = []
    contents = []
    for index, lines in enumerate(pages):
        page_number = 3 + index * 2
        content_number = page_number + 1
        content_numbers.append(content_number)
        stream = _page_stream(lines)
        contents.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
        page_objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_number} 0 R /Resources << /Font << /F1 {font_number} 0 R >> >> >>"
            ).encode()
        )
    for page_object, content in zip(page_objects, contents):
        objects.append(page_object)
        objects.append(content)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    return objects


def _page_stream(lines: list[str]) -> bytes:
    if not lines:
        return b""
    commands = ["BT", "/F1 12 Tf", "72 740 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("0 -18 Td")
        commands.append(f"({_escape(line)}) Tj")
    commands.append("ET")
    return ("\n".join(commands) + "\n").encode("latin-1")


def _escape(text: str) -> str:
    encoded = text.encode("latin-1")
    return encoded.decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
