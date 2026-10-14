from __future__ import annotations

import json
from pathlib import Path

from tender_intel.ai.provider import AbstainProvider
from tender_intel.pipeline import compare_paths


def measure_case(case_path: Path) -> dict:
    spec = json.loads(case_path.read_text(encoding="utf-8"))
    root = case_path.parents[2]
    package_dir = root / spec["package"]
    profiles = []
    ok = True
    for profile in spec["profiles"]:
        result = compare_paths(package_dir, root / profile["facts"], AbstainProvider())
        match = result.overall == profile["expected_overall"]
        grounded = all(item.evidence_ok for item in result.evaluations if item.layer == "PRE_SUBMISSION")
        invented = not grounded
        if not match or not grounded:
            ok = False
        profiles.append(
            {
                "name": profile["name"],
                "expected": profile["expected_overall"],
                "got": result.overall,
                "match": match,
                "all_pre_submission_grounded": grounded,
                "invented_citation": invented,
            }
        )
    return {"case": spec["id"], "ok": ok, "profiles": profiles}
