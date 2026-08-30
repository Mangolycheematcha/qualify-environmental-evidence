from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


APPROVAL_PROTOCOL_VERSION = "2.0.0"
CANONICALISATION_ID = "CANONICAL_JSON_V1"
EXPECTED_REPOSITORY = "Mangolycheematcha/qualify-environmental-evidence"
EXPECTED_APPROVER_LOGIN = "Mangolycheematcha"
ALLOWED_EVIDENCE_TYPES = ("GITHUB_ISSUE", "GITHUB_ISSUE_COMMENT")
POLICY_ID = "DEMO_QUALIFICATION_POLICY_EOP101132_V4"
APPROVED_POLICY_SHA256 = "3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd"
RUNTIME_SPEC_ID = "EOP101132_STEP2B_V4_RUNTIME_V1"
EXECUTION_MODE = "QUALIFICATION"
QUALIFICATION_MODE = "STEP2B_V4_BOUNDED_NDVI"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REQUEST_ID_RE = re.compile(r"^APR-EOP101132-V2-[0-9a-f]{32}$")
RUN_ID_RE = re.compile(r"^EOP101132-STEP2B-V4-[0-9]{8}T[0-9]{12}Z-[0-9a-f]{16}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")

REQUEST_FIELDS = {
    "approval_protocol_version",
    "approval_request_id",
    "reserved_run_id",
    "nonce",
    "policy_id",
    "policy_sha256",
    "runtime_spec_id",
    "runtime_spec_sha256",
    "executable_git_commit",
    "execution_mode",
    "qualification_mode",
    "source_scope",
    "input_scope",
    "maximum_executions",
    "created_at_utc",
    "expires_at_utc",
    "expected_approver_login",
    "expected_github_repository",
    "allowed_evidence_type",
    "canonicalisation_id",
    "canonical_approval_statement",
    "approval_request_sha256",
}


class ApprovalProtocolError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "APPROVAL_BINDING_INVALID") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ApprovalProtocolError(f"{field} must be an ISO-8601 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApprovalProtocolError(f"{field} must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ApprovalProtocolError(f"{field} must use UTC")
    return parsed


def _reject_constant(value: str) -> None:
    raise ApprovalProtocolError(f"non-standard JSON numeric constant: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ApprovalProtocolError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(raw: bytes | str) -> Any:
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ApprovalProtocolError("JSON must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ApprovalProtocolError(f"invalid JSON: {exc.msg}") from exc


def read_json(path: Path) -> Any:
    return strict_json_loads(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as exc:
        raise ApprovalProtocolError("value is not canonical JSON") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(6).hex()}.tmp")
    payload = canonical_bytes(value)
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def scope_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def request_binding_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        key: request[key]
        for key in sorted(REQUEST_FIELDS - {"canonical_approval_statement", "approval_request_sha256"})
    }


def calculate_request_sha256(request: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes(request_binding_payload(request)))


def build_canonical_statement(request: dict[str, Any], request_hash: str) -> str:
    evidence_types = ",".join(request["allowed_evidence_type"])
    return " ".join(
        (
            "APPROVE",
            "APPROVAL_PROTOCOL_V2",
            f"REQUEST={request['approval_request_id']}",
            f"RUN={request['reserved_run_id']}",
            f"NONCE={request['nonce']}",
            f"POLICY_ID={request['policy_id']}",
            f"POLICY_SHA256={request['policy_sha256']}",
            f"RUNTIME_SPEC_ID={request['runtime_spec_id']}",
            f"RUNTIME_SPEC_SHA256={request['runtime_spec_sha256']}",
            f"COMMIT={request['executable_git_commit']}",
            f"EXECUTION_MODE={request['execution_mode']}",
            f"QUALIFICATION_MODE={request['qualification_mode']}",
            f"SOURCE_SCOPE_SHA256={scope_sha256(request['source_scope'])}",
            f"INPUT_SCOPE_SHA256={scope_sha256(request['input_scope'])}",
            f"MAX_EXECUTIONS={request['maximum_executions']}",
            f"CREATED_AT={request['created_at_utc']}",
            f"EXPIRES_AT={request['expires_at_utc']}",
            f"APPROVER={request['expected_approver_login']}",
            f"REPOSITORY={request['expected_github_repository']}",
            f"EVIDENCE_TYPE={evidence_types}",
            f"REQUEST_SHA256={request_hash}",
        )
    )


def _require_pattern(value: Any, pattern: re.Pattern[str], field: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ApprovalProtocolError(f"invalid {field}")
    return value


def validate_request(request: dict[str, Any], *, now: str | None = None) -> None:
    if not isinstance(request, dict):
        raise ApprovalProtocolError("approval request must be a JSON object")
    if set(request) != REQUEST_FIELDS:
        missing = sorted(REQUEST_FIELDS - set(request))
        extra = sorted(set(request) - REQUEST_FIELDS)
        raise ApprovalProtocolError(f"approval request fields mismatch; missing={missing}; extra={extra}")
    expected = {
        "approval_protocol_version": APPROVAL_PROTOCOL_VERSION,
        "policy_id": POLICY_ID,
        "policy_sha256": APPROVED_POLICY_SHA256,
        "runtime_spec_id": RUNTIME_SPEC_ID,
        "execution_mode": EXECUTION_MODE,
        "qualification_mode": QUALIFICATION_MODE,
        "maximum_executions": 1,
        "expected_approver_login": EXPECTED_APPROVER_LOGIN,
        "expected_github_repository": EXPECTED_REPOSITORY,
        "allowed_evidence_type": list(ALLOWED_EVIDENCE_TYPES),
        "canonicalisation_id": CANONICALISATION_ID,
    }
    for field, value in expected.items():
        if request.get(field) != value:
            raise ApprovalProtocolError(f"approval request {field} mismatch")
    _require_pattern(request["approval_request_id"], REQUEST_ID_RE, "approval_request_id")
    _require_pattern(request["reserved_run_id"], RUN_ID_RE, "reserved_run_id")
    _require_pattern(request["nonce"], NONCE_RE, "nonce")
    _require_pattern(request["policy_sha256"], SHA256_RE, "policy_sha256")
    _require_pattern(request["runtime_spec_sha256"], SHA256_RE, "runtime_spec_sha256")
    _require_pattern(request["executable_git_commit"], COMMIT_RE, "executable_git_commit")
    _require_pattern(request["approval_request_sha256"], SHA256_RE, "approval_request_sha256")
    if not isinstance(request["source_scope"], dict) or not request["source_scope"]:
        raise ApprovalProtocolError("source_scope must be a non-empty object")
    if not isinstance(request["input_scope"], dict) or not request["input_scope"]:
        raise ApprovalProtocolError("input_scope must be a non-empty object")
    created = parse_utc(request["created_at_utc"], "created_at_utc")
    expires = parse_utc(request["expires_at_utc"], "expires_at_utc")
    if expires <= created:
        raise ApprovalProtocolError("expires_at_utc must be after created_at_utc")
    calculated = calculate_request_sha256(request)
    if request["approval_request_sha256"] != calculated:
        raise ApprovalProtocolError("approval request hash mismatch")
    expected_statement = build_canonical_statement(request, calculated)
    if request["canonical_approval_statement"] != expected_statement:
        raise ApprovalProtocolError("canonical approval statement mismatch")
    if now is not None and parse_utc(now, "current_time") > expires:
        raise ApprovalProtocolError("approval request expired", "APPROVAL_EXPIRED")


def validate_execution_bindings(
    request: dict[str, Any],
    *,
    policy_sha256: str,
    runtime_spec_sha256: str,
    executable_git_commit: str,
    reserved_run_id: str | None = None,
) -> None:
    validate_request(request)
    expected = {
        "policy_sha256": policy_sha256,
        "runtime_spec_sha256": runtime_spec_sha256,
        "executable_git_commit": executable_git_commit,
    }
    if reserved_run_id is not None:
        expected["reserved_run_id"] = reserved_run_id
    for field, value in expected.items():
        if request[field] != value:
            reason = "APPROVAL_RUN_ID_MISMATCH" if field == "reserved_run_id" else "APPROVAL_BINDING_INVALID"
            raise ApprovalProtocolError(f"approval request {field} mismatch", reason)


def build_request(
    *,
    policy_sha256: str,
    runtime_spec_sha256: str,
    executable_git_commit: str,
    created_at_utc: str | None = None,
    lifetime_hours: int = 24,
) -> dict[str, Any]:
    _require_pattern(policy_sha256, SHA256_RE, "policy_sha256")
    _require_pattern(runtime_spec_sha256, SHA256_RE, "runtime_spec_sha256")
    _require_pattern(executable_git_commit, COMMIT_RE, "executable_git_commit")
    created_text = created_at_utc or utc_now()
    created = parse_utc(created_text, "created_at_utc")
    if not 1 <= lifetime_hours <= 168:
        raise ApprovalProtocolError("lifetime_hours must be between 1 and 168")
    stamp = created.strftime("%Y%m%dT%H%M%S%fZ")
    request = {
        "approval_protocol_version": APPROVAL_PROTOCOL_VERSION,
        "approval_request_id": f"APR-EOP101132-V2-{os.urandom(16).hex()}",
        "reserved_run_id": f"EOP101132-STEP2B-V4-{stamp}-{os.urandom(8).hex()}",
        "nonce": os.urandom(32).hex(),
        "policy_id": POLICY_ID,
        "policy_sha256": policy_sha256,
        "runtime_spec_id": RUNTIME_SPEC_ID,
        "runtime_spec_sha256": runtime_spec_sha256,
        "executable_git_commit": executable_git_commit,
        "execution_mode": EXECUTION_MODE,
        "qualification_mode": QUALIFICATION_MODE,
        "source_scope": {
            "project_id": "EOP101132",
            "sources": ["CER_PROJECT_RECORD", "CER_PUBLISHED_CEA", "MSPC_SENTINEL2_L2A"],
            "stac_collection": "sentinel-2-l2a",
        },
        "input_scope": {
            "case_id": "EOP101132-NDVI-001",
            "pre_window": ["2017-06-01", "2017-08-31"],
            "post_window": ["2025-06-01", "2025-08-31"],
            "cea_sha256": "3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2",
        },
        "maximum_executions": 1,
        "created_at_utc": created_text,
        "expires_at_utc": (created + timedelta(hours=lifetime_hours)).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "expected_approver_login": EXPECTED_APPROVER_LOGIN,
        "expected_github_repository": EXPECTED_REPOSITORY,
        "allowed_evidence_type": list(ALLOWED_EVIDENCE_TYPES),
        "canonicalisation_id": CANONICALISATION_ID,
        "canonical_approval_statement": "",
        "approval_request_sha256": "",
    }
    request_hash = calculate_request_sha256(request)
    request["approval_request_sha256"] = request_hash
    request["canonical_approval_statement"] = build_canonical_statement(request, request_hash)
    validate_request(request)
    return request


def initialise_request_directory(output_root: Path, request: dict[str, Any]) -> Path:
    validate_request(request)
    request_dir = output_root / request["approval_request_id"]
    request_dir.mkdir(parents=True, exist_ok=False)
    atomic_write_json(request_dir / "approval-request.json", request)
    atomic_write_json(
        request_dir / "approval-state.json",
        {
            "approval_protocol_version": APPROVAL_PROTOCOL_VERSION,
            "approval_request_id": request["approval_request_id"],
            "approval_request_sha256": request["approval_request_sha256"],
            "reserved_run_id": request["reserved_run_id"],
            "lifecycle_state": "PENDING",
            "authorization_network_access_attempted": False,
            "first_authorization_access_attempt_at": None,
            "authorization_access_attempt_count": 0,
            "approval_evidence_sha256": None,
            "updated_at_utc": utc_now(),
        },
    )
    return request_dir


def validate_verified_bundle(request_dir: Path, *, now: str | None = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = read_json(request_dir / "approval-request.json")
    validate_request(request, now=now)
    state = read_json(request_dir / "approval-state.json")
    evidence_path = request_dir / "approval-verification.json"
    if state.get("lifecycle_state") != "VERIFIED" or not evidence_path.is_file():
        if state.get("lifecycle_state") == "CONSUMED":
            raise ApprovalProtocolError("approval request already consumed", "APPROVAL_ALREADY_CONSUMED")
        raise ApprovalProtocolError("independent approval evidence is not verified", "APPROVAL_EVIDENCE_NOT_INDEPENDENT")
    evidence = read_json(evidence_path)
    attempts_path = request_dir / "authorization-network-attempts.json"
    if (
        state.get("authorization_network_access_attempted") is not True
        or not state.get("first_authorization_access_attempt_at")
        or state.get("authorization_access_attempt_count", 0) < 1
        or not attempts_path.is_file()
    ):
        raise ApprovalProtocolError(
            "verified evidence lacks a persisted read-only authorization-network attempt",
            "APPROVAL_EVIDENCE_NOT_INDEPENDENT",
        )
    attempts_document = read_json(attempts_path)
    attempts = attempts_document.get("attempts") if isinstance(attempts_document, dict) else None
    if not isinstance(attempts, list) or len(attempts) != state["authorization_access_attempt_count"]:
        raise ApprovalProtocolError("authorization-network attempt history mismatch")
    if any(item.get("method") != "GET" or item.get("network_class") != "AUTHORIZATION_GITHUB_READ_ONLY" for item in attempts):
        raise ApprovalProtocolError("authorization evidence was not retrieved through the read-only adapter")
    evidence_hash = sha256_file(evidence_path)
    if state.get("approval_evidence_sha256") != evidence_hash:
        raise ApprovalProtocolError("approval evidence hash mismatch")
    if evidence.get("approval_request_sha256") != request["approval_request_sha256"]:
        raise ApprovalProtocolError("approval evidence binds another request")
    if evidence.get("reserved_run_id") != request["reserved_run_id"]:
        raise ApprovalProtocolError("approval evidence binds another Run ID", "APPROVAL_RUN_ID_MISMATCH")
    return request, state, evidence


def consume_verified_approval(
    request_dir: Path,
    *,
    executable_git_commit: str,
    execution_initialized_at_utc: str | None = None,
) -> dict[str, Any]:
    initialized_at = execution_initialized_at_utc or utc_now()
    lock_path = request_dir / ".consume.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ApprovalProtocolError("approval request already consumed or consumption is in progress", "APPROVAL_ALREADY_CONSUMED") from exc
    with os.fdopen(descriptor, "w", encoding="ascii") as lock:
        lock.write(f"fail-closed one-time consumption lock created {initialized_at}\n")
        lock.flush()
        os.fsync(lock.fileno())
    try:
        request, state, evidence = validate_verified_bundle(request_dir, now=initialized_at)
        if request["executable_git_commit"] != executable_git_commit:
            raise ApprovalProtocolError("approval executable Git commit mismatch")
        evidence_created = parse_utc(evidence.get("github_created_at_utc"), "github_created_at_utc")
        initialized = parse_utc(initialized_at, "execution_initialized_at_utc")
        if evidence_created >= initialized:
            raise ApprovalProtocolError("approval evidence was not created before execution initialization")
        consumption = {
            "approval_protocol_version": APPROVAL_PROTOCOL_VERSION,
            "approval_request_id": request["approval_request_id"],
            "approval_request_sha256": request["approval_request_sha256"],
            "approval_evidence_sha256": sha256_file(request_dir / "approval-verification.json"),
            "consumed_at_utc": initialized_at,
            "consumed_by_run_id": request["reserved_run_id"],
            "executable_commit": executable_git_commit,
            "maximum_executions": 1,
            "actual_consumption_count": 1,
        }
        atomic_write_json(request_dir / "approval-consumption.json", consumption)
        state.update(
            lifecycle_state="CONSUMED",
            consumed_at_utc=initialized_at,
            consumed_by_run_id=request["reserved_run_id"],
            approval_consumption_sha256=sha256_file(request_dir / "approval-consumption.json"),
            actual_consumption_count=1,
            updated_at_utc=utc_now(),
        )
        atomic_write_json(request_dir / "approval-state.json", state)
        return consumption
    except Exception:
        # The lock deliberately remains after any post-lock failure. Recovery is fail-closed.
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or validate Approval Protocol V2 requests without network access")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-request")
    create.add_argument("--output-root", type=Path, required=True)
    create.add_argument("--policy-sha256", required=True)
    create.add_argument("--runtime-spec-sha256", required=True)
    create.add_argument("--commit", required=True)
    create.add_argument("--lifetime-hours", type=int, default=24)
    validate = sub.add_parser("validate-request")
    validate.add_argument("request", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create-request":
            request = build_request(
                policy_sha256=args.policy_sha256,
                runtime_spec_sha256=args.runtime_spec_sha256,
                executable_git_commit=args.commit,
                lifetime_hours=args.lifetime_hours,
            )
            request_dir = initialise_request_directory(args.output_root, request)
            print(request_dir)
            print(request["approval_request_sha256"])
            print(request["canonical_approval_statement"])
        else:
            request = read_json(args.request)
            validate_request(request)
            print(f"VALID {request['approval_request_sha256']}")
        return 0
    except (ApprovalProtocolError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
