from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import qualification_workflow as workflow
    import retrieval_memory
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow
    from scripts import retrieval_memory


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "evaluation" / "retrieval-benchmark.json"
RESULT = ROOT / "evaluation" / "results" / "retrieval-comparison.json"


def evaluate(benchmark: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    if benchmark.get("split") != "CONTROLLED_FROZEN_QUERY_SET" or benchmark.get("query_count") != len(benchmark.get("cases", [])):
        raise workflow.QualificationError("retrieval benchmark is not a valid controlled query set")
    if benchmark.get("direct_label_leakage_check") != "PASS" or benchmark.get("ranking_text_fields") != ["text"]:
        raise workflow.QualificationError("retrieval benchmark leakage controls are missing")
    for case in benchmark["cases"]:
        question = case["question"].lower()
        if case["expected_fact_id"].lower() in question or case["subject_id"].lower() in question:
            raise workflow.QualificationError(f"direct query-label leakage: {case['query_id']}")
    index = retrieval_memory.build_index(root)
    modes: dict[str, Any] = {}
    for mode in ("lexical", "vector", "hybrid"):
        top1 = recall3 = 0
        reciprocal_ranks = []
        records = []
        for case in benchmark["cases"]:
            ranking = index.rank(
                case["question"],
                mode,
                limit=len(index.facts),
                subject_type=case["subject_type"],
                subject_id=case["subject_id"],
            )
            ranked_ids = [item[0] for item in ranking]
            expected = case["expected_fact_id"]
            rank = ranked_ids.index(expected) + 1 if expected in ranked_ids else None
            top1 += int(rank == 1)
            recall3 += int(rank is not None and rank <= 3)
            reciprocal_ranks.append(1 / rank if rank else 0.0)
            records.append({"query_id": case["query_id"], "expected_fact_id": expected, "candidate_count": len(ranked_ids), "rank": rank, "top3": ranked_ids[:3]})
        count = len(benchmark["cases"])
        modes[mode] = {
            "query_count": count,
            "top1_accuracy": top1 / count,
            "recall_at_3": recall3 / count,
            "mean_reciprocal_rank": sum(reciprocal_ranks) / count,
            "records": records,
        }
    lexical = modes["lexical"]
    vector = modes["vector"]
    hybrid = modes["hybrid"]
    best_alternative = max(vector["top1_accuracy"], hybrid["top1_accuracy"])
    top1_gain = best_alternative - lexical["top1_accuracy"]
    material_gain_min = 0.05
    material_gain = top1_gain >= material_gain_min
    deterministic = {
        "benchmark_sha256": benchmark["cases_sha256"],
        "mode_metrics": {mode: {key: value for key, value in result.items() if key != "records"} for mode, result in modes.items()},
        "best_alternative_top1_gain": top1_gain,
        "material_top1_gain_min": material_gain_min,
        "materiality_threshold_provenance": "ADDED_DURING_2026-09-06_AUDIT_NOT_PREREGISTERED",
        "single_candidate_query_count": sum(record["candidate_count"] == 1 for record in lexical["records"]),
        "decision": "EVALUATE_VECTOR_FOR_PRODUCTION" if material_gain else "RETAIN_LEXICAL_NO_EXTERNAL_VECTOR_INFRASTRUCTURE",
    }
    return {
        "result_version": "2.0.0",
        "evaluation_scope": "CONTROLLED_ENGINEERING_RELEVANCE_NOT_INDEPENDENT_HUMAN_GOLD",
        "query_provenance": benchmark["query_provenance"],
        "ranking_text_fields": benchmark["ranking_text_fields"],
        "metadata_filters": benchmark["metadata_filters"],
        "direct_label_leakage_check": benchmark["direct_label_leakage_check"],
        **deterministic,
        "result_sha256": workflow.sha256_bytes(workflow.canonical_bytes(deterministic)),
        "modes": modes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare lexical, local vector and hybrid retrieval.")
    parser.add_argument("--write", action="store_true", help="Write the deterministic result artifact.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(workflow.load_json(BENCHMARK))
    if args.write:
        RESULT.parent.mkdir(parents=True, exist_ok=True)
        RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
