from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import qualification_session as session
    import qualification_workflow as workflow
    from retrieval_memory import CheckpointStore
except ModuleNotFoundError:
    from scripts import qualification_session as session
    from scripts import qualification_workflow as workflow
    from scripts.retrieval_memory import CheckpointStore


ROOT = Path(__file__).resolve().parents[1]
MAX_AGENT_STEPS = 20
ACTION_BY_STAGE = {
    "REQUEST_VALIDATED": "VALIDATE_REQUEST",
    "EVIDENCE_SNAPSHOTTED": "SNAPSHOT_EVIDENCE",
    "COMPLETE": "QUALIFY",
}


def _checkpoint_state(store: CheckpointStore, workflow_id: str) -> tuple[int, dict[str, Any]] | None:
    return store.latest(workflow_id)


def _next_stage(state: dict[str, Any] | None) -> str | None:
    completed = set(state.get("completed_stages", [])) if state else set()
    return next((stage for stage in session.STAGES if stage not in completed), None)


def _receipt_hash(receipt: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return workflow.sha256_bytes(workflow.canonical_bytes(unsigned))


def run_agent(
    request: dict[str, Any],
    *,
    state_root: Path,
    workflow_id: str,
    root: Path = ROOT,
    max_steps: int = 3,
) -> dict[str, Any]:
    """Run a bounded observe-decide-act-verify loop over the resumable workflow."""
    if max_steps < 1 or max_steps > MAX_AGENT_STEPS:
        raise workflow.QualificationError(f"max_steps must be between 1 and {MAX_AGENT_STEPS}")

    request_hash = workflow.sha256_bytes(workflow.canonical_bytes(request))
    store = CheckpointStore(state_root)
    events: list[dict[str, Any]] = []
    final_status = "PAUSED"
    stop_reason = "STEP_BUDGET_EXHAUSTED"

    for step_number in range(1, max_steps + 1):
        before = _checkpoint_state(store, workflow_id)
        before_state = before[1] if before else None
        next_stage = _next_stage(before_state)
        action = "REPLAY_VERIFY" if next_stage is None else ACTION_BY_STAGE[next_stage]
        stop_after = next_stage if next_stage in {"REQUEST_VALIDATED", "EVIDENCE_SNAPSHOTTED"} else None

        outcome = session.run_resumable(
            request,
            state_root=state_root,
            workflow_id=workflow_id,
            root=root,
            stop_after=stop_after,
        )
        latest = _checkpoint_state(store, workflow_id)
        if latest is None:
            raise workflow.QualificationError("agent action produced no checkpoint")
        sequence, state = latest
        checkpoint_hash = workflow.sha256_bytes(workflow.canonical_bytes(state))
        result = outcome.get("result")
        result_hash = result.get("result_sha256") if result else None
        event = {
            "step": step_number,
            "action": action,
            "session_status": outcome["session_status"],
            "checkpoint_sequence": sequence,
            "checkpoint_sha256": checkpoint_hash,
            "completed_stages": sorted(state["completed_stages"]),
            "evidence_snapshot_count": len(state.get("evidence_snapshot_sha256s", [])),
            "verified": True,
        }
        if result_hash is not None:
            event["result_sha256"] = result_hash
        events.append(event)

        if outcome["session_status"] in {"COMPLETED", "REPLAYED"}:
            final_status = outcome["session_status"]
            stop_reason = "ALREADY_COMPLETE" if outcome["session_status"] == "REPLAYED" else "TERMINAL_RESULT"
            break

    latest = _checkpoint_state(store, workflow_id)
    latest_state = latest[1] if latest else {}
    result = latest_state.get("result")
    receipt = {
        "receipt_schema_version": "1.0.0",
        "workflow_id": workflow_id,
        "request_sha256": request_hash,
        "max_steps": max_steps,
        "steps": events,
        "final_status": final_status,
        "stop_reason": stop_reason,
        "network_access": False,
        "external_action_count": 0,
        "evidence_snapshot_sha256s": sorted(latest_state.get("evidence_snapshot_sha256s", [])),
        "result_sha256": result.get("result_sha256") if result else None,
    }
    receipt["receipt_sha256"] = _receipt_hash(receipt)
    schema = workflow.load_json(root / "schemas" / "agent-execution-receipt.schema.json")
    workflow.validate_schema(receipt, schema, "agent execution receipt")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bounded offline qualification agent with durable checkpoints.")
    parser.add_argument("request", type=Path)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--max-steps", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = run_agent(
        workflow.load_json(args.request),
        state_root=args.state_root,
        workflow_id=args.workflow_id,
        max_steps=args.max_steps,
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(receipt, indent=2))
    return 0 if receipt["final_status"] in {"COMPLETED", "REPLAYED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
