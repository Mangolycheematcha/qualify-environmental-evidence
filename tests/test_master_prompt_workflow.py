from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_corpus_manifest, build_evaluation_corpus, build_retrieval_benchmark
from scripts import evaluate_model_comparisons, evaluate_retrieval, evaluate_security
from scripts import qualification_session, qualification_workflow as workflow, run_e2e_demos
from scripts import model_provider
from scripts.retrieval_memory import CheckpointStore, EvidenceSnapshotStore, PreferenceStore


ROOT = Path(__file__).resolve().parents[1]


def request(subject_type="ACCU_PROJECT", subject_id="EOP101132", family="REGISTRY_FACTS"):
    return {"schema_version": "1.0.0", "request_id": "TEST-MASTER", "subject_type": subject_type, "subject_id": subject_id, "claim_family": family, "question": "Return a bounded and source-attributed qualification memo for this subject.", "requested_output": "BOUNDED_EVIDENCE_MEMO"}


def test_corpus_has_seven_real_accu_projects_and_one_safeguard_record():
    manifest = build_corpus_manifest.build()
    assert manifest["document_count"] == 9
    assert manifest["subject_type_counts"] == {"ACCU_PROJECT": 7, "SAFEGUARD_FACILITY": 1, "UNIT_CONCEPTS": 1}
    assert all(item.get("source_content_sha256") for item in manifest["records"])


def test_real_safeguard_record_does_not_transfer_to_accu_semantics():
    supported = workflow.run_qualification(request("SAFEGUARD_FACILITY", "SAFEGUARD.2024-25.ARCADIA", "SAFEGUARD_FACILITY_FACTS"))
    assert supported["workflow_status"] == "QUALIFIED"
    assert "not an ACCU project record" in supported["bounded_statement"]
    mismatch = workflow.run_qualification(request("ACCU_PROJECT", "EOP101132", "SAFEGUARD_FACILITY_FACTS"))
    assert mismatch["reason_codes"] == ["ENTITY_TYPE_MISMATCH"]


def test_conflicting_assertions_fail_closed():
    paths = [ROOT / "evaluation" / "fixtures" / f"conflict-{suffix}.json" for suffix in ("a", "b")]
    result = workflow.run_qualification(request("ACCU_PROJECT", "SYNTHETIC-CONFLICT"), evidence_paths=paths)
    assert result["workflow_status"] == "ERROR"
    assert result["reason_codes"] == ["EVIDENCE_CONFLICT_UNRESOLVED"]
    assert result["assurance_checks"]["evidence_consistency"] == "FAIL"


def test_evaluation_corpus_is_group_frozen_without_leakage():
    benchmark, freeze = build_evaluation_corpus.build()
    assert benchmark["case_count"] == 80
    assert freeze["held_out_case_count"] == 27
    group_splits = {}
    for case in benchmark["cases"]:
        assert group_splits.setdefault(case["group_id"], case["split"]) == case["split"]


def test_retrieval_benchmark_and_comparison_are_frozen_and_perfectly_tied():
    benchmark = build_retrieval_benchmark.build()
    report = evaluate_retrieval.evaluate(benchmark)
    assert len(benchmark["cases"]) == 25
    assert {value["top1_accuracy"] for value in report["mode_metrics"].values()} == {1.0}
    assert report["decision"] == "RETAIN_LEXICAL_NO_EXTERNAL_VECTOR_INFRASTRUCTURE"


def test_memory_stores_are_separate_hash_checked_and_path_safe(tmp_path):
    document = workflow.load_json(ROOT / "data" / "cer" / "eop101132-project-record.json")
    digest = EvidenceSnapshotStore(tmp_path).put(document)
    assert EvidenceSnapshotStore(tmp_path).get(digest) == document
    CheckpointStore(tmp_path).put("FLOW-A", 1, {"stage": "A"})
    PreferenceStore(tmp_path).put("SESSION-A", {"locale": "en-AU"})
    assert (tmp_path / "evidence").is_dir() and (tmp_path / "checkpoints").is_dir() and (tmp_path / "preferences").is_dir()
    with pytest.raises(workflow.QualificationError):
        CheckpointStore(tmp_path).put("../escape", 1, {})
    with pytest.raises(workflow.QualificationError):
        PreferenceStore(tmp_path).put("SESSION-A", {"api_key": "no"})


def test_resumable_session_replays_identical_result_bytes(tmp_path):
    req = request(subject_id="EOP101053")
    paused = qualification_session.run_resumable(req, state_root=tmp_path, workflow_id="FLOW", stop_after="EVIDENCE_SNAPSHOTTED")
    completed = qualification_session.run_resumable(req, state_root=tmp_path, workflow_id="FLOW")
    replayed = qualification_session.run_resumable(req, state_root=tmp_path, workflow_id="FLOW")
    assert paused["session_status"] == "PAUSED"
    assert completed["session_status"] == "COMPLETED" and replayed["session_status"] == "REPLAYED"
    assert workflow.canonical_bytes(completed["result"]) == workflow.canonical_bytes(replayed["result"])


def test_e2e_security_and_provider_status_are_honest(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    e2e = run_e2e_demos.build()
    security = evaluate_security.evaluate()
    provider = evaluate_model_comparisons.status_report("UNSELECTED_SAME_MODEL_REQUIRED")
    assert e2e["status"] == "PASS" and e2e["journey_count"] == 4
    assert security["status"] == "PASS" and security["executed_case_count"] == 8
    assert provider["arms"]["B0"]["executed"] == 0
    assert provider["human_evaluation"]["independently_labelled"] == 0
    assert provider["provider"]["fixture_is_behavioural_evidence"] is False


def test_openai_responses_adapter_contract_without_network(monkeypatch):
    captured = {}
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self):
            return json.dumps({"output": [{"content": [{"type": "output_text", "text": json.dumps({"workflow_status": "ABSTAINED", "qualification": "INCONCLUSIVE", "reason_codes": ["TEST"], "bounded_statement": "Bounded."})}]}]}).encode()
    def fake_urlopen(http_request, timeout):
        captured["body"] = json.loads(http_request.data)
        captured["timeout"] = timeout
        return Response()
    monkeypatch.setattr(model_provider.urllib.request, "urlopen", fake_urlopen)
    provider = model_provider.OpenAIResponsesProvider(api_key="test-only")
    result = provider.qualify(request(), {"facts": []}, model_provider.ProviderSettings(model="same-model"))
    assert result["workflow_status"] == "ABSTAINED"
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    assert captured["body"]["model"] == "same-model"
