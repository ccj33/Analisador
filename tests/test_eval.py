import json
from dataclasses import replace
from pathlib import Path

from tender_intel.compile.extract import compile_rules
from tender_intel.domain.ast import Compare, FactRef, Literal
from tender_intel.domain.evidence import EvidenceSpan
from tender_intel.domain.rules import rules_from_dict
from tender_intel.eval.harness import measure_case
from tender_intel.eval.rules import compare_rules, values_missing_from_evidence
from tender_intel.ingest.text import ingest_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "fixtures" / "cnpq-universal-sintetica"


def _annotated():
    return rules_from_dict(json.loads((PACKAGE / "graph.json").read_text(encoding="utf-8")))


def _compiled():
    return compile_rules(ingest_package(PACKAGE))


def test_eval_measures_compiler_not_only_annotation():
    report = measure_case(ROOT / "gold" / "cases" / "cnpq-universal-sintetica.json")
    assert report["compiler"]["counts"]["MATCH"] == 6
    assert all(profile["compiled"]["match"] for profile in report["profiles"])


def test_missing_rule_is_omission():
    compiled = [rule for rule in _compiled() if rule.id != "REQ-COORD"]
    report = compare_rules(_annotated(), compiled)
    assert report["ok"] is False
    omitted = [row for row in report["rules"] if row["outcome"] == "OMITTED"]
    assert [row["annotated_id"] for row in omitted] == ["REQ-COORD"]
    assert report["by_type"]["PRE_SUBMISSION/COORDINATOR"]["OMITTED"] == 1


def test_extra_rule_is_invention():
    extra = replace(
        _compiled()[0],
        id="REQ-MG",
        expression=Compare("EQ", FactRef("organization.state"), Literal("MG")),
    )
    report = compare_rules(_annotated(), [*_compiled(), extra])
    assert report["counts"]["INVENTED"] == 1


def test_wrong_value_is_different_logic():
    compiled = [
        replace(rule, expression=Compare("GTE", FactRef("project.merit_min_pct"), Literal(60))) if rule.id == "REQ-MERIT" else rule
        for rule in _compiled()
    ]
    report = compare_rules(_annotated(), compiled)
    row = next(row for row in report["rules"] if row["annotated_id"] == "REQ-MERIT")
    assert row["outcome"] == "DIFFERENT_LOGIC"
    assert row["values_missing_from_evidence"] == ["60"]


def test_date_must_appear_in_quote():
    rule = next(rule for rule in _compiled() if rule.id == "REQ-DEADLINE")
    assert values_missing_from_evidence(rule) == []
    wrong = replace(rule, evidence=(EvidenceSpan("x", rule.evidence[0].element_id, "as propostas"),))
    assert values_missing_from_evidence(wrong) == ["2026-12-07T23:59:00-03:00"]
