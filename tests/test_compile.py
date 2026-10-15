import json
from dataclasses import replace
from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.compile.coverage import clause_coverage, coverage_counts
from tender_intel.compile.discover import discover
from tender_intel.compile.extract import compile_rules
from tender_intel.domain.documents import DocumentElement, SourceDocument, TenderPackage
from tender_intel.domain.rules import rules_from_dict, rules_to_dict
from tender_intel.domain.types import AuthorityTier, EventType
from tender_intel.ingest.pdf import write_text_pdf
from tender_intel.ingest.text import ingest_package
from tender_intel.pipeline import compare, compare_paths

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "fixtures" / "cnpq-universal-sintetica"


def test_retificacao_supersedes_original_deadline():
    draft = discover(ingest_package(PACKAGE))
    effective = [item for item in draft.deadlines if item.effective]
    superseded = [item for item in draft.deadlines if not item.effective]
    assert len(effective) == 1
    assert effective[0].iso_date == "2026-12-07"
    assert effective[0].event == "RETIFICACAO"
    assert superseded[0].iso_date == "2026-11-30"
    assert superseded[0].superseded_by == effective[0].element_id


def test_missing_manual_stays_unresolved():
    draft = discover(ingest_package(PACKAGE))
    manuals = [item for item in draft.dependencies if "Manual de Bolsas" in item.target]
    assert manuals
    assert manuals[0].status == "UNRESOLVED"


def test_impugnacao_does_not_suspend():
    draft = discover(ingest_package(PACKAGE))
    assert any(item.effect == "NAO_SUSPENDE_PRAZO" for item in draft.effects)


def test_pdf_text_layer_and_blank_page(tmp_path: Path):
    pdf = tmp_path / "edital.pdf"
    write_text_pdf(
        pdf,
        [
            ["2.1 Instituicoes sediadas no Brasil."],
            [],
        ],
    )
    manifest = {
        "id": "pdf-sintetico",
        "title": "PDF sintetico",
        "documents": [
            {"id": "edital", "path": "edital.pdf", "authority": "EDITAL_CORPO", "event": "PUBLICACAO"}
        ],
    }
    (tmp_path / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    package = ingest_package(tmp_path)
    document = package.documents[0]
    assert document.extractor == "pypdf"
    assert document.needs_ocr_pages == (2,)
    assert any("sediadas no Brasil" in element.text for element in document.elements)
    assert document.elements[0].page == 1


def test_compiled_graph_matches_gold_profiles():
    expected = {
        "facts-elegivel.json": "SATISFIED",
        "facts-incompleto.json": "UNKNOWN",
        "facts-inelegivel.json": "UNSATISFIED",
    }
    for name, overall in expected.items():
        result = compare_paths(PACKAGE, PACKAGE / name, AbstainProvider(), source="compiled")
        assert result.overall == overall
        assert result.rule_source == "compiled"
        assert all(item.evidence_ok for item in result.evaluations)


def test_compiler_skips_sentence_without_pattern():
    package = TenderPackage(
        id="vazio",
        title="Sem regra",
        documents=[
            SourceDocument(
                id="doc",
                path="doc.md",
                authority=AuthorityTier.EDITAL_CORPO,
                event=EventType.PUBLICACAO,
                sha256="0",
                text="Apoio a projetos de pesquisa.",
                elements=(
                    DocumentElement("doc.elm_0001", "doc", "paragraph", "Apoio a projetos de pesquisa.", (), 0, 10),
                ),
            )
        ],
    )
    assert compile_rules(package) == []


def test_compiled_rules_roundtrip():
    rules = compile_rules(ingest_package(PACKAGE))
    restored = rules_from_dict(rules_to_dict(rules))
    assert [rule.id for rule in restored] == [rule.id for rule in rules]


def test_human_review_overrides_deadline(tmp_path: Path):
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps({"overrides": [{"rule_id": "REQ-DEADLINE", "status": "SATISFIED"}]}),
        encoding="utf-8",
    )
    result = compare_paths(
        PACKAGE,
        PACKAGE / "facts-inelegivel.json",
        AbstainProvider(),
        review,
    )
    deadline = next(item for item in result.evaluations if item.rule_id == "REQ-DEADLINE")
    assert deadline.status == "SATISFIED"
    assert deadline.human_override == "SATISFIED"
    assert result.overall == "SATISFIED"


def test_every_clause_has_a_destination():
    package = ingest_package(PACKAGE)
    rules = compile_rules(package)
    clauses = clause_coverage(package, rules, discover(package))
    counts = coverage_counts(clauses)
    by_id = {item.element_id: item for item in clauses}
    assert counts["clauses"] == counts["clauses_in_rules"] + counts["clauses_in_discovery"] + counts["clauses_unclassified"]
    assert by_id["chamada.elm_0011"].used_by == ("REQ-GEO", "REQ-INST")
    assert by_id["chamada.elm_0021"].status == "DISCOVERY"
    assert by_id["chamada.elm_0007"].status == "UNCLASSIFIED"


def test_unknown_clause_is_reported_not_dropped():
    package = ingest_package(PACKAGE)
    first = package.documents[0]
    extra = DocumentElement(f"{first.id}.elm_9999", first.id, "item", "2.9 O proponente deverá ter sede em Minas Gerais.", ("2.9",), 0, 0)
    package.documents[0] = replace(first, elements=(*first.elements, extra))
    result = compare(package, compile_rules(package), {"assertions": []}, AbstainProvider(), "compiled")
    unclassified = [item for item in result.clauses if item["status"] == "UNCLASSIFIED"]
    assert extra.id in {item["element_id"] for item in unclassified}
    assert result.coverage["clauses_unclassified"] == len(unclassified)
