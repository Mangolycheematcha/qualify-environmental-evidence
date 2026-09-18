from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import pytest

from scripts import agent_runtime
from scripts import evaluate_agent_runtime
from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "examples" / "qualification" / "eop101132-request.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_agent_loop_completes_with_receipt_and_preserved_evidence(tmp_path):
    receipt = agent_runtime.run_agent(
        load(REQUEST),
        state_root=tmp_path,
        workflow_id="TEST-AGENT",
        max_steps=3,
    )
    assert receipt["final_status"] == "COMPLETED"
    assert [step["action"] for step in receipt["steps"]] == [
        "VALIDATE_REQUEST",
        "SNAPSHOT_EVIDENCE",
        "QUALIFY",
    ]
    assert len(receipt["evidence_snapshot_sha256s"]) == 10
    assert len(list((tmp_path / "evidence").glob("*.json"))) == 10
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    assert hashlib.sha256(workflow.canonical_bytes(unsigned)).hexdigest() == receipt["receipt_sha256"]


def test_step_budget_pauses_then_resume_completes(tmp_path):
    request = load(REQUEST)
    paused = agent_runtime.run_agent(
        request,
        state_root=tmp_path,
        workflow_id="TEST-BUDGET",
        max_steps=1,
    )
    assert paused["final_status"] == "PAUSED"
    assert paused["stop_reason"] == "STEP_BUDGET_EXHAUSTED"
    resumed = agent_runtime.run_agent(
        request,
        state_root=tmp_path,
        workflow_id="TEST-BUDGET",
        max_steps=2,
    )
    assert resumed["final_status"] == "COMPLETED"
    assert [step["action"] for step in resumed["steps"]] == ["SNAPSHOT_EVIDENCE", "QUALIFY"]


def test_completed_replay_is_side_effect_free(tmp_path):
    request = load(REQUEST)
    completed = agent_runtime.run_agent(
        request,
        state_root=tmp_path,
        workflow_id="TEST-REPLAY",
        max_steps=3,
    )
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.json"))
    replayed = agent_runtime.run_agent(
        request,
        state_root=tmp_path,
        workflow_id="TEST-REPLAY",
        max_steps=1,
    )
    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.json"))
    assert replayed["final_status"] == "REPLAYED"
    assert replayed["stop_reason"] == "ALREADY_COMPLETE"
    assert completed["result_sha256"] == replayed["result_sha256"]
    assert before == after


def test_resume_rejects_changed_request(tmp_path):
    request = load(REQUEST)
    agent_runtime.run_agent(request, state_root=tmp_path, workflow_id="TEST-MISMATCH", max_steps=1)
    request["question"] = request["question"] + " changed"
    with pytest.raises(workflow.QualificationError, match="resume request hash mismatch"):
        agent_runtime.run_agent(request, state_root=tmp_path, workflow_id="TEST-MISMATCH", max_steps=2)


def test_agent_runtime_performs_no_network(monkeypatch, tmp_path):
    def blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    receipt = agent_runtime.run_agent(
        load(REQUEST),
        state_root=tmp_path,
        workflow_id="TEST-OFFLINE",
        max_steps=3,
    )
    assert receipt["network_access"] is False
    assert receipt["external_action_count"] == 0


def test_agent_runtime_evaluation_passes_and_matches_committed_artifact():
    report = evaluate_agent_runtime.build()
    assert report["status"] == "PASS"
    assert all(report["checks"].values())
    assert load(ROOT / "evaluation" / "results" / "agent-runtime-evaluation.json") == report
