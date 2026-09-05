from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

try:
    import qualification_workflow as workflow
except ModuleNotFoundError:  # Support `python -m scripts.evaluate_qualification`.
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "evaluation" / "qualification-benchmark.json"


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def evaluate(benchmark: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    cases = benchmark.get("cases")
    if not isinstance(cases, list) or not cases:
        raise workflow.QualificationError("benchmark must contain at least one case")
    case_results: list[dict[str, Any]] = []
    exact = deterministic = unsupported = security_passed = 0
    security_total = 0
    refusal_total = refusal_passed = 0
    latencies: list[float] = []
    deterministic_records: list[dict[str, Any]] = []

    for case in cases:
        start = time.perf_counter()
        first = workflow.run_qualification(case["request"], root=root)
        latency_ms = (time.perf_counter() - start) * 1000
        second = workflow.run_qualification(case["request"], root=root)
        latencies.append(latency_ms)
        expected = {
            "workflow_status": case["expected_workflow_status"],
            "qualification": case["expected_qualification"],
            "reason_codes": case["expected_reason_codes"],
        }
        actual = {key: first[key] for key in expected}
        exact_match = actual == expected
        deterministic_match = workflow.canonical_bytes(first) == workflow.canonical_bytes(second)
        unsupported_assertion = (
            first["assurance_checks"]["non_inference"] != "PASS"
            or (first["workflow_status"] == "QUALIFIED" and not first["evidence_refs"])
            or (first["workflow_status"] == "REFUSED" and first["bounded_statement"] is not None)
        )
        if exact_match:
            exact += 1
        if deterministic_match:
            deterministic += 1
        if unsupported_assertion:
            unsupported += 1
        if case.get("security_case"):
            security_total += 1
            if exact_match and first["assurance_checks"]["non_inference"] == "PASS":
                security_passed += 1
        if case["expected_workflow_status"] == "REFUSED":
            refusal_total += 1
            if first["workflow_status"] == "REFUSED" and not first["evidence_refs"]:
                refusal_passed += 1
        record = {
            "case_id": case["case_id"],
            "actual": actual,
            "exact_match": exact_match,
            "deterministic_replay": deterministic_match,
            "unsupported_assertion": unsupported_assertion,
            "result_sha256": first["result_sha256"],
        }
        deterministic_records.append(record)
        case_results.append({**record, "latency_ms": round(latency_ms, 3)})

    total = len(cases)
    metrics = {
        "case_count": total,
        "exact_outcome_rate": _rate(exact, total),
        "forbidden_request_refusal_rate": _rate(refusal_passed, refusal_total),
        "deterministic_replay_rate": _rate(deterministic, total),
        "unsupported_assertion_rate": _rate(unsupported, total),
        "security_case_pass_rate": _rate(security_passed, security_total),
        "p95_latency_ms": round(_percentile_nearest_rank(latencies, 0.95), 3),
    }
    thresholds = benchmark["thresholds"]
    checks = {
        "exact_outcome": metrics["exact_outcome_rate"] >= thresholds["exact_outcome_rate_min"],
        "forbidden_request_refusal": metrics["forbidden_request_refusal_rate"] >= thresholds["forbidden_request_refusal_rate_min"],
        "deterministic_replay": metrics["deterministic_replay_rate"] >= thresholds["deterministic_replay_rate_min"],
        "unsupported_assertion": metrics["unsupported_assertion_rate"] <= thresholds["unsupported_assertion_rate_max"],
        "security_cases": metrics["security_case_pass_rate"] >= thresholds["security_case_pass_rate_min"],
        "performance": metrics["p95_latency_ms"] <= thresholds["p95_latency_ms_max"],
    }
    outcome_sha256 = workflow.sha256_bytes(workflow.canonical_bytes({
        "benchmark_version": benchmark["benchmark_version"],
        "case_results": deterministic_records,
    }))
    return {
        "evaluation_schema_version": "1.0.0",
        "benchmark_version": benchmark["benchmark_version"],
        "evaluation_mode": benchmark["evaluation_mode"],
        "network_access": False,
        "model_api_used": False,
        "hallucination_evaluation_scope": "DETERMINISTIC_UNSUPPORTED_ASSERTION_PROXY_ONLY",
        "metrics": metrics,
        "threshold_checks": checks,
        "deterministic_outcomes_sha256": outcome_sha256,
        "case_results": case_results,
        "evaluation_status": "PASS" if all(checks.values()) else "FAIL",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the offline qualification workflow.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = evaluate(workflow.load_json(args.benchmark.resolve()))
    except workflow.QualificationError as exc:
        print(json.dumps({"outcome": "INVALID_EVALUATION_INPUT", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(report, indent=2))
    return 0 if report["evaluation_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
