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

IDENTITY_QUERIES = (
    "Which record gives this project's registered name, method category, and jurisdiction?",
    "Which fact identifies this project by registered name, method and state?",
    "Which public-register fact states the project identity, method family, and state?",
    "Return the source-backed project identity fields, including method type and location.",
    "What identity information does the register provide for this project?",
    "Find the fact that describes this project's name, scheme category, and operating area.",
    "Which evidence item identifies the project and its method and location?",
)
TIMING_QUERIES = (
    "Which fact records this project's registration and crediting-period dates?",
    "Find the public timing fields for registration, crediting start, and crediting end.",
    "What register evidence describes the project's key dates and crediting period?",
    "Return the fact containing registration timing and the crediting-period window.",
    "Which source-backed statement gives this project's registration and crediting dates?",
    "Locate the project timing record, including registration and crediting period.",
    "Which evidence item contains the project's registration and scheme timing?",
)
CONTEXT_QUERIES = (
    "Which fact reports mapping availability and issued-unit context for this project?",
    "Find the register context about project mapping and issuance totals.",
    "What evidence records the project's map status and credited-unit context?",
    "Return the contextual register fact about map availability and issuance.",
    "Which source-backed statement covers mapping and unit-issuance context?",
    "Locate the project context record for mapping and credited units.",
    "Which evidence item describes map availability and issuance context?",
)


def build() -> dict[str, Any]:
    cases = []
    project_names = dict(PROJECTS)
    for index, (project_id, name) in enumerate(PROJECTS):
        cases.extend([
            {"query_id": f"RET-{project_id}-IDENTITY", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": IDENTITY_QUERIES[index], "expected_fact_id": f"CER_{project_id}.IDENTITY"},
            {"query_id": f"RET-{project_id}-TIMING", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": TIMING_QUERIES[index], "expected_fact_id": f"CER_{project_id}.TIMING"},
            {"query_id": f"RET-{project_id}-CONTEXT", "group_id": f"RET-{project_id}", "subject_type": "ACCU_PROJECT", "subject_id": project_id, "question": CONTEXT_QUERIES[index], "expected_fact_id": f"CER_{project_id}.CONTEXT" if project_id != "EOP101132" else "CER_EOP101132.ISSUANCE"},
        ])
    cases.extend([
        {"query_id": "RET-SAFEGUARD-ARCADIA", "group_id": "RET-SAFEGUARD", "subject_type": "SAFEGUARD_FACILITY", "subject_id": "SAFEGUARD.2024-25.ARCADIA", "question": "Which facility-period fact contains baseline, covered emissions, net position, and SMC issuance?", "expected_fact_id": "CER_SAFEGUARD_ARCADIA.2024-25"},
        {"query_id": "RET-UNIT-ACCU", "group_id": "RET-UNIT", "subject_type": "UNIT_CONCEPTS", "subject_id": "ACCU_SMC", "question": "Which definition describes a unit for emissions that otherwise would have entered the atmosphere?", "expected_fact_id": "CER_UNIT.ACCU_DEFINITION"},
        {"query_id": "RET-UNIT-SMC", "group_id": "RET-UNIT", "subject_type": "UNIT_CONCEPTS", "subject_id": "ACCU_SMC", "question": "Which definition describes a below-baseline facility unit that is not an offset?", "expected_fact_id": "CER_UNIT.SMC_DEFINITION"},
        {"query_id": "RET-FROZEN-OBSERVATION", "group_id": "RET-FROZEN", "subject_type": "ACCU_PROJECT", "subject_id": "EOP101132", "question": "Which frozen observation reports PRE and POST NDVI, delta, threshold disposition, and joint coverage?", "expected_fact_id": "EOP101132_V4.OBSERVATION"},
    ])
    for case in cases:
        question = case["question"].lower()
        prohibited = [case["expected_fact_id"], case["subject_id"], "Arcadia"]
        prohibited.extend(project_names)
        prohibited.extend(project_names.values())
        if any(value.lower() in question for value in prohibited):
            raise AssertionError(f"direct query-label leakage in {case['query_id']}")
    return {
        "benchmark_version": "2.0.0",
        "split": "CONTROLLED_FROZEN_QUERY_SET",
        "label_authority": "REPOSITORY_ENGINEERING_RELEVANCE_EXPECTATION_NOT_HUMAN_GOLD",
        "query_provenance": "REPOSITORY_AUTHORED_AFTER_CORPUS_NOT_INDEPENDENT_HUMAN_QUERIES",
        "ranking_text_fields": ["text"],
        "metadata_filters": ["subject_type", "subject_id"],
        "direct_label_leakage_check": "PASS",
        "query_count": len(cases),
        "cases_sha256": workflow.sha256_bytes(workflow.canonical_bytes(cases)),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the controlled retrieval benchmark.")
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
