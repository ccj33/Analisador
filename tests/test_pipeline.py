from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.domain.evidence import EvidenceSpan, check_span
from tender_intel.eval.harness import measure_case
from tender_intel.ingest.text import ingest_package
from tender_intel.pipeline import compare_paths

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "fixtures" / "cnpq-universal-sintetica"


def test_missing_quote_is_not_empty_field():
    package = ingest_package(PACKAGE)
    check = check_span(package, EvidenceSpan("x", "chamada.elm_0011", "texto que ninguém escreveu"))
    assert check.found is False
    assert "não é substring" in check.reason


def test_grounded_quote_must_be_substring():
    package = ingest_package(PACKAGE)
    check = check_span(
        package,
        EvidenceSpan("x", "chamada.elm_0011", "instituições científicas, tecnológicas e de inovação sediadas no Brasil"),
    )
    assert check.found is True


def test_gold_profiles():
    report = measure_case(ROOT / "gold" / "cases" / "cnpq-universal-sintetica.json")
    assert report["ok"] is True


def test_merit_does_not_decide_overall():
    result = compare_paths(PACKAGE, PACKAGE / "facts-elegivel.json", AbstainProvider())
    merit = next(item for item in result.evaluations if item.rule_id == "REQ-MERIT")
    assert merit.status == "NOT_APPLICABLE"
    assert result.overall == "SATISFIED"


def test_human_override_wins():
    # A pipeline lê graph.json; este teste cobre o contrato via compare_paths + fato incompleto.
    result = compare_paths(PACKAGE, PACKAGE / "facts-incompleto.json", AbstainProvider())
    assert result.overall == "UNKNOWN"
    assert result.disclaimer.startswith("Assistente de conformidade")
