from __future__ import annotations

import json
from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.compile.extract import compile_rules
from tender_intel.domain.rules import rules_from_dict
from tender_intel.eval.rules import compare_rules
from tender_intel.ingest.text import ingest_package
from tender_intel.pipeline import compare_paths

SOURCES = ("annotated", "compiled")


def measure_case(case_path: Path) -> dict:
    """Mede o caso duas vezes: com o grafo anotado (solver) e com o compilado (compilador + solver)."""
    spec = json.loads(case_path.read_text(encoding="utf-8"))
    root = case_path.parents[2]
    package_dir = root / spec["package"]
    annotated = rules_from_dict(json.loads((package_dir / "graph.json").read_text(encoding="utf-8")))
    compiler = compare_rules(annotated, compile_rules(ingest_package(package_dir)))
    ok = compiler["ok"]
    profiles = []
    for profile in spec["profiles"]:
        row = {"name": profile["name"], "expected": profile["expected_overall"]}
        for source in SOURCES:
            result = compare_paths(package_dir, root / profile["facts"], AbstainProvider(), source=source)
            match = result.overall == profile["expected_overall"]
            grounded = all(item.evidence_ok for item in result.evaluations if item.layer == "PRE_SUBMISSION")
            if not match or not grounded:
                ok = False
            row[source] = {
                "got": result.overall,
                "match": match,
                "all_pre_submission_grounded": grounded,
                "invented_citation": not grounded,
            }
        profiles.append(row)
    return {"case": spec["id"], "ok": ok, "compiler": compiler, "profiles": profiles}
