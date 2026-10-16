import json
import zipfile
from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.compile.discover import discover, submission_deadline
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


REAL_CASES = {"fapemig-sede-018-2026": 15, "cnpq-arc-34-2026": 13, "cnpq-anr-32-2026": 10}


def test_real_gold_profiles_with_annotated_graph():
    for case in REAL_CASES:
        package = ROOT / "fixtures" / case
        for name, expected in (
            ("facts-elegivel.json", "SATISFIED"),
            ("facts-incompleto.json", "UNKNOWN"),
            ("facts-inelegivel.json", "UNSATISFIED"),
        ):
            result = compare_paths(package, package / name, AbstainProvider(), source="annotated")
            assert result.overall == expected, (case, name)
            assert all(item.evidence_ok for item in result.evaluations), case


def test_compiler_baseline_is_measured():
    # Linha de base honesta: o compilador de regex não reconhece nada destas chamadas.
    # Quando ele melhorar, estes números mudam e o teste deve ser atualizado.
    for case, rules in REAL_CASES.items():
        report = measure_case(ROOT / "gold" / "cases" / f"{case}.json")
        assert report["ok"] is False
        assert report["compiler"]["counts"]["OMITTED"] == rules, case
        assert report["compiler"]["counts"]["INVENTED"] == 0, case
        assert all(profile["annotated"]["match"] for profile in report["profiles"]), case


def test_submission_deadline_found_in_real_calls():
    expected = {"fapemig-sede-018-2026": "2026-12-09", "cnpq-arc-34-2026": "2026-12-04", "cnpq-anr-32-2026": "2027-03-31"}
    for case, iso in expected.items():
        effective = [item.iso_date for item in discover(ingest_package(ROOT / "fixtures" / case)).deadlines if item.effective]
        assert effective == [iso], case


def test_launch_and_challenge_dates_are_not_deadlines():
    assert submission_deadline("Lançamento da Chamada 14/10/2026 Prazo para impugnação da Chamada 26/10/2026") is None
    assert submission_deadline("Disponibilização do Formulário Eletrônico para submissão de propostas 09/10/2026") is None
    assert submission_deadline("Data limite para submissão das propostas 04/12/2026") == "2026-12-04"
    assert submission_deadline("deverão ser enviadas até 30/11/2026, às 23h59") == "2026-11-30"


def test_cnpq_numbering_and_sei_print_footer():
    package = ingest_package(ROOT / "fixtures" / "cnpq-anr-32-2026")
    texts = [element.text for element in package.documents[0].elements]
    assert not any("sei.cnpq.br/sei/controlador" in text for text in texts)
    by_section = {element.section_path: element for element in package.documents[0].elements}
    assert by_section[("7",)].text == "7- JULGAMENTO"
    assert by_section[("3.2.1", "b")].text == "b) possuir o título de doutor(a);"
    arc = ingest_package(ROOT / "fixtures" / "cnpq-arc-34-2026").documents[0].elements
    # "1.3.1.1 -Nos termos" e "1.3.3- LINHA 3" abrem cláusula; "conforme" + "CRONOGRAMA." é uma frase só
    assert any(element.section_path == ("1.3.3",) and element.kind == "heading" for element in arc)
    assert any(" ".join(element.text.split()).endswith("Diário Oficial da União, conforme CRONOGRAMA.") for element in arc)
