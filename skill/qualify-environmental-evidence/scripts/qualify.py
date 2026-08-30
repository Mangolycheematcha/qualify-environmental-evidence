from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_MANIFEST = SKILL_ROOT / "resource-manifest.json"
STATIC_PACKAGE_PATHS = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/authority-and-review.md",
    "references/contract-and-status.md",
    "references/evidence-identity.md",
    "references/provenance-and-cli.md",
    "resource-manifest.json",
    "scripts/qualify.py",
}
EXIT_OK, EXIT_INVALID, EXIT_REFUSED, EXIT_RESOURCE_INTEGRITY, EXIT_INTERNAL = 0, 2, 3, 4, 5
CONTRACT_VERSION = "0.5.0"
contracts: Any = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_resources() -> list[str]:
    failures: list[str] = []
    try:
        manifest = json.loads(RESOURCE_MANIFEST.read_text(encoding="utf-8"))
        if set(manifest) != {"manifest_version", "contract_version", "resources"}:
            return ["resource manifest has unexpected or missing fields"]
        if manifest["manifest_version"] != "1" or manifest["contract_version"] != CONTRACT_VERSION:
            return ["resource manifest version mismatch"]
        entries = manifest["resources"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return [f"resource manifest unavailable or invalid: {exc}"]
    expected_paths: set[str] = set()
    for entry in entries:
        try:
            relative, expected_hash = entry["path"], entry["sha256"]
        except (KeyError, TypeError) as exc:
            failures.append(f"invalid resource manifest entry: {exc}")
            continue
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts or relative_path.as_posix() != relative:
            failures.append(f"unsafe resource path: {relative}")
            continue
        if relative in expected_paths:
            failures.append(f"duplicate resource entry: {relative}")
            continue
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            failures.append(f"invalid resource hash: {relative}")
            continue
        expected_paths.add(relative)
        path = SKILL_ROOT / relative
        if not path.is_file():
            failures.append(f"missing resource: {relative}")
        elif _sha256(path) != expected_hash:
            failures.append(f"hash mismatch: {relative}")
    found = {path.relative_to(SKILL_ROOT).as_posix() for path in SKILL_ROOT.rglob("*") if path.is_file()}
    allowed = expected_paths.union(STATIC_PACKAGE_PATHS)
    failures.extend(f"unexpected resource: {relative}" for relative in sorted(found - allowed))
    return failures


def _pending_reasons(case: dict[str, Any]) -> list[str]:
    reasons = ["RUNTIME_SPECIFICATION_NOT_FROZEN"]
    pending = set(case.get("pending_step_2", []))
    if "BOUNDARY_FILE_AND_CHECKSUM" in pending:
        reasons.append("BOUNDARY_NOT_FROZEN")
    if {"PRE_WINDOW", "POST_WINDOW"}.intersection(pending):
        reasons.append("TEMPORAL_SCOPE_NOT_FROZEN")
    if "SEASONAL_MATCHING_RULE" in pending:
        reasons.append("SEASONAL_RULE_NOT_FROZEN")
    return [code for code in contracts.REQUIRED_REASON_CODES if code in reasons]


def _result(outcome: str, *, status: str, disposition: str | None, reasons: list[str], human_review: bool, runtime_ready: bool, detail: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "outcome": outcome,
        "execution_status": status,
        "evidence_disposition": disposition,
        "reason_codes": reasons,
        "human_review_required": human_review,
        "runtime_ready": runtime_ready,
        "scientific_execution_available": False,
        "empirical_environmental_result": False,
        "detail": detail,
    }


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
    else:
        print(f"{payload['outcome']}: {payload['detail']}")


def _authority_refusal(case: dict[str, Any]) -> dict[str, Any] | None:
    claim = case.get("claim_contract")
    if not isinstance(claim, dict):
        return None
    if claim.get("authority_ceiling") != "OBSERVATIONAL_CONSISTENCY_ONLY" or claim.get("forbidden_inferences") != contracts.FORBIDDEN_CODES:
        return _result(
            "CONTROLLED_REFUSAL", status="REFUSED", disposition=None,
            reasons=["AUTHORITY_SCOPE_EXCEEDED"], human_review=True, runtime_ready=False,
            detail="The request exceeds the bounded observational authority ceiling.",
        )
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate contract-only environmental-evidence specifications without network access.")
    parser.add_argument("case", nargs="?", help="Path to a claim/case specification JSON file.")
    parser.add_argument("--assessment", help="Path to a linked assessment JSON file; requires --manifest.")
    parser.add_argument("--manifest", help="Path to a linked provenance manifest JSON file; requires --assessment.")
    parser.add_argument("--json", action="store_true", help="Emit one compact JSON object to stdout.")
    parser.add_argument("--check-resources", action="store_true", help="Verify packaged resource hashes and exit.")
    parser.add_argument("--approval-request", help="Strictly validate an Approval Protocol V2 request without network access.")
    return parser


def main(argv: list[str] | None = None) -> int:
    global contracts
    args = _parser().parse_args(argv)
    failures = check_resources()
    if failures:
        payload = _result(
            "RESOURCE_INTEGRITY_FAILURE", status="ERROR", disposition=None,
            reasons=["DETERMINISTIC_PROCESSING_ERROR"], human_review=True, runtime_ready=False,
            detail="; ".join(failures),
        )
        print(payload["detail"], file=sys.stderr)
        _emit(payload, args.json)
        return EXIT_RESOURCE_INTEGRITY
    if args.check_resources:
        payload = _result(
            "RESOURCES_VALID", status="ABSTAINED", disposition="INCONCLUSIVE",
            reasons=["RUNTIME_SPECIFICATION_NOT_FROZEN"], human_review=True, runtime_ready=False,
            detail="Packaged contract resources match resource-manifest.json.",
        )
        _emit(payload, args.json)
        return EXIT_OK
    if args.approval_request:
        try:
            import approval_protocol_v2

            request = approval_protocol_v2.read_json(Path(args.approval_request).resolve())
            approval_protocol_v2.validate_request(request)
            payload = _result(
                "VALID_APPROVAL_REQUEST_V2", status="ABSTAINED", disposition="INCONCLUSIVE",
                reasons=["HUMAN_REVIEW_REQUIRED"], human_review=True, runtime_ready=False,
                detail="Approval request bindings and canonical hash are valid; no approval evidence was retrieved or consumed.",
            )
            payload["approval_request_sha256"] = request["approval_request_sha256"]
            _emit(payload, args.json)
            return EXIT_OK
        except Exception as exc:
            payload = _result(
                "INVALID_APPROVAL_REQUEST_V2", status="ERROR", disposition=None,
                reasons=["APPROVAL_BINDING_INVALID"], human_review=True, runtime_ready=False,
                detail=str(exc),
            )
            print(str(exc), file=sys.stderr)
            _emit(payload, args.json)
            return EXIT_INVALID
    if not args.case:
        payload = _result(
            "INVALID_INVOCATION", status="ERROR", disposition=None,
            reasons=["REQUIRED_FIELD_MISSING"], human_review=True, runtime_ready=False,
            detail="case is required unless --check-resources is used",
        )
        print(payload["detail"], file=sys.stderr)
        _emit(payload, args.json)
        return EXIT_INVALID
    if bool(args.assessment) != bool(args.manifest):
        payload = _result(
            "INVALID_INVOCATION", status="ERROR", disposition=None,
            reasons=["REQUIRED_FIELD_MISSING"], human_review=True, runtime_ready=False,
            detail="--assessment and --manifest must be supplied together",
        )
        print(payload["detail"], file=sys.stderr)
        _emit(payload, args.json)
        return EXIT_INVALID
    try:
        import validate_step1_specs as packaged_contracts

        contracts = packaged_contracts
        loaded = contracts.load_contracts()
        contracts.validate_schemas(loaded["schemas"])
        contracts.validate_registries(loaded["registries"])
        case = contracts.load_json(Path(args.case).resolve())
        refusal = _authority_refusal(case)
        if refusal:
            print(refusal["detail"], file=sys.stderr)
            _emit(refusal, args.json)
            return EXIT_REFUSED
        contracts.validate_case(case, loaded["schemas"], loaded["registries"])
        if args.assessment:
            assessment = contracts.load_json(Path(args.assessment).resolve())
            manifest = contracts.load_json(Path(args.manifest).resolve())
            contracts.validate_linked_result(case, assessment, manifest, loaded["schemas"], loaded["registries"])
            payload = _result(
                "VALID_LINKED_CONTRACT", status=assessment["execution_status"],
                disposition=assessment["evidence_disposition"], reasons=assessment["reason_codes"],
                human_review=assessment["human_review_required"], runtime_ready=case["runtime_ready"],
                detail="The linked contract artifacts are valid; no environmental execution was performed.",
            )
            payload["artifact_runtime_mode"] = manifest["runtime_mode"]
        elif not case["runtime_ready"]:
            payload = _result(
                "VALID_SPECIFICATION_PENDING", status="ABSTAINED", disposition="INCONCLUSIVE",
                reasons=_pending_reasons(case), human_review=True, runtime_ready=False,
                detail="The bounded specification is valid but frozen scientific fields remain pending.",
            )
        else:
            payload = _result(
                "RUNTIME_EXECUTION_UNAVAILABLE", status="ABSTAINED", disposition="INCONCLUSIVE",
                reasons=["HUMAN_REVIEW_REQUIRED"], human_review=True, runtime_ready=True,
                detail="The contract is runtime-ready, but this skill does not implement scientific execution.",
            )
        _emit(payload, args.json)
        print(payload["detail"], file=sys.stderr)
        return EXIT_OK
    except contracts.ContractError as exc:
        payload = _result(
            "INVALID_CONTRACT", status="ERROR", disposition=None,
            reasons=["DETERMINISTIC_PROCESSING_ERROR"], human_review=True, runtime_ready=False, detail=str(exc),
        )
        print(str(exc), file=sys.stderr)
        _emit(payload, args.json)
        return EXIT_INVALID
    except Exception as exc:
        payload = _result(
            "INTERNAL_ERROR", status="ERROR", disposition=None,
            reasons=["DETERMINISTIC_PROCESSING_ERROR"], human_review=True, runtime_ready=False,
            detail=f"unexpected internal error: {exc}",
        )
        print(payload["detail"], file=sys.stderr)
        _emit(payload, args.json)
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
