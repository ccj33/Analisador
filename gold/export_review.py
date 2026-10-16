"""Exporta o gabarito dos editais reais para a página de conferência.

Cada regra sai com a frase em português simples (`tender_intel.explain`) e, para cada citação,
a cláusula do edital com o trecho marcado, a seção e a página. Saída `.html` monta a página
a partir de `gold/review_page.html`; qualquer outra extensão grava só os dados em JSON.

    python gold/export_review.py conferencia-gabarito.html
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tender_intel.domain.rules import rules_from_dict  # noqa: E402
from tender_intel.explain import ACTORS, explain, section_label  # noqa: E402
from tender_intel.ingest.text import ingest_package  # noqa: E402

CASES = {
    "fapemig-sede-018-2026": {
        "short": "FAPEMIG 018/2026",
        "nickname": "HubMG Gov",
        "reader_note": "",
    },
    "cnpq-arc-34-2026": {
        "short": "CNPq 34/2026",
        "nickname": "Promoção de eventos (ARC)",
        "reader_note": "Nesta chamada, quem envia a proposta é o(a) coordenador(a) do projeto (item 3.2.1, alínea c).",
    },
    "cnpq-anr-32-2026": {
        "short": "CNPq 32/2026",
        "nickname": "Cooperação Brasil–França (ANR)",
        "reader_note": "Nesta chamada, quem envia a proposta é o(a) coordenador(a) brasileiro(a) do projeto (item 3.2.1).",
    },
}
CONTEXT = 260
PLACEHOLDER = "/*__GABARITO__*/"


def main(out: Path) -> None:
    cases = []
    for case_id, extra in CASES.items():
        package_dir = ROOT / "fixtures" / case_id
        package = ingest_package(package_dir)
        meta = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
        notes = json.loads((ROOT / "gold" / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))["notes"]
        rules = rules_from_dict(json.loads((package_dir / "graph.json").read_text(encoding="utf-8")))
        cases.append({
            "id": case_id,
            "title": meta["title"],
            "source": meta.get("source", ""),
            "notes": notes,
            **extra,
            "rules": [
                _with_rev({
                    "id": rule.id,
                    "title": rule.title,
                    "actor": ACTORS.get(rule.actor, rule.actor),
                    "explain": explain(rule.expression),
                    "evidence": [_excerpt(package, span) for span in rule.evidence],
                    "links": [_link(package, span) for span in rule.relation_evidence],
                })
                for rule in rules
            ],
        })
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "cases": cases}
    if out.suffix == ".html":
        template = (ROOT / "gold" / "review_page.html").read_text(encoding="utf-8")
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        out.write_text(template.replace(PLACEHOLDER, data, 1), encoding="utf-8")
    else:
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out}: {sum(len(case['rules']) for case in cases)} regras em {len(cases)} chamadas")


def rule_rev(rule: dict) -> str:
    """Muda quando muda o que a pessoa conferiu (título, frase, trechos): a marcação antiga deixa de valer."""
    seen = {
        "title": rule["title"],
        "explain": rule["explain"],
        "evidence": [item["quote"] for item in rule["evidence"]],
        "links": [item["quote"] for item in rule["links"]],
    }
    return hashlib.sha256(json.dumps(seen, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def _with_rev(rule: dict) -> dict:
    rule["rev"] = rule_rev(rule)
    return rule


def _excerpt(package, span) -> dict:
    element = package.element(span.element_id)
    if element is None:
        raise SystemExit(f"{span.id}: elemento {span.element_id} não existe")
    match = _locate(element.text, span.quote)
    if match is None:
        raise SystemExit(f"{span.id}: citação não encontrada no elemento {span.element_id}")
    before, after = element.text[: match.start()], element.text[match.end():]
    cut_before, cut_after = len(before) > CONTEXT, len(after) > CONTEXT
    if cut_before:
        before = before[-CONTEXT:].split(" ", 1)[-1]
    if cut_after:
        after = after[:CONTEXT].rsplit(" ", 1)[0]
    return {
        "id": span.id,
        "section": section_label(element.section_path),
        "page": element.page,
        "document": element.document_id,
        "before": _tidy(before),
        "quote": _tidy(match.group(0)),
        "after": _tidy(after),
        "cut_before": cut_before,
        "cut_after": cut_after,
        "full": _tidy(element.text) if (cut_before or cut_after) else "",
    }


def _link(package, span) -> dict:
    element = package.element(span.element_id)
    return {"id": span.id, "section": section_label(element.section_path) if element else "", "quote": _tidy(span.quote)}


def _locate(text: str, quote: str):
    words = quote.split()
    return re.search(r"\s+".join(re.escape(word) for word in words), text) if words else None


def _tidy(text: str) -> str:
    return " ".join(text.split()) if text.strip() else ""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: python gold/export_review.py saida.json")
    main(Path(sys.argv[1]))
