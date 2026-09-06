from __future__ import annotations

import json
import math
import statistics
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import build_corpus_manifest, build_evaluation_corpus, build_retrieval_benchmark
from scripts import evaluate_model_comparisons, evaluate_qualification, evaluate_retrieval, evaluate_security
from scripts import qualification_session, qualification_workflow as workflow, run_e2e_demos
from scripts import model_provider
from scripts.retrieval_memory import CheckpointStore, EvidenceSnapshotStore, PreferenceStore, fact_text


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
    assert "does not independently prove an issuance event" in supported["bounded_statement"]
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
    assert evaluate_qualification.validate_partitions(benchmark["cases"]) == {
        "group_id": "PASS",
        "template_family": "PASS",
        "subject_partition_keys": "PASS",
        "target_evidence_ids": "PASS",
    }
    leaked = deepcopy(benchmark["cases"])
    next(item for item in leaked if item["split"] == "HELD_OUT")["subject_partition_keys"] = ["EOP101132"]
    with pytest.raises(workflow.QualificationError, match="subject_partition_keys leakage"):
        evaluate_qualification.validate_partitions(leaked)


def test_retrieval_benchmark_has_no_direct_labels_and_reports_small_hybrid_gain():
    benchmark = build_retrieval_benchmark.build()
    report = evaluate_retrieval.evaluate(benchmark)
    assert len(benchmark["cases"]) == 25
    assert report["modes"]["lexical"]["top1_accuracy"] == 22 / 25
    assert report["modes"]["vector"]["top1_accuracy"] == 22 / 25
    assert report["modes"]["hybrid"]["top1_accuracy"] == 23 / 25
    assert report["best_alternative_top1_gain"] == pytest.approx(1 / 25)
    assert report["single_candidate_query_count"] == 1
    assert report["materiality_threshold_provenance"].endswith("NOT_PREREGISTERED")
    assert report["decision"] == "RETAIN_LEXICAL_NO_EXTERNAL_VECTOR_INFRASTRUCTURE"
    assert all(case["expected_fact_id"].lower() not in case["question"].lower() for case in benchmark["cases"])
    first_fact = workflow.load_json(ROOT / "data" / "cer" / "eop101132-project-record.json")["facts"][0]
    assert first_fact["fact_id"].lower() not in fact_text(first_fact)
    assert fact_text(first_fact) == first_fact["text"].lower()
    leaked = deepcopy(benchmark)
    leaked["cases"][0]["question"] += " " + leaked["cases"][0]["expected_fact_id"]
    with pytest.raises(workflow.QualificationError, match="direct query-label leakage"):
        evaluate_retrieval.evaluate(leaked)


def test_memory_stores_are_separate_hash_checked_and_path_safe(tmp_path):
    document = workflow.load_json(ROOT / "data" / "cer" / "eop101132-project-record.json")
    digest = EvidenceSnapshotStore(tmp_path).put(document)
    assert EvidenceSnapshotStore(tmp_path).get(digest) == document
    checkpoints = CheckpointStore(tmp_path)
    first_checkpoint_hash = checkpoints.put("FLOW-A", 1, {"stage": "A"})
    assert checkpoints.put("FLOW-A", 1, {"stage": "A"}) == first_checkpoint_hash
    with pytest.raises(workflow.QualificationError, match="immutable store collision"):
        checkpoints.put("FLOW-A", 1, {"stage": "changed"})
    with pytest.raises(workflow.QualificationError, match="must append at 2"):
        checkpoints.put("FLOW-A", 3, {"stage": "skipped"})
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
    paths_before = sorted((path.relative_to(tmp_path), path.read_bytes()) for path in tmp_path.rglob("*.json"))
    replayed = qualification_session.run_resumable(req, state_root=tmp_path, workflow_id="FLOW")
    paths_after = sorted((path.relative_to(tmp_path), path.read_bytes()) for path in tmp_path.rglob("*.json"))
    assert paused["session_status"] == "PAUSED"
    assert completed["session_status"] == "COMPLETED" and replayed["session_status"] == "REPLAYED"
    assert workflow.canonical_bytes(completed["result"]) == workflow.canonical_bytes(replayed["result"])
    assert paths_before == paths_after


def test_e2e_security_and_provider_status_are_honest(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    e2e = run_e2e_demos.build()
    security = evaluate_security.evaluate()
    provider = evaluate_model_comparisons.status_report("UNSELECTED_SAME_MODEL_REQUIRED")
    assert e2e["status"] == "PASS" and e2e["journey_count"] == 4
    assert security["status"] == "PASS" and security["executed_case_count"] == 7
    assert security["not_applicable_case_count"] == 3
    assert provider["arms"]["B0"] == {"planned_cases": 27, "completed_cases": 0, "status": "NOT_EXECUTED"}
    assert provider["human_evaluation"]["planned_cases"] == 27
    assert provider["human_evaluation"]["completed_cases"] == 0
    assert provider["human_evaluation"]["status"] == "NOT_EXECUTED"
    assert provider["provider"]["fixture_is_behavioural_evidence"] is False


def test_performance_artifact_percentiles_recompute_from_recorded_samples():
    report = workflow.load_json(ROOT / "evaluation" / "results" / "performance.json")
    sections = [report["cold_process_end_to_end"], report["warm_process_end_to_end"]]
    sections.extend(report["warm_in_memory_retrieval"].values())
    for section in sections:
        samples = section["samples_ms"]
        assert section["samples"] == len(samples)
        assert section["p50_ms"] == round(statistics.median(samples), 3)
        rank = max(0, math.ceil(len(samples) * 0.95) - 1)
        assert section["p95_ms"] == round(sorted(samples)[rank], 3)


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
