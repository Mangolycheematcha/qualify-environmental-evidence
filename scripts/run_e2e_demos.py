from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

try:
    import qualification_session as session
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import qualification_session as session
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "results" / "e2e-demonstrations.json"


def request(request_id: str, subject_type: str, subject_id: str, family: str, question: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "request_id": request_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "claim_family": family,
        "question": question,
        "requested_output": "BOUNDED_EVIDENCE_MEMO",
        **extra,
    }


def summarize(name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "journey": name,
        "workflow_status": result["workflow_status"],
        "qualification": result["qualification"],
        "reason_codes": result["reason_codes"],
        "evidence_fact_ids": [item["fact_id"] for item in result["evidence_refs"]],
        "result_sha256": result["result_sha256"],
    }


def build(root: Path = ROOT) -> dict[str, Any]:
    journeys: list[dict[str, Any]] = []
    registry = workflow.run_qualification(request(
        "E2E-REGISTRY", "ACCU_PROJECT", "ERF108333", "REGISTRY_FACTS",
        "Give a bounded public CER registry memo for ERF108333 without judging quality.",
    ), root=root)
    journeys.append(summarize("REAL_ACCU_REGISTRY", registry))

    safeguard = workflow.run_qualification(request(
        "E2E-SAFEGUARD", "SAFEGUARD_FACILITY", "SAFEGUARD.2024-25.ARCADIA",
        "SAFEGUARD_FACILITY_FACTS", "Restate the published Arcadia facility-period Safeguard and SMC facts.",
    ), root=root)
    journeys.append(summarize("REAL_SAFEGUARD_SMC", safeguard))

    fault_results = {}
    fault_results["missing"] = workflow.run_qualification(request(
        "E2E-MISSING", "ACCU_PROJECT", "EOP999999", "REGISTRY_FACTS",
        "Give authoritative CER registry facts for a deliberately absent project.",
    ), root=root)
    fault_results["stale"] = workflow.run_qualification(request(
        "E2E-STALE", "ACCU_PROJECT", "EOP101132", "REGISTRY_FACTS",
        "Use only evidence newer than the curated public source snapshot for EOP101132.",
        minimum_source_date="2026-09-06",
    ), root=root)
    conflict_paths = [root / "evaluation" / "fixtures" / f"conflict-{suffix}.json" for suffix in ("a", "b")]
    fault_results["conflict"] = workflow.run_qualification(request(
        "E2E-CONFLICT", "ACCU_PROJECT", "SYNTHETIC-CONFLICT", "REGISTRY_FACTS",
        "Resolve two deliberately conflicting method-type assertions without guessing.",
    ), root=root, evidence_paths=conflict_paths)
    journeys.append({
        "journey": "FAIL_CLOSED_EVIDENCE_FAULTS",
        "outcomes": {key: summarize(key.upper(), value) for key, value in fault_results.items()},
    })

    mismatch = workflow.run_qualification(request(
        "E2E-BOUNDARY", "UNIT_CONCEPTS", "ACCU_SMC", "ACCU_SMC_EQUIVALENCE",
        "Treat ACCUs and SMCs as interchangeable because both use tonnes of carbon dioxide equivalent.",
    ), root=root)
    journeys.append(summarize("ACCU_SMC_MISMATCH_REFUSAL", mismatch))

    resumable_request = request(
        "E2E-RESUME", "ACCU_PROJECT", "EOP101053", "REGISTRY_FACTS",
        "Give a resumable bounded registry memo for EOP101053 without a quality conclusion.",
    )
    with tempfile.TemporaryDirectory(prefix="qualification-e2e-") as temporary:
        state_root = Path(temporary)
        paused = session.run_resumable(resumable_request, state_root=state_root, workflow_id="E2E-RESUME", root=root, stop_after="EVIDENCE_SNAPSHOTTED")
        completed = session.run_resumable(resumable_request, state_root=state_root, workflow_id="E2E-RESUME", root=root)
        checkpoints_before_replay = len(list((state_root / "checkpoints").rglob("*.json")))
        evidence_before_replay = len(list((state_root / "evidence").glob("*.json")))
        replayed = session.run_resumable(resumable_request, state_root=state_root, workflow_id="E2E-RESUME", root=root)
        checkpoints_after_replay = len(list((state_root / "checkpoints").rglob("*.json")))
        evidence_after_replay = len(list((state_root / "evidence").glob("*.json")))
        replay_equal = workflow.canonical_bytes(completed["result"]) == workflow.canonical_bytes(replayed["result"])
        replay_side_effect_free = (
            checkpoints_before_replay == checkpoints_after_replay
            and evidence_before_replay == evidence_after_replay
        )

    expected = {
        "REAL_ACCU_REGISTRY": "QUALIFIED",
        "REAL_SAFEGUARD_SMC": "QUALIFIED",
        "ACCU_SMC_MISMATCH_REFUSAL": "REFUSED",
    }
    ordinary_ok = all(next(item for item in journeys if item["journey"] == name)["workflow_status"] == status for name, status in expected.items())
    faults_ok = [fault_results[key]["reason_codes"] for key in ("missing", "stale", "conflict")] == [
        ["REQUIRED_EVIDENCE_MISSING"], ["EVIDENCE_TEMPORAL_MISMATCH"], ["EVIDENCE_CONFLICT_UNRESOLVED"]
    ]
    report = {
        "report_version": "2.0.0",
        "network_access": False,
        "live_eo_executed": False,
        "journey_count": 4,
        "journeys": journeys,
        "resume_replay": {
            "paused_status": paused["session_status"],
            "completed_status": completed["session_status"],
            "replayed_status": replayed["session_status"],
            "canonical_result_bytes_equal": replay_equal,
            "checkpoint_files_before_replay": checkpoints_before_replay,
            "checkpoint_files_after_replay": checkpoints_after_replay,
            "evidence_files_before_replay": evidence_before_replay,
            "evidence_files_after_replay": evidence_after_replay,
            "external_action_count": 0,
            "replay_created_no_files": replay_side_effect_free,
            "result_sha256": completed["result"]["result_sha256"],
        },
        "status": "PASS" if ordinary_ok and faults_ok and replay_equal and replay_side_effect_free else "FAIL",
    }
    report["report_sha256"] = workflow.sha256_bytes(workflow.canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run four offline end-to-end qualification journeys.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
