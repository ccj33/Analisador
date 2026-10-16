from __future__ import annotations

import re
from dataclasses import dataclass

from tender_intel.domain.documents import DocumentElement

# "3.1.1. Texto", "13. CALENDÁRIO", "2.1 Texto", "1 - OBJETO", "1.1 – A Chamada". Número solto sem
# ponto ("18 meses") não abre cláusula, nem remissão quebrada no início da linha ("4.3 desta Chamada").
NUMBERED = re.compile(
    r"^(?P<num>\d+(?:\.\d+)*)\.\s+\S"
    r"|^(?P<dash>\d+(?:\.\d+)+)\s*[-–]\s*\S|^(?P<dash1>\d+)\s*[-–]\s+[A-ZÀ-Ý]"
    r"|^(?P<multi>\d+(?:\.\d+)+)\s+[A-ZÀ-Ý]"
)
PAGE_NUMBER = re.compile(r"pg\.\s*(\d+)\s*$|^P[áa]gina\s+(\d+)", re.IGNORECASE)
ALINEA = re.compile(r"^(?P<letter>[a-z])[\).]\s+\S")
CHAPTER = re.compile(r"^(CAP[IÍ]TULO|ANEXO)\s+[IVXLC\d]+\b")
# Rodapé/cabeçalho repetido do SEI e numeração de página.
PAGE_NOISE = re.compile(r"/\s*pg\.\s*\d+\s*$|^P[áa]gina\s+\d+(\s+de\s+\d+)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Line:
    text: str
    start: int
    end: int
    page: int | None = None


def segment(document_id: str, lines: list[Line], extractor: str, join_continuations: bool = True) -> tuple[DocumentElement, ...]:
    """Agrupa linhas quebradas pelo PDF em cláusulas.

    Uma cláusula começa em item numerado, alínea, capítulo/anexo ou título em
    caixa alta. Linha que não começa nada continua a cláusula anterior.
    """
    elements: list[DocumentElement] = []
    current: dict | None = None
    section: list[str] = []

    def flush() -> None:
        nonlocal current
        if current is not None:
            elements.append(
                DocumentElement(
                    id=f"{document_id}.elm_{len(elements) + 1:04d}",
                    document_id=document_id,
                    kind=current["kind"],
                    text=" ".join(current["parts"]),
                    section_path=current["section"],
                    start=current["start"],
                    end=current["end"],
                    page=current["page"],
                    extractor=extractor,
                )
            )
        current = None

    for line in lines:
        text = line.text.strip()
        if not text or PAGE_NOISE.search(text):
            continue
        kind, section = _classify(text, section)
        continues_heading = (
            join_continuations
            and current is not None
            and current["kind"] == "heading"
            and kind == "heading"
            and not NUMBERED.match(text)
            and not CHAPTER.match(text)
        )
        # Linha em caixa alta no meio de uma frase ("conforme" / "CRONOGRAMA.") é continuação, não título.
        mid_sentence = (
            kind == "heading"
            and current is not None
            and current["kind"] != "heading"
            and not NUMBERED.match(text)
            and not CHAPTER.match(text)
            and not current["parts"][-1].rstrip().endswith((".", ":", ";", "!", "?"))
        )
        continues_text = join_continuations and current is not None and current["kind"] != "heading" and (kind is None or mid_sentence)
        if continues_heading or continues_text:
            current["parts"].append(text)
            current["end"] = line.end
            continue
        flush()
        current = {
            "kind": kind or "paragraph",
            "parts": [text],
            "section": tuple(section),
            "start": line.start,
            "end": line.end,
            "page": line.page,
        }
    flush()
    return tuple(elements)


def lines_of(text: str, page: int | None = None, offset: int = 0) -> list[Line]:
    lines = []
    cursor = offset
    for raw in text.splitlines():
        lines.append(Line(raw, cursor, cursor + len(raw), page))
        cursor += len(raw) + 1
    return lines


def drop_repeated(lines: list[Line], min_pages: int = 3) -> list[Line]:
    """Cabeçalho/rodapé que se repete em mais da metade das páginas (impressão do SEI, URL, "1/5")."""
    pages = {line.page for line in lines if line.page is not None}
    if len(pages) < min_pages:
        return lines
    seen: dict[str, set[int]] = {}
    for line in lines:
        key = _shape(line.text)
        if key and line.page is not None:
            seen.setdefault(key, set()).add(line.page)
    noise = {key for key, where in seen.items() if len(where) > len(pages) / 2}
    return [line for line in lines if _shape(line.text) not in noise]


def _shape(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.split()))


def paged_lines(text: str) -> list[Line]:
    """Texto extraído de PDF com rodapé "pg. N": a linha herda a página do próximo rodapé."""
    lines = lines_of(text)
    paged: list[Line] = []
    pending: list[Line] = []
    for line in lines:
        pending.append(line)
        match = PAGE_NUMBER.search(line.text.strip())
        if match:
            page = int(match.group(1) or match.group(2))
            paged.extend(Line(item.text, item.start, item.end, page) for item in pending)
            pending = []
    last = (paged[-1].page or 0) + 1 if paged else None
    paged.extend(Line(item.text, item.start, item.end, last) for item in pending)
    return paged


def _classify(text: str, section: list[str]) -> tuple[str | None, list[str]]:
    numbered = NUMBERED.match(text)
    if numbered:
        number = numbered.group("num") or numbered.group("dash") or numbered.group("dash1") or numbered.group("multi")
        return ("heading" if _is_upper(text) or _is_title(text[numbered.end() - 1 :]) else "item"), [number]
    if CHAPTER.match(text):
        return "heading", [text.split(" –")[0].split(" -")[0]]
    alinea = ALINEA.match(text)
    if alinea:
        parent = section[:1]
        return "item", [*parent, alinea.group("letter")]
    if _is_upper(text):
        return "heading", section
    return None, section


def _is_title(rest: str) -> bool:
    """"1 – Objeto", "3.1. Por parte da Proponente": curto e sem pontuação final."""
    return len(rest.split()) <= 6 and not rest.rstrip().endswith((".", ";", ":", ","))


def _is_upper(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 4 or len(text) > 140:
        return False
    return sum(1 for char in letters if char.isupper()) / len(letters) >= 0.8
