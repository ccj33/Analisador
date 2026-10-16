"""Casos que a conferência humana do gabarito (16/10/2026) apontou e que o gabarito tem de manter."""
import json
from pathlib import Path

from tender_intel.domain.rules import rules_from_dict
from tender_intel.domain.solver import solve

ROOT = Path(__file__).resolve().parents[1]


def _rule(case: str, rule_id: str):
    data = json.loads((ROOT / "fixtures" / case / "graph.json").read_text(encoding="utf-8"))
    return next(rule for rule in rules_from_dict(data) if rule.id == rule_id)


def _status(rule, **facts) -> str:
    values = {key.replace("__", "."): value for key, value in facts.items()}
    values["_conflicts"] = set()
    return solve(rule.expression, values).status


def test_fapemig_proposal_started_after_17h_misses_the_deadline():
    deadline = _rule("fapemig-sede-018-2026", "FAP-DEADLINE")
    sent = "2026-12-09T22:00:00-03:00"
    assert _status(deadline, submission__started_at="2026-12-09T16:59:00-03:00", submission__sent_at=sent) == "SATISFIED"
    assert _status(deadline, submission__started_at="2026-12-09T18:00:00-03:00", submission__sent_at=sent) == "UNSATISFIED"


def test_fapemig_counterpart_depends_on_proponent_type():
    rule = _rule("fapemig-sede-018-2026", "FAP-CONTRAPARTIDA")
    # startup com só contrapartida econômica não atende
    assert _status(rule, organization__type="STARTUP", project__total_counterpart_pct=10) != "SATISFIED"
    assert _status(rule, organization__type="STARTUP", project__financial_counterpart_pct=10) == "SATISFIED"
    # ICT-MG pode trocar a econômica por financeira, desde que a soma chegue a 10%
    assert _status(rule, organization__type="ICT_MG", project__total_counterpart_pct=10) == "SATISFIED"
    assert _status(rule, organization__type="ICT_MG", project__total_counterpart_pct=8) == "UNSATISFIED"


def test_fapemig_three_proposals_must_be_for_distinct_challenges():
    rule = _rule("fapemig-sede-018-2026", "FAP-LIMITE")
    big = {"organization__annual_gross_revenue_mg": 20000000, "organization__proposals_submitted": 3}
    assert _status(rule, **big, organization__proposals_distinct_challenges=True) == "SATISFIED"
    assert _status(rule, **big, organization__proposals_distinct_challenges=False) == "UNSATISFIED"


def test_fapemig_activities_outside_mg_only_when_accessory_and_justified():
    rule = _rule("fapemig-sede-018-2026", "FAP-EXEC-MG")
    outside = {"project__execution_state": "MG", "project__has_activities_outside_mg": True}
    assert _status(rule, **outside, project__outside_mg_activities_accessory=True, project__outside_mg_activities_justified=True) == "SATISFIED"
    assert _status(rule, **outside, project__outside_mg_activities_accessory=False, project__outside_mg_activities_justified=True) == "UNSATISFIED"


def test_fapemig_subcoordinator_in_commissioned_post_only_is_out():
    rule = _rule("fapemig-sede-018-2026", "FAP-SUBCOORD")
    ok = {
        "subcoordinator__is_career_public_servant": True, "subcoordinator__from_challenge_author_body": True,
        "subcoordinator__only_commissioned_post": False, "subcoordinator__works_in_challenge_area": True,
        "subcoordinator__has_authorization": True, "subcoordinator__indicated_in_everest": True,
        "subcoordinator__signed_interest_statement": True, "project__subcoordinators_count": 1,
    }
    assert _status(rule, **ok) == "SATISFIED"
    assert _status(rule, **{**ok, "subcoordinator__only_commissioned_post": True}) == "UNSATISFIED"
    assert _status(rule, **{**ok, "project__subcoordinators_count": 2}) == "UNSATISFIED"


def test_anr_cooperation_needs_technical_missions():
    rule = _rule("cnpq-anr-32-2026", "ANR-FRANCA")
    assert _status(rule, project__has_french_team=True, project__plans_technical_missions=False) == "UNSATISFIED"
