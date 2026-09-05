from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "cer" / "corpus-manifest.json"


def build(root: Path = ROOT) -> dict[str, Any]:
    schema = workflow.load_json(root / "schemas" / "evidence-memory-document.schema.json")
    policy = workflow.load_json(root / "config" / "semantic-boundaries.json")
    paths = workflow.default_evidence_paths(root)[:-1]
    memory = workflow.EvidenceMemory.from_paths(paths, schema, policy["source_policies"])
    records = []
    counts: dict[str, int] = {}
    for path in paths:
        document = workflow.load_json(path)
        subject_type = document["subject"]["subject_type"]
        counts[subject_type] = counts.get(subject_type, 0) + 1
        records.append({
            "evidence_id": document["evidence_id"],
            "subject_type": subject_type,
            "subject_id": document["subject"]["subject_id"],
            "snapshot_path": path.relative_to(root).as_posix(),
            "snapshot_sha256": workflow.sha256_bytes(path.read_bytes()),
            "source_uri": document["source"]["canonical_uri"],
            "source_accessed_on": document["source"]["accessed_on"],
            "source_content_sha256": document["source"].get("source_content_sha256"),
            "source_content_bytes": document["source"].get("source_content_bytes"),
            "redistribution_status": document["source"].get("redistribution_status", "SOURCE_TERMS_APPLY"),
        })
    return {
        "manifest_version": "1.0.0",
        "generated_from": "CURATED_FACT_SNAPSHOTS",
        "document_count": len(records),
        "subject_type_counts": dict(sorted(counts.items())),
        "public_memory_snapshot_sha256": memory.snapshot_sha256,
        "records": records,
    }


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the curated CER corpus manifest.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    expected = render(build())
    if args.check:
        if not MANIFEST.is_file() or MANIFEST.read_text(encoding="utf-8") != expected:
            print("corpus manifest is missing or stale", file=sys.stderr)
            return 1
        print("CER corpus manifest valid")
        return 0
    MANIFEST.write_text(expected, encoding="utf-8")
    print(f"Wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
