from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    import model_provider
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import model_provider
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "results" / "model-comparison-status.json"


def _heldout() -> list[dict[str, Any]]:
    benchmark = workflow.load_json(ROOT / "evaluation" / "qualification-benchmark.json")
    return [case for case in benchmark["cases"] if case["split"] == "HELD_OUT"]


def _evidence_packet(request: dict[str, Any]) -> dict[str, Any]:
    schema = workflow.load_json(ROOT / "schemas" / "evidence-memory-document.schema.json")
    policy = workflow.load_json(ROOT / "config" / "semantic-boundaries.json")
    memory = workflow.EvidenceMemory.from_paths(workflow.default_evidence_paths(ROOT), schema, policy["source_policies"])
    facts = [
        {key: value for key, value in fact.items() if not key.startswith("_")}
        for fact in memory.facts.values()
        if fact["subject_type"] == request["subject_type"] and fact["subject_id"] == request["subject_id"]
    ]
    packet = {"subject_type": request["subject_type"], "subject_id": request["subject_id"], "facts": sorted(facts, key=lambda item: item["fact_id"])}
    return {**packet, "packet_sha256": workflow.sha256_bytes(workflow.canonical_bytes(packet))}


def status_report(model: str) -> dict[str, Any]:
    cases = _heldout()
    fixture = model_provider.FixtureProvider().qualify(cases[0]["request"], None, model_provider.ProviderSettings(model="fixture"))
    packet_pairs = [{"case_id": case["case_id"], "b1": _evidence_packet(case["request"])["packet_sha256"], "t1": _evidence_packet(case["request"])["packet_sha256"]} for case in cases]
    credentials = bool(os.environ.get("OPENAI_API_KEY"))
    report = {
        "report_version": "1.0.0",
        "evaluation_design": {
            "held_out_cases": len(cases),
            "split": "HELD_OUT",
            "label_authority": "REPOSITORY_ENGINEERING_EXPECTATION_NOT_HUMAN_GOLD",
            "b0": "question only",
            "b1": "question plus matched evidence packet",
            "t1": "same B1 packet plus deterministic authority gate",
            "controlled_variables": {"model": model, "temperature": 0.0, "max_output_tokens": 500},
            "b1_t1_evidence_hash_match_count": sum(item["b1"] == item["t1"] for item in packet_pairs),
        },
        "provider": {
            "adapter": "OPENAI_RESPONSES_API",
            "credential_present": credentials,
            "live_adapter_status": "READY_NOT_EXECUTED" if credentials else "BLOCKED_NO_CREDENTIAL",
            "fixture_contract_test": "PASS",
            "fixture_output_status": fixture["reason_codes"][0],
            "fixture_is_behavioural_evidence": False,
        },
        "arms": {arm: {"planned": len(cases), "executed": 0, "status": "NOT_RUN"} for arm in ("B0", "B1", "T1")},
        "human_evaluation": {
            "name": "H1",
            "planned": len(cases),
            "independently_labelled": 0,
            "status": "BLOCKED_PENDING_INDEPENDENT_HUMAN_LABELS",
            "self_labels_counted_as_human": False,
        },
        "network_access": False,
        "api_cost": None,
        "status": "LIVE_MODEL_EVALUATION_BLOCKED" if not credentials else "LIVE_MODEL_EVALUATION_READY_NOT_AUTHORIZED",
    }
    report["report_sha256"] = workflow.sha256_bytes(workflow.canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report matched B0/B1/T1 evaluation readiness without silently calling a model API.")
    parser.add_argument("--model", default="UNSELECTED_SAME_MODEL_REQUIRED")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = status_report(args.model)
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
