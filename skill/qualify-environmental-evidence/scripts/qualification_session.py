from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import qualification_workflow as workflow
    from retrieval_memory import CheckpointStore, EvidenceSnapshotStore
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow
    from scripts.retrieval_memory import CheckpointStore, EvidenceSnapshotStore


STAGES = ("REQUEST_VALIDATED", "EVIDENCE_SNAPSHOTTED", "COMPLETE")


def run_resumable(
    request: dict[str, Any],
    *,
    state_root: Path,
    workflow_id: str,
    root: Path = workflow.ROOT,
    stop_after: str | None = None,
) -> dict[str, Any]:
    request_hash = workflow.sha256_bytes(workflow.canonical_bytes(request))
    checkpoints = CheckpointStore(state_root)
    latest = checkpoints.latest(workflow_id)
    sequence = 0
    completed: set[str] = set()
    evidence_hashes: list[str] = []
    if latest:
        sequence, state = latest
        if state["request_sha256"] != request_hash:
            raise workflow.QualificationError("resume request hash mismatch")
        completed = set(state["completed_stages"])
        evidence_hashes = list(state.get("evidence_snapshot_sha256s", []))
        if "COMPLETE" in completed:
            result = state["result"]
            unsigned = {key: value for key, value in result.items() if key != "result_sha256"}
            if workflow.sha256_bytes(workflow.canonical_bytes(unsigned)) != result["result_sha256"]:
                raise workflow.QualificationError("checkpoint result hash mismatch")
            return {"session_status": "REPLAYED", "result": result, "checkpoint_sequence": sequence}

    if "REQUEST_VALIDATED" not in completed:
        schema = workflow.load_json(root / "schemas" / "qualification-request.schema.json")
        workflow.validate_schema(request, schema, "qualification request")
        completed.add("REQUEST_VALIDATED")
        sequence += 1
        checkpoints.put(workflow_id, sequence, {"request_sha256": request_hash, "completed_stages": sorted(completed)})
        if stop_after == "REQUEST_VALIDATED":
            return {"session_status": "PAUSED", "checkpoint_sequence": sequence}

    if "EVIDENCE_SNAPSHOTTED" not in completed:
        evidence_store = EvidenceSnapshotStore(state_root)
        evidence_hashes = [evidence_store.put(workflow.load_json(path)) for path in workflow.default_evidence_paths(root)]
        completed.add("EVIDENCE_SNAPSHOTTED")
        sequence += 1
        checkpoints.put(workflow_id, sequence, {
            "request_sha256": request_hash,
            "completed_stages": sorted(completed),
            "evidence_snapshot_sha256s": sorted(evidence_hashes),
        })
        if stop_after == "EVIDENCE_SNAPSHOTTED":
            return {"session_status": "PAUSED", "checkpoint_sequence": sequence, "evidence_count": len(evidence_hashes)}

    if not evidence_hashes:
        raise workflow.QualificationError("checkpoint is missing bound evidence snapshots")
    evidence_paths = [EvidenceSnapshotStore(state_root).root / f"{digest}.json" for digest in evidence_hashes]
    result = workflow.run_qualification(request, root=root, evidence_paths=evidence_paths)
    completed.add("COMPLETE")
    sequence += 1
    checkpoints.put(workflow_id, sequence, {
        "request_sha256": request_hash,
        "completed_stages": sorted(completed),
        "evidence_snapshot_sha256s": sorted(evidence_hashes),
        "result": result,
    })
    return {"session_status": "COMPLETED", "result": result, "checkpoint_sequence": sequence}
