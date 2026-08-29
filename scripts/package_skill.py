from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skill" / "qualify-environmental-evidence"
MANIFEST_PATH = SKILL_ROOT / "resource-manifest.json"
RESOURCE_PATHS = (
    "config/allowed-transformations.json",
    "config/evidence-sources.json",
    "config/forbidden-inferences.json",
    "config/reason-codes.json",
    "config/statement-templates.json",
    "schemas/assessment-output.schema.json",
    "schemas/claim-contract.schema.json",
    "schemas/provenance-manifest.schema.json",
    "cases/eop101132/case-spec.json",
    "policies/eop101132/step2b-proposed-policy.json",
    "policies/eop101132/step2b-proposed-policy-v4.json",
    "scripts/step2b_acquisition.py",
    "scripts/step2b_offline.py",
    "scripts/validate_step1_specs.py",
)
STATIC_PACKAGE_PATHS = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/authority-and-review.md",
    "references/contract-and-status.md",
    "references/evidence-identity.md",
    "references/provenance-and-cli.md",
    "resource-manifest.json",
    "scripts/qualify.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_manifest() -> dict[str, object]:
    return {
        "manifest_version": "1",
        "contract_version": "0.5.0",
        "resources": [{"path": relative, "sha256": sha256(ROOT / relative)} for relative in RESOURCE_PATHS],
    }


def unexpected_package_files() -> list[str]:
    expected = set(RESOURCE_PATHS).union(STATIC_PACKAGE_PATHS)
    found = {path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*") if path.is_file()}
    return sorted(found - expected)


def check() -> list[str]:
    failures: list[str] = []
    expected = expected_manifest()
    if not MANIFEST_PATH.is_file():
        return ["missing resource-manifest.json"]
    try:
        actual = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid resource-manifest.json: {exc}"]
    if actual != expected:
        failures.append("resource manifest is stale or hash-mismatched")
    for item in expected["resources"]:
        relative = item["path"]
        packaged = SKILL_ROOT / relative
        if not packaged.is_file():
            failures.append(f"missing packaged resource: {relative}")
        elif sha256(packaged) != item["sha256"]:
            failures.append(f"packaged resource differs from source of truth: {relative}")
    failures.extend(f"unexpected packaged file: {relative}" for relative in unexpected_package_files())
    return failures


def sync() -> None:
    for relative in RESOURCE_PATHS:
        source = ROOT / relative
        target = SKILL_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    MANIFEST_PATH.write_text(json.dumps(expected_manifest(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronise allowlisted contract resources into the installable skill.")
    parser.add_argument("--check", action="store_true", help="Fail if packaged resources or their manifest drifted.")
    args = parser.parse_args()
    if not args.check:
        sync()
    failures = check()
    if failures:
        for failure in failures:
            print(f"skill package check failed: {failure}", file=sys.stderr)
        return 1
    action = "checked" if args.check else "synchronised"
    print(f"Skill resources {action}: {len(RESOURCE_PATHS)} files; no drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
