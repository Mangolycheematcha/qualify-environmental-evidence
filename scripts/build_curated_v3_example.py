from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "EOP101132-STEP2B-20260829T105228553596Z-be9fe09f"
RUN = ROOT / "runs" / RUN_ID
DESTINATION = ROOT / "examples" / "eop101132-v3-abstained"
V3_POLICY_SHA256 = "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


def write_text_lf(path: Path, value: str, encoding: str = "utf-8") -> None:
    path.write_bytes(value.replace("\r\n", "\n").encode(encoding))


def redact_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def redact_inventory_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {name: redact_inventory_value(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [redact_inventory_value(item, key) for item in value]
    if isinstance(value, str) and (key or "").endswith(("_identity", "_uri", "_url")):
        return redact_url(value)
    return value


def build() -> None:
    if not RUN.is_dir():
        raise FileNotFoundError(f"local immutable V3 run is required at {RUN}")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name in ("assessment.json", "provenance-manifest.json"):
        shutil.copyfile(RUN / name, DESTINATION / name)
    write_text_lf(DESTINATION / "run-summary.md", (RUN / "run-summary.md").read_text(encoding="utf-8"))
    write_text_lf(
        DESTINATION / "final-report.md",
        (ROOT / "STEP2B_EOP101132_FINAL_REPORT.md").read_text(encoding="utf-8"),
    )
    inventory = json.loads((RUN / "inventory" / "scene-inventory.json").read_text(encoding="utf-8"))
    write_text_lf(
        DESTINATION / "scene-inventory.redacted.json",
        canonical_json(redact_inventory_value(inventory)),
    )
    binding = {
        "run_id": RUN_ID,
        "policy_id": "DEMO_QUALIFICATION_POLICY_EOP101132_V3",
        "approved_policy_sha256": V3_POLICY_SHA256,
        "assessment_sha256": "f46822f29ef00c511fdc340c3adf240b5255aa6aec9e9a32e0dd692d1217dcf9",
        "provenance_sha256": "69d3e3c0b054dc9f4ba2ac9610332a78e6ed104b53e115cb5539be39f434e407",
        "terminal_result": {
            "execution_status": "ABSTAINED",
            "evidence_disposition": "INCONCLUSIVE",
            "reason_code": "RESOURCE_LIMIT_EXCEEDED",
        },
        "curation_status": "SAFE_DERIVATIVES_ONLY",
    }
    write_text_lf(DESTINATION / "policy-binding.json", canonical_json(binding))
    readme = """# Curated V3 Abstained Run Example

This directory contains reviewed derivatives from the immutable live V3 run. It is not the complete runtime evidence package and does not replace the locally preserved `runs/` directory.

This live run reached the official CER and Planetary Computer STAC
sources but stopped before raster access because the frozen raw-item
resource limit was exceeded. It produced no coverage, NDVI or
environmental qualification result.

The 58 discovered STAC items were unevaluated because execution stopped at the resource gate. They must not be described as inadmissible. Canonical asset identities in the redacted inventory contain no signed query parameters. Raw HTTP payloads, headers, caches, raster data, AOI chips, signed URLs, credentials, and local machine paths are excluded.

No affiliation, endorsement, regulatory approval, scientific validation, carbon conclusion, credit-quality conclusion, or financial conclusion is asserted.
"""
    write_text_lf(DESTINATION / "README.md", readme)
    checksum_rows = []
    for path in sorted(DESTINATION.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "checksums.sha256":
            checksum_rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    write_text_lf(DESTINATION / "checksums.sha256", "\n".join(checksum_rows) + "\n", encoding="ascii")


def expected_files() -> set[str]:
    return {
        "README.md",
        "assessment.json",
        "checksums.sha256",
        "final-report.md",
        "policy-binding.json",
        "provenance-manifest.json",
        "run-summary.md",
        "scene-inventory.redacted.json",
    }


def check() -> list[str]:
    failures: list[str] = []
    found = {path.name for path in DESTINATION.iterdir() if path.is_file()} if DESTINATION.is_dir() else set()
    if found != expected_files():
        failures.append(f"curated file set differs: expected={sorted(expected_files())}, found={sorted(found)}")
    checksums = DESTINATION / "checksums.sha256"
    if checksums.is_file():
        for line in checksums.read_text(encoding="ascii").splitlines():
            expected, name = line.split("  ", 1)
            path = DESTINATION / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                failures.append(f"curated checksum mismatch: {name}")
    else:
        failures.append("curated checksums.sha256 is missing")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed, public-safe derivative of the local V3 run.")
    parser.add_argument("--check", action="store_true", help="Validate the checked-in curated example.")
    args = parser.parse_args()
    if not args.check:
        build()
    failures = check()
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"Curated V3 example valid: {len(expected_files())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
