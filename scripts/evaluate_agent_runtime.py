from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

try:
    import agent_runtime
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import agent_runtime
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "results" / "agent-runtime-evaluation.json"
def _counts(state_root: Path) -> dict[str, int]:
    return {
        "checkpoint_files": len(list((state_root / "checkpoints").rglob("*.json"))),
        "evidence_files": len(list((state_root / "evidence").glob("*.json"))),
    }


def build(root: Path = ROOT) -> dict:
    request = workflow.load_json(root / "examples" / "qualification" / "eop101132-request.json")
    with tempfile.TemporaryDirectory(prefix="agent-runtime-eval-") as temporary:
        state_root = Path(temporary)
        completed = agent_runtime.run_agent(
            request,
            state_root=state_root,
            workflow_id="AGENT-RUNTIME-EVAL",
            root=root,
            max_steps=3,
        )
        before_replay = _counts(state_root)
        replayed = agent_runtime.run_agent(
            request,
            state_root=state_root,
            workflow_id="AGENT-RUNTIME-EVAL",
            root=root,
            max_steps=1,
        )
        after_replay = _counts(state_root)

    with tempfile.TemporaryDirectory(prefix="agent-budget-eval-") as temporary:
        state_root = Path(temporary)
        paused = agent_runtime.run_agent(
            request,
            state_root=state_root,
            workflow_id="AGENT-BUDGET-EVAL",
            root=root,
            max_steps=1,
        )
        resumed = agent_runtime.run_agent(
            request,
            state_root=state_root,
            workflow_id="AGENT-BUDGET-EVAL",
            root=root,
            max_steps=2,
        )

    checks = {
        "bounded_three_step_completion": completed["final_status"] == "COMPLETED" and len(completed["steps"]) == 3,
        "one_step_budget_stop": paused["final_status"] == "PAUSED" and paused["stop_reason"] == "STEP_BUDGET_EXHAUSTED",
        "resume_after_budget_stop": resumed["final_status"] == "COMPLETED",
        "replay_is_terminal": replayed["final_status"] == "REPLAYED",
        "replay_result_is_byte_identical": completed["result_sha256"] == replayed["result_sha256"],
        "replay_creates_no_files": before_replay == after_replay,
        "network_remained_disabled": all(
            receipt["network_access"] is False
            for receipt in (completed, replayed, paused, resumed)
        ),
        "external_action_count_zero": all(
            receipt["external_action_count"] == 0
            for receipt in (completed, replayed, paused, resumed)
        ),
    }
    report = {
        "report_version": "1.0.0",
        "agent_loop": "OBSERVE_DECIDE_ACT_VERIFY",
        "memory_mode": "CONTENT_ADDRESSED_LOCAL_EVIDENCE",
        "checkpoint_mode": "APPEND_ONLY_HASH_BOUND",
        "completed_receipt_sha256": completed["receipt_sha256"],
        "replayed_receipt_sha256": replayed["receipt_sha256"],
        "paused_receipt_sha256": paused["receipt_sha256"],
        "resumed_receipt_sha256": resumed["receipt_sha256"],
        "result_sha256": completed["result_sha256"],
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    report["report_sha256"] = workflow.sha256_bytes(workflow.canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the bounded offline agent runtime.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if args.check:
        if not OUTPUT.is_file() or workflow.load_json(OUTPUT) != report:
            print("agent runtime evaluation artifact is stale", file=sys.stderr)
            return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
