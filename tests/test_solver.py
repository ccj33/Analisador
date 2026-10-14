from tender_intel.domain.ast import All, AnyOf, Compare, Count, Exists, FactRef, Literal, Not, Unless
from tender_intel.domain.solver import solve
from tender_intel.domain.types import Status


def test_all_unknown_when_fact_missing():
    node = All((Compare("EQ", FactRef("organization.country"), Literal("BR")),))
    result = solve(node, {"_conflicts": set()})
    assert result.status == Status.UNKNOWN.value


def test_private_needs_public_ict_partner():
    node = AnyOf(
        (
            All(
                (
                    Compare("EQ", FactRef("organization.type"), Literal("ICT")),
                    Compare("EQ", FactRef("organization.legal_nature"), Literal("PUBLIC")),
                )
            ),
            All(
                (
                    Compare("EQ", FactRef("organization.legal_nature"), Literal("PRIVATE")),
                    Exists(
                        FactRef("project.partners"),
                        All(
                            (
                                Compare("EQ", FactRef("type"), Literal("ICT")),
                                Compare("EQ", FactRef("legal_nature"), Literal("PUBLIC")),
                            )
                        ),
                    ),
                )
            ),
        )
    )
    private_ok = {
        "organization.type": "COMPANY",
        "organization.legal_nature": "PRIVATE",
        "project.partners": [{"type": "ICT", "legal_nature": "PUBLIC"}],
        "_conflicts": set(),
    }
    private_fail = {
        "organization.legal_nature": "PRIVATE",
        "project.partners": [{"type": "COMPANY", "legal_nature": "PRIVATE"}],
        "_conflicts": set(),
    }
    assert solve(node, private_ok).status == Status.SATISFIED.value
    assert solve(node, private_fail).status == Status.UNSATISFIED.value


def test_unless_and_not():
    node = Unless(FactRef("eligible"), FactRef("excluded"))
    assert solve(node, {"eligible": True, "excluded": False, "_conflicts": set()}).status == Status.SATISFIED.value
    assert solve(node, {"eligible": True, "excluded": True, "_conflicts": set()}).status == Status.UNSATISFIED.value


def test_count_doctors():
    node = Count(FactRef("project.members"), Compare("EQ", FactRef("degree"), Literal("PHD")), "GTE", 2)
    facts = {
        "project.members": [{"degree": "PHD"}, {"degree": "MSC"}, {"degree": "PHD"}],
        "_conflicts": set(),
    }
    assert solve(node, facts).status == Status.SATISFIED.value


def test_deadline_uses_brasilia_offset():
    node = Compare("LTE", FactRef("submission.sent_at"), Literal("2026-12-07T23:59:00-03:00"))
    on_time = {"submission.sent_at": "2026-12-07T20:00:00-03:00", "_conflicts": set()}
    late = {"submission.sent_at": "2026-12-08T00:10:00-03:00", "_conflicts": set()}
    assert solve(node, on_time).status == Status.SATISFIED.value
    assert solve(node, late).status == Status.UNSATISFIED.value


def test_conflict_beats_unknown():
    node = Compare("EQ", FactRef("organization.country"), Literal("BR"))
    result = solve(node, {"_conflicts": {"organization.country"}})
    assert result.status == Status.CONFLICT.value


def test_not_unknown_stays_unknown():
    result = solve(Not(FactRef("missing")), {"_conflicts": set()})
    assert result.status == Status.UNKNOWN.value
