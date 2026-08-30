from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from scripts import approval_protocol_v2 as protocol


ISSUE_PATH_RE = re.compile(r"^/([^/]+/[^/]+)/issues/([1-9][0-9]*)$")
COMMENT_FRAGMENT_RE = re.compile(r"^issuecomment-([1-9][0-9]*)$")
API_ROOT = "https://api.github.com"


def _safe_state(request_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    request = protocol.read_json(request_dir / "approval-request.json")
    protocol.validate_request(request)
    state = protocol.read_json(request_dir / "approval-state.json")
    if state.get("lifecycle_state") == "CONSUMED":
        raise protocol.ApprovalProtocolError("approval request already consumed", "APPROVAL_ALREADY_CONSUMED")
    return request, state


def parse_evidence_url(url: str, expected_repository: str) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query:
        raise protocol.ApprovalProtocolError("GitHub evidence URL must be a canonical github.com HTTPS URL")
    match = ISSUE_PATH_RE.fullmatch(parsed.path)
    if not match or match.group(1) != expected_repository:
        raise protocol.ApprovalProtocolError("GitHub repository identity mismatch", "APPROVAL_IDENTITY_MISMATCH")
    issue_number = int(match.group(2))
    if parsed.fragment:
        fragment = COMMENT_FRAGMENT_RE.fullmatch(parsed.fragment)
        if not fragment:
            raise protocol.ApprovalProtocolError("GitHub comment URL is not canonical")
        comment_id = int(fragment.group(1))
        return {
            "evidence_type": "GITHUB_ISSUE_COMMENT",
            "canonical_url": f"https://github.com/{expected_repository}/issues/{issue_number}#issuecomment-{comment_id}",
            "api_url": f"{API_ROOT}/repos/{expected_repository}/issues/comments/{comment_id}",
            "issue_number": issue_number,
            "evidence_id": comment_id,
        }
    return {
        "evidence_type": "GITHUB_ISSUE",
        "canonical_url": f"https://github.com/{expected_repository}/issues/{issue_number}",
        "api_url": f"{API_ROOT}/repos/{expected_repository}/issues/{issue_number}",
        "issue_number": issue_number,
        "evidence_id": issue_number,
    }


def _record_authorization_attempt(request_dir: Path, state: dict[str, Any], parsed: dict[str, Any]) -> str:
    attempted_at = protocol.utc_now()
    attempts_path = request_dir / "authorization-network-attempts.json"
    attempts = protocol.read_json(attempts_path).get("attempts", []) if attempts_path.is_file() else []
    attempts.append(
        {
            "attempt": len(attempts) + 1,
            "attempted_at_utc": attempted_at,
            "network_class": "AUTHORIZATION_GITHUB_READ_ONLY",
            "method": "GET",
            "api_url": parsed["api_url"],
        }
    )
    protocol.atomic_write_json(attempts_path, {"attempts": attempts})
    state.update(
        authorization_network_access_attempted=True,
        authorization_access_attempt_count=len(attempts),
        updated_at_utc=attempted_at,
    )
    if state.get("first_authorization_access_attempt_at") is None:
        state["first_authorization_access_attempt_at"] = attempted_at
    protocol.atomic_write_json(request_dir / "approval-state.json", state)
    return attempted_at


def _identity(payload: dict[str, Any]) -> tuple[str, str]:
    user = payload.get("user")
    if not isinstance(user, dict):
        raise protocol.ApprovalProtocolError("GitHub evidence has no authoritative actor", "APPROVAL_IDENTITY_MISMATCH")
    login = user.get("login")
    actor_type = user.get("type")
    if not isinstance(login, str) or not isinstance(actor_type, str):
        raise protocol.ApprovalProtocolError("GitHub actor identity is incomplete", "APPROVAL_IDENTITY_MISMATCH")
    return login, actor_type


def validate_github_payload(
    request: dict[str, Any],
    parsed: dict[str, Any],
    payload: dict[str, Any],
    *,
    retrieved_at_utc: str,
) -> dict[str, Any]:
    protocol.validate_request(request, now=retrieved_at_utc)
    if parsed["evidence_type"] not in request["allowed_evidence_type"]:
        raise protocol.ApprovalProtocolError("GitHub evidence type is not allowed")
    expected_repo_api = f"{API_ROOT}/repos/{request['expected_github_repository']}"
    expected_issue_api = f"{expected_repo_api}/issues/{parsed['issue_number']}"
    if parsed["evidence_type"] == "GITHUB_ISSUE":
        if payload.get("number") != parsed["issue_number"] or payload.get("repository_url") != expected_repo_api:
            raise protocol.ApprovalProtocolError("GitHub issue repository or ID mismatch", "APPROVAL_IDENTITY_MISMATCH")
    else:
        if payload.get("id") != parsed["evidence_id"] or payload.get("issue_url") != expected_issue_api:
            raise protocol.ApprovalProtocolError("GitHub comment repository or ID mismatch", "APPROVAL_IDENTITY_MISMATCH")
    if payload.get("html_url") != parsed["canonical_url"]:
        raise protocol.ApprovalProtocolError("GitHub evidence canonical URL mismatch", "APPROVAL_IDENTITY_MISMATCH")
    login, actor_type = _identity(payload)
    if login != request["expected_approver_login"] or actor_type != "User":
        raise protocol.ApprovalProtocolError("GitHub approval actor mismatch", "APPROVAL_IDENTITY_MISMATCH")
    body = payload.get("body")
    if not isinstance(body, str) or body.encode("utf-8") != request["canonical_approval_statement"].encode("utf-8"):
        raise protocol.ApprovalProtocolError("GitHub approval body does not exactly match the canonical statement")
    created_text = payload.get("created_at")
    updated_text = payload.get("updated_at")
    created = protocol.parse_utc(created_text, "github.created_at")
    updated = protocol.parse_utc(updated_text, "github.updated_at")
    if updated != created:
        raise protocol.ApprovalProtocolError("edited GitHub approval body is not accepted")
    request_created = protocol.parse_utc(request["created_at_utc"], "created_at_utc")
    expires = protocol.parse_utc(request["expires_at_utc"], "expires_at_utc")
    if created < request_created or created > expires:
        raise protocol.ApprovalProtocolError("GitHub approval timestamp is outside the request lifetime", "APPROVAL_EXPIRED")
    safe_snapshot = {
        "repository": request["expected_github_repository"],
        "evidence_type": parsed["evidence_type"],
        "evidence_id": parsed["evidence_id"],
        "issue_number": parsed["issue_number"],
        "canonical_url": parsed["canonical_url"],
        "author_login": login,
        "author_type": actor_type,
        "author_association": payload.get("author_association"),
        "created_at_utc": created_text,
        "updated_at_utc": updated_text,
        "body_sha256": protocol.sha256_bytes(body.encode("utf-8")),
    }
    return {
        "approval_protocol_version": protocol.APPROVAL_PROTOCOL_VERSION,
        "approval_request_id": request["approval_request_id"],
        "approval_request_sha256": request["approval_request_sha256"],
        "reserved_run_id": request["reserved_run_id"],
        "evidence_type": parsed["evidence_type"],
        "github_repository": request["expected_github_repository"],
        "github_url": parsed["canonical_url"],
        "github_evidence_id": parsed["evidence_id"],
        "github_issue_number": parsed["issue_number"],
        "github_author_login": login,
        "github_author_type": actor_type,
        "github_created_at_utc": created_text,
        "github_retrieved_at_utc": retrieved_at_utc,
        "approval_body_sha256": safe_snapshot["body_sha256"],
        "safe_response_snapshot": safe_snapshot,
        "safe_response_snapshot_sha256": protocol.sha256_bytes(protocol.canonical_bytes(safe_snapshot)),
        "independent_identity_source": "GITHUB_API_ACTOR",
        "read_only_method": "GET",
    }


def verify_payload_offline(
    request_dir: Path,
    evidence_url: str,
    payload_raw: bytes,
    *,
    retrieved_at_utc: str,
) -> dict[str, Any]:
    request, state = _safe_state(request_dir)
    parsed = parse_evidence_url(evidence_url, request["expected_github_repository"])
    payload = protocol.strict_json_loads(payload_raw)
    if not isinstance(payload, dict):
        raise protocol.ApprovalProtocolError("GitHub response must be a JSON object")
    try:
        verification = validate_github_payload(request, parsed, payload, retrieved_at_utc=retrieved_at_utc)
    except protocol.ApprovalProtocolError as exc:
        state.update(lifecycle_state="REJECTED", rejection_reason_code=exc.reason_code, updated_at_utc=protocol.utc_now())
        protocol.atomic_write_json(request_dir / "approval-state.json", state)
        raise
    protocol.atomic_write_json(request_dir / "approval-verification.json", verification)
    state.update(
        lifecycle_state="VERIFIED",
        approval_evidence_sha256=protocol.sha256_file(request_dir / "approval-verification.json"),
        verified_at_utc=retrieved_at_utc,
        updated_at_utc=protocol.utc_now(),
    )
    protocol.atomic_write_json(request_dir / "approval-state.json", state)
    return verification


def retrieve_and_verify(
    request_dir: Path,
    evidence_url: str,
    *,
    token: str | None = None,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    request, state = _safe_state(request_dir)
    parsed = parse_evidence_url(evidence_url, request["expected_github_repository"])
    _record_authorization_attempt(request_dir, state, parsed)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "qualify-environmental-evidence-approval-v2",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    github_request = urllib.request.Request(parsed["api_url"], headers=headers, method="GET")
    try:
        with opener(github_request, timeout=30) as response:
            raw = response.read()
    except (OSError, urllib.error.URLError) as exc:
        raise protocol.ApprovalProtocolError("GitHub approval evidence unavailable", "APPROVAL_EVIDENCE_UNAVAILABLE") from exc
    return verify_payload_offline(request_dir, evidence_url, raw, retrieved_at_utc=protocol.utc_now())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read and verify a pre-existing GitHub approval using GET only")
    parser.add_argument("request_dir", type=Path)
    parser.add_argument("github_url")
    args = parser.parse_args(argv)
    try:
        verification = retrieve_and_verify(args.request_dir, args.github_url, token=os.environ.get("GITHUB_TOKEN"))
        print(protocol.sha256_bytes(protocol.canonical_bytes(verification)))
        return 0
    except (protocol.ApprovalProtocolError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
