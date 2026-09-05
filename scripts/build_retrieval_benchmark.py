from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "retrieval-benchmark.json"
PROJECTS = [
    ("EOP101132", "Sunday Morning Hills Revegetation"),
    ("EOP101053", "Moquilambo Native Forest Protection Project"),
    ("ERF101444", "Watson River Station"),
    ("EOP100183", "Rochedale Landfill Gas Project"),
    ("ERF108333", "Bonnie Doone Soil Carbon Project"),
    ("EOP101126", "AHG Land Transport Emissions Reduction"),
    ("ERF169256", "Tahmoor Waste Coal Mine Gas Power Station"),
]


def build() -> dict[str, Any]:
    cases = []
    for project_id, name in PROJECTS:
        cases.extend([
            {"query_id": f"RET-{project_id}-IDENTITY", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": f"What is the registered name and method type for {project_id} {name}?", "expected_fact_id": f"CER_{project_id}.IDENTITY"},
            {"query_id": f"RET-{project_id}-TIMING", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": f"When was {project_id} registered and what is its crediting period timing?", "expected_fact_id": f"CER_{project_id}.TIMING"},
            {"query_id": f"RET-{project_id}-CONTEXT", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": f"What mapping availability and KACCU issuance context is recorded for {project_id}?", "expected_fact_id": f"CER_{project_id}.CONTEXT" if project_id != "EOP101132" else "CER_EOP101132.ISSUANCE"},
        ])
    cases.extend([
        {"query_id": "RET-SAFEGUARD-ARCADIA", "group_id": "RET-SAFEGUARD", "subject_type": "SAFEGUARD_FACILITY", "subject_id": "SAFEGUARD.2024-25.ARCADIA", "question": "Arcadia 2024-25 baseline covered emissions and SMC issuance", "expected_fact_id": "CER_SAFEGUARD_ARCADIA.2024-25"},
        {"query_id": "RET-UNIT-ACCU", "group_id": "RET-UNIT", "subject_type": "UNIT_CONCEPTS", "subject_id": "ACCU_SMC", "question": "CER definition of an ACCU and emissions otherwise released", "expected_fact_id": "CER_UNIT.ACCU_DEFINITION"},
        {"query_id": "RET-UNIT-SMC", "group_id": "RET-UNIT", "subject_type": "UNIT_CONCEPTS", "subject_id": "ACCU_SMC", "question": "CER definition of an SMC below a Safeguard facility baseline", "expected_fact_id": "CER_UNIT.SMC_DEFINITION"},
        {"query_id": "RET-FROZEN-OBSERVATION", "group_id": "RET-FROZEN", "subject_type": "ACCU_PROJECT", "subject_id": "EOP101132", "question": "EOP101132 frozen PRE POST median NDVI delta and joint coverage", "expected_fact_id": "EOP101132_V4.OBSERVATION"},
    ])
    return {
        "benchmark_version": "1.0.0",
        "split": "HELD_OUT",
        "label_authority": "REPOSITORY_ENGINEERING_RELEVANCE_EXPECTATION_NOT_HUMAN_GOLD",
        "query_count": len(cases),
        "cases_sha256": workflow.sha256_bytes(workflow.canonical_bytes(cases)),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the held-out retrieval benchmark.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = json.dumps(build(), indent=2, ensure_ascii=True) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("retrieval benchmark is missing or stale", file=sys.stderr)
            return 1
        print("Retrieval benchmark valid")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
