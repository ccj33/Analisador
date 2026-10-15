import json
import zipfile
from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.domain.types import AuthorityTier, EventType
from tender_intel.eval.harness import measure_case
from tender_intel.ingest.clauses import paged_lines, segment
from tender_intel.ingest.text import ingest_package
from tender_intel.pipeline import compare, compare_paths

ROOT = Path(__file__).resolve().parents[1]
FAPEMIG = ROOT / "fixtures" / "fapemig-sede-018-2026"

WRAPPED = """3. CRITÉRIOS DE ELEGIBILIDADE
3.1.1. Poderão figurar como Proponente empresas, startups, cooperativas ou ICTs-MG, observadas as
seguintes condições:
a) as ICTs-MG deverão executar as atividades do projeto no Estado de Minas Gerais;
Edital Fapemig/SEDE - 018/2026 - HUBMG GOV (150716523) SEI 2070.01.0004193/2026-74 / pg. 6
b) as Empresas poderão estar sediadas em qualquer unidade da federação, na forma do item
4.3 desta Chamada, com prazo de 18
meses.
"""


def test_wrapped_pdf_text_becomes_whole_clauses():
    elements = segment("d", paged_lines(WRAPPED), "text-pdf")
    texts = [element.text for element in elements]
    assert texts[0] == "3. CRITÉRIOS DE ELEGIBILIDADE"
    assert elements[0].kind == "heading"
    assert texts[1].endswith("observadas as seguintes condições:")
    assert elements[2].section_path == ("3.1.1", "a")
    assert elements[2].page == 6
    # rodapé some; remissão "4.3 desta" e "18 meses" não abrem cláusula nova
    assert len(elements) == 4
    assert texts[3].endswith("na forma do item 4.3 desta Chamada, com prazo de 18 meses.")
    assert elements[3].page == 7


def test_docx_paragraphs_and_tables(tmp_path: Path):
    body = (
        '<w:document xmlns:w="w"><w:body>'
        "<w:p><w:r><w:t>ANEXO VI - DECLARAÇÃO</w:t></w:r></w:p>"
        '<w:p><w:r><w:t xml:space="preserve">Nos termos do item 3.1.4, a Proponente </w:t></w:r>'
        "<w:r><w:t>&lt;NOME&gt; DECLARA.</w:t></w:r></w:p>"
        "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>célula</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(tmp_path / "anexo.docx", "w") as archive:
        archive.writestr("word/document.xml", body)
    manifest = {"id": "x", "title": "x", "documents": [{"id": "anexo", "path": "anexo.docx", "authority": "ANEXO_EDITAL", "event": "PUBLICACAO"}]}
    (tmp_path / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    document = ingest_package(tmp_path).documents[0]
    assert document.extractor == "docx-xml"
    assert [element.text for element in document.elements] == [
        "ANEXO VI - DECLARAÇÃO",
        "Nos termos do item 3.1.4, a Proponente <NOME> DECLARA.",
        "célula",
    ]


def test_no_rule_is_unknown_not_satisfied():
    package = ingest_package(FAPEMIG)
    result = compare(package, [], {"assertions": []}, AbstainProvider(), "compiled")
    assert result.overall == "UNKNOWN"


def test_fapemig_package_ingests_every_document():
    package = ingest_package(FAPEMIG)
    assert len(package.documents) == 10
    assert package.documents[1].authority == AuthorityTier.ANEXO_EDITAL
    assert package.documents[0].event == EventType.PUBLICACAO


def test_fapemig_gold_profiles_with_annotated_graph():
    for name, expected in (
        ("facts-elegivel.json", "SATISFIED"),
        ("facts-incompleto.json", "UNKNOWN"),
        ("facts-inelegivel.json", "UNSATISFIED"),
    ):
        result = compare_paths(FAPEMIG, FAPEMIG / name, AbstainProvider(), source="annotated")
        assert result.overall == expected, name
        assert all(item.evidence_ok for item in result.evaluations)


def test_fapemig_compiler_baseline_is_measured():
    # Linha de base honesta: o compilador de regex não reconhece nada desta chamada.
    # Quando ele melhorar, este número sobe e o teste deve ser atualizado.
    report = measure_case(ROOT / "gold" / "cases" / "fapemig-sede-018-2026.json")
    assert report["ok"] is False
    assert report["compiler"]["counts"]["OMITTED"] == 15
    assert report["compiler"]["counts"]["INVENTED"] == 0
    assert all(profile["annotated"]["match"] for profile in report["profiles"])
