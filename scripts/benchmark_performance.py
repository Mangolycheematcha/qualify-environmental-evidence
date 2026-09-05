from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

try:
    import qualification_workflow as workflow
    from retrieval_memory import build_index
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow
    from scripts.retrieval_memory import build_index


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evaluation" / "results" / "performance.json"
REQUEST = ROOT / "examples" / "qualification" / "eop101132-request.json"


def percentile(values: list[float], value: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * value) - 1)]


def measure(action: Callable[[], Any], count: int) -> list[float]:
    values = []
    for _ in range(count):
        started = time.perf_counter()
        action()
        values.append((time.perf_counter() - started) * 1000)
    return values


def summary(values: list[float]) -> dict[str, Any]:
    return {"samples": len(values), "p50_ms": round(statistics.median(values), 3), "p95_ms": round(percentile(values, 0.95), 3), "min_ms": round(min(values), 3), "max_ms": round(max(values), 3)}


def benchmark(root: Path = ROOT, cold_samples: int = 8, warm_samples: int = 40, retrieval_samples: int = 200) -> dict[str, Any]:
    command = [sys.executable, "-B", str(root / "scripts" / "qualification_workflow.py"), str(REQUEST), "--json"]
    cold = measure(lambda: subprocess.run(command, cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True), cold_samples)
    request_value = workflow.load_json(REQUEST)
    warm = measure(lambda: workflow.run_qualification(request_value, root=root), warm_samples)
    index = build_index(root)
    retrieval = {}
    for mode in ("lexical", "vector", "hybrid"):
        values = measure(lambda mode=mode: index.rank("EOP101132 frozen observational NDVI disposition", mode, subject_type="ACCU_PROJECT", subject_id="EOP101132"), retrieval_samples)
        retrieval[mode] = summary(values)
    report = {
        "report_version": "1.0.0",
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown")},
        "network_access": False,
        "live_eo_executed": False,
        "cold_process_end_to_end": {**summary(cold), "cache_state": "new Python interpreter each sample; operating-system disk cache uncontrolled"},
        "warm_process_end_to_end": {**summary(warm), "cache_state": "same Python interpreter; workflow schemas and evidence are intentionally rebuilt each call; OS cache warm"},
        "warm_in_memory_retrieval": retrieval,
        "model_provider_latency": {"samples": 0, "status": "NOT_MEASURED_NO_CREDENTIALS"},
        "model_provider_cost": {"samples": 0, "status": "NOT_MEASURED_NO_CREDENTIALS"},
    }
    report["report_sha256"] = workflow.sha256_bytes(workflow.canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark offline qualification and retrieval paths.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = benchmark()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
