from __future__ import annotations

from html import escape
from pathlib import Path

from tender_intel.pipeline import CompareResult


def write_review_table(result: CompareResult, path: Path) -> None:
    rows = []
    for item in result.evaluations:
        notes = "<br>".join(escape(note) for note in item.evidence_notes)
        rows.append(
            "<tr>"
            f"<td>{escape(item.rule_id)}</td>"
            f"<td>{escape(item.title)}<div class='muted'>{escape(item.rendered)}</div></td>"
            f"<td>{escape(item.layer)} / {escape(item.actor)}</td>"
            f"<td class='{item.status.lower()}'>{escape(item.status)}</td>"
            f"<td>{escape(item.reason)}</td>"
            f"<td>{notes}</td>"
            "</tr>"
        )
    deadline_rows = "".join(
        "<li>"
        f"{escape(item['iso_date'])} · {escape(item['event'])} · {escape(item['element_id'])}"
        f" · {'vigente' if item['effective'] else 'substituído por ' + escape(item['superseded_by'] or '')}"
        "</li>"
        for item in result.deadlines
    )
    dependency_rows = "".join(
        f"<li>{escape(item['status'])}: {escape(item['target'])} ({escape(item['element_id'])})</li>"
        for item in result.dependencies
    )
    effect_rows = "".join(
        f"<li>{escape(item['effect'])} ({escape(item['element_id'])})</li>" for item in result.effects
    )
    ocr_rows = "".join(
        f"<li>{escape(str(item['document_id']))}: páginas {escape(', '.join(str(page) for page in item['pages']))}</li>"
        for item in result.needs_ocr
    )
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Review Table — {escape(result.title)}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 2rem; color: #1a1a1a; background: #f7f5f0; }}
    h1 {{ font-size: 1.4rem; }}
    .disclaimer {{ max-width: 70ch; border-left: 3px solid #6b4f2a; padding-left: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border: 1px solid #d6d1c4; padding: 0.6rem; vertical-align: top; font-size: 0.92rem; }}
    th {{ text-align: left; background: #efeae0; }}
    .muted {{ color: #5c574c; font-size: 0.85rem; margin-top: 0.35rem; }}
    .satisfied {{ color: #1f5c38; font-weight: 700; }}
    .unsatisfied {{ color: #8a1f1f; font-weight: 700; }}
    .unknown {{ color: #6b4f2a; font-weight: 700; }}
    .conflict {{ color: #6b2a5c; font-weight: 700; }}
    .not_applicable {{ color: #5c574c; }}
  </style>
</head>
<body>
  <p class="disclaimer">{escape(result.disclaimer)}</p>
  <h1>{escape(result.title)}</h1>
  <p>Resultado global da camada PRE_SUBMISSION: <strong>{escape(result.overall)}</strong></p>
  <p>Origem das regras: {escape("compiladas do texto" if result.rule_source == "compiled" else "grafo anotado")}</p>
  <p>Arquivos {result.coverage["documents"]} · elementos {result.coverage["elements"]} · regras {result.coverage["rules"]} · evidências ancoradas {result.coverage["rules_with_grounded_evidence"]}/{result.coverage["rules"]}</p>
  <h2>Prazos</h2>
  <ul>{deadline_rows or "<li>Nenhum prazo com data encontrado.</li>"}</ul>
  <h2>Referências externas</h2>
  <ul>{dependency_rows or "<li>Nenhuma referência externa detectada.</li>"}</ul>
  <h2>Efeitos</h2>
  <ul>{effect_rows or "<li>Nenhum efeito de impugnação detectado.</li>"}</ul>
  <h2>Páginas sem camada de texto</h2>
  <ul>{ocr_rows or "<li>Nenhuma. OCR não foi acionado.</li>"}</ul>
  <table>
    <thead>
      <tr><th>ID</th><th>Regra</th><th>Camada / ator</th><th>Status</th><th>Motivo</th><th>Evidência</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
