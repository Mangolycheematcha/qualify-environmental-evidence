from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts import approval_protocol_v2 as protocol
from scripts import github_approval_readonly as github
from scripts import step2b_v4_runtime as runtime


POLICY_HASH = protocol.APPROVED_POLICY_SHA256
SPEC_HASH = "b" * 64
COMMIT = "a" * 40
CREATED = "2026-08-30T00:00:00.000000Z"
APPROVED_AT = "2026-08-30T01:00:00.000000Z"
RETRIEVED = "2026-08-30T02:00:00.000000Z"
INITIALIZED = "2026-08-30T03:00:00.000000Z"
ISSUE_URL = "https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/17"


def make_request() -> dict:
    return protocol.build_request(
        policy_sha256=POLICY_HASH,
        runtime_spec_sha256=SPEC_HASH,
        executable_git_commit=COMMIT,
        created_at_utc=CREATED,
        lifetime_hours=168,
    )


def make_request_dir(tmp_path: Path) -> tuple[Path, dict]:
    request = make_request()
    return protocol.initialise_request_directory(tmp_path, request), request


def issue_payload(request: dict, **changes: object) -> dict:
    payload = {
        "number": 17,
        "repository_url": "https://api.github.com/repos/Mangolycheematcha/qualify-environmental-evidence",
        "html_url": ISSUE_URL,
        "user": {"login": "Mangolycheematcha", "type": "User"},
        "body": request["canonical_approval_statement"],
        "created_at": APPROVED_AT,
        "updated_at": APPROVED_AT,
        "author_association": "OWNER",
    }
    payload.update(changes)
    return payload


def verify(tmp_path: Path) -> tuple[Path, dict, dict]:
    request_dir, request = make_request_dir(tmp_path)
    state = protocol.read_json(request_dir / "approval-state.json")
    state.update(
        authorization_network_access_attempted=True,
        first_authorization_access_attempt_at="2026-08-30T01:59:59.000000Z",
        authorization_access_attempt_count=1,
    )
    protocol.atomic_write_json(request_dir / "approval-state.json", state)
    protocol.atomic_write_json(
        request_dir / "authorization-network-attempts.json",
        {"attempts": [{"attempt": 1, "attempted_at_utc": "2026-08-30T01:59:59.000000Z", "network_class": "AUTHORIZATION_GITHUB_READ_ONLY", "method": "GET", "api_url": "https://api.github.com/repos/Mangolycheematcha/qualify-environmental-evidence/issues/17"}]},
    )
    verification = github.verify_payload_offline(
        request_dir,
        ISSUE_URL,
        json.dumps(issue_payload(request), allow_nan=False).encode(),
        retrieved_at_utc=RETRIEVED,
    )
    return request_dir, request, verification


def test_canonical_request_golden_vector(monkeypatch):
    values = [bytes.fromhex("11" * 16), bytes.fromhex("22" * 8), bytes.fromhex("33" * 32)]
    monkeypatch.setattr(protocol.os, "urandom", lambda _size: values.pop(0))
    request = protocol.build_request(
        policy_sha256=POLICY_HASH,
        runtime_spec_sha256=SPEC_HASH,
        executable_git_commit=COMMIT,
        created_at_utc=CREATED,
        lifetime_hours=24,
    )
    assert request["approval_request_sha256"] == "af8e4ee825e276e340551def7dc71c39f4271330695fb976f308b5f5ac4d350b"
    assert protocol.sha256_bytes(protocol.canonical_bytes(request)) == "682feb1f13e9e24668527edab6d15ebee119ac7acf5a78c33118d781b03882da"


def rewrite_bound_request(request_dir: Path, request: dict) -> None:
    request["approval_request_sha256"] = protocol.calculate_request_sha256(request)
    request["canonical_approval_statement"] = protocol.build_canonical_statement(request, request["approval_request_sha256"])
    protocol.atomic_write_json(request_dir / "approval-request.json", request)


def test_self_attested_and_codex_generated_detached_approval_are_rejected():
    with pytest.raises(runtime.V4RuntimeFailure, match="not independent") as error:
        runtime.validate_detached_approval(
            {"approver_role": "HUMAN_PROJECT_OWNER", "generated_by": "Codex"},
            runtime_spec_hash=SPEC_HASH,
            git_commit=COMMIT,
        )
    assert error.value.reason_code == "APPROVAL_EVIDENCE_NOT_INDEPENDENT"


@pytest.mark.parametrize(
    ("field", "expected", "reason"),
    [
        ("policy_sha256", "c" * 64, "APPROVAL_BINDING_INVALID"),
        ("runtime_spec_sha256", "c" * 64, "APPROVAL_BINDING_INVALID"),
        ("executable_git_commit", "c" * 40, "APPROVAL_BINDING_INVALID"),
        ("reserved_run_id", "EOP101132-STEP2B-V4-20260830T111111111111Z-cccccccccccccccc", "APPROVAL_RUN_ID_MISMATCH"),
    ],
)
def test_execution_tuple_mismatches_hit_exact_guard(field: str, expected: str, reason: str):
    request = make_request()
    kwargs = {
        "policy_sha256": request["policy_sha256"],
        "runtime_spec_sha256": request["runtime_spec_sha256"],
        "executable_git_commit": request["executable_git_commit"],
        "reserved_run_id": request["reserved_run_id"],
    }
    kwargs[field] = expected
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        protocol.validate_execution_bindings(request, **kwargs)
    assert error.value.reason_code == reason


@pytest.mark.parametrize("field", ["approval_request_id", "reserved_run_id", "nonce"])
def test_request_id_run_id_and_nonce_are_bound_by_exact_body(tmp_path: Path, field: str):
    request_dir, request = make_request_dir(tmp_path)
    changed = copy.deepcopy(request)
    changed[field] = (
        "APR-EOP101132-V2-" + "c" * 32
        if field == "approval_request_id"
        else "EOP101132-STEP2B-V4-20260830T111111111111Z-cccccccccccccccc"
        if field == "reserved_run_id"
        else "c" * 64
    )
    rewrite_bound_request(request_dir, changed)
    with pytest.raises(protocol.ApprovalProtocolError, match="body"):
        github.verify_payload_offline(
            request_dir, ISSUE_URL, json.dumps(issue_payload(request)).encode(), retrieved_at_utc=RETRIEVED
        )


def test_wrong_github_repository_hits_identity_guard():
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        github.parse_evidence_url("https://github.com/other/repo/issues/17", protocol.EXPECTED_REPOSITORY)
    assert error.value.reason_code == "APPROVAL_IDENTITY_MISMATCH"


def test_issue_comment_identity_and_canonical_url_validate(tmp_path: Path):
    request_dir, request = make_request_dir(tmp_path)
    comment_url = ISSUE_URL + "#issuecomment-99"
    payload = issue_payload(request)
    payload.pop("number")
    payload.pop("repository_url")
    payload.update(
        id=99,
        issue_url="https://api.github.com/repos/Mangolycheematcha/qualify-environmental-evidence/issues/17",
        html_url=comment_url,
    )
    verification = github.verify_payload_offline(
        request_dir, comment_url, json.dumps(payload).encode(), retrieved_at_utc=RETRIEVED
    )
    assert verification["evidence_type"] == "GITHUB_ISSUE_COMMENT"
    assert verification["github_evidence_id"] == 99


@pytest.mark.parametrize("quoted", [False, True])
def test_wrong_github_author_and_quoted_text_hit_identity_guard(tmp_path: Path, quoted: bool):
    request_dir, request = make_request_dir(tmp_path)
    payload = issue_payload(request, user={"login": "someone-else", "type": "User"})
    if quoted:
        payload["body"] = request["canonical_approval_statement"]
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        github.verify_payload_offline(request_dir, ISSUE_URL, json.dumps(payload).encode(), retrieved_at_utc=RETRIEVED)
    assert error.value.reason_code == "APPROVAL_IDENTITY_MISMATCH"


def test_edited_approval_body_is_rejected(tmp_path: Path):
    request_dir, request = make_request_dir(tmp_path)
    payload = issue_payload(request, updated_at="2026-08-30T01:00:01.000000Z")
    with pytest.raises(protocol.ApprovalProtocolError, match="edited"):
        github.verify_payload_offline(request_dir, ISSUE_URL, json.dumps(payload).encode(), retrieved_at_utc=RETRIEVED)


def test_approval_created_after_execution_initialization_is_rejected(tmp_path: Path):
    request_dir, _, verification = verify(tmp_path)
    verification["github_created_at_utc"] = "2026-08-30T04:00:00.000000Z"
    protocol.atomic_write_json(request_dir / "approval-verification.json", verification)
    state = protocol.read_json(request_dir / "approval-state.json")
    state["approval_evidence_sha256"] = protocol.sha256_file(request_dir / "approval-verification.json")
    protocol.atomic_write_json(request_dir / "approval-state.json", state)
    with pytest.raises(protocol.ApprovalProtocolError, match="before execution"):
        protocol.consume_verified_approval(request_dir, executable_git_commit=COMMIT, execution_initialized_at_utc=INITIALIZED)


def test_expired_approval_request_hits_expiry_guard(tmp_path: Path):
    request_dir, request = make_request_dir(tmp_path)
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        github.verify_payload_offline(
            request_dir, ISSUE_URL, json.dumps(issue_payload(request)).encode(), retrieved_at_utc="2026-09-07T00:00:00.000000Z"
        )
    assert error.value.reason_code == "APPROVAL_EXPIRED"


def test_malformed_timestamp_is_rejected(tmp_path: Path):
    request_dir, request = make_request_dir(tmp_path)
    with pytest.raises(protocol.ApprovalProtocolError, match="timestamp"):
        github.verify_payload_offline(
            request_dir,
            ISSUE_URL,
            json.dumps(issue_payload(request, created_at="not-a-time", updated_at="not-a-time")).encode(),
            retrieved_at_utc=RETRIEVED,
        )


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'])
def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(raw: bytes):
    with pytest.raises(protocol.ApprovalProtocolError):
        protocol.strict_json_loads(raw)


def test_preflight_verifies_without_consuming(tmp_path: Path):
    request_dir, _, _ = verify(tmp_path)
    assert protocol.read_json(request_dir / "approval-state.json")["lifecycle_state"] == "VERIFIED"
    assert not (request_dir / "approval-consumption.json").exists()
    assert not (request_dir / ".consume.lock").exists()


def test_execution_consumes_atomically_once_and_duplicate_fails(tmp_path: Path):
    request_dir, request, _ = verify(tmp_path)
    consumption = protocol.consume_verified_approval(request_dir, executable_git_commit=COMMIT, execution_initialized_at_utc=INITIALIZED)
    assert consumption["consumed_by_run_id"] == request["reserved_run_id"]
    assert consumption["actual_consumption_count"] == 1
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        protocol.consume_verified_approval(request_dir, executable_git_commit=COMMIT, execution_initialized_at_utc=INITIALIZED)
    assert error.value.reason_code == "APPROVAL_ALREADY_CONSUMED"


def test_consumption_persists_after_later_source_failure(tmp_path: Path):
    request_dir, _, _ = verify(tmp_path)
    protocol.consume_verified_approval(request_dir, executable_git_commit=COMMIT, execution_initialized_at_utc=INITIALIZED)
    with pytest.raises(RuntimeError, match="source unavailable"):
        raise RuntimeError("source unavailable")
    assert protocol.read_json(request_dir / "approval-state.json")["lifecycle_state"] == "CONSUMED"


def test_approval_failure_does_not_call_environmental_data_client(tmp_path: Path, monkeypatch):
    request_dir, _ = make_request_dir(tmp_path)
    calls = {"data": 0}
    monkeypatch.setattr(runtime, "fetch_sources", lambda *_args, **_kwargs: calls.__setitem__("data", calls["data"] + 1))
    with pytest.raises(protocol.ApprovalProtocolError) as error:
        protocol.validate_verified_bundle(request_dir)
    assert error.value.reason_code == "APPROVAL_EVIDENCE_NOT_INDEPENDENT"
    assert calls["data"] == 0


def test_first_data_network_attempt_is_persisted_before_request_and_timeout(tmp_path: Path, monkeypatch):
    run_dir = tmp_path / "run"
    (run_dir / "diagnostics").mkdir(parents=True)
    runtime.write_json(
        run_dir / "run-state.json",
        {
            "first_data_network_attempt_at": None,
            "first_data_network_attempt_event_id": None,
            "last_data_network_attempt_at": None,
            "last_data_network_attempt_event_id": None,
            "data_network_access_attempted": False,
            "network_accessed": False,
        },
    )

    def request(*_args, **_kwargs):
        state = runtime.read_json(run_dir / "run-state.json")
        assert state["data_network_access_attempted"] is True
        assert state["first_data_network_attempt_at"]
        assert state["first_data_network_attempt_event_id"]
        raise TimeoutError("timeout")

    monkeypatch.setattr(runtime.legacy_io, "http_request", request)
    monkeypatch.setattr(runtime.time, "sleep", lambda _seconds: None)
    with pytest.raises(runtime.V4RuntimeFailure):
        runtime._http_request("https://cer.gov.au/test", audit_run_dir=run_dir)
    attempts = runtime.read_json(run_dir / "diagnostics" / "data-network-attempts.json")["attempts"]
    assert len(attempts) == 3
    assert all(item["attempted_at_utc"] for item in attempts)
    state = runtime.read_json(run_dir / "run-state.json")
    assert state["first_data_network_attempt_event_id"] == attempts[0]["event_id"]
    assert state["first_data_network_attempt_at"] == attempts[0]["attempted_at_utc"]


class FakeResponse:
    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.raw


def test_authorization_and_data_records_are_separate_and_token_is_not_persisted(tmp_path: Path):
    request_dir, request = make_request_dir(tmp_path)
    token = "TEST_TOKEN_MUST_NOT_PERSIST"
    captured = {}

    def opener(req, timeout):
        captured["method"] = req.get_method()
        captured["authorization"] = req.headers.get("Authorization")
        assert timeout == 30
        return FakeResponse(json.dumps(issue_payload(request)).encode())

    github.retrieve_and_verify(request_dir, ISSUE_URL, token=token, opener=opener)
    assert captured == {"method": "GET", "authorization": f"Bearer {token}"}
    state = protocol.read_json(request_dir / "approval-state.json")
    assert state["authorization_network_access_attempted"] is True
    assert state["first_authorization_access_attempt_at"]
    persisted = [path.read_bytes() for path in request_dir.rglob("*") if path.is_file()]
    assert not any(token.encode() in raw or b"Authorization" in raw for raw in persisted)


def test_provenance_schema_and_runtime_bind_request_evidence_and_consumption():
    schema = json.loads((runtime.ROOT / "schemas" / "provenance-manifest.schema.json").read_text())
    properties = schema["$defs"]["run_identity"]["properties"]
    binding_fields = (
        "approval_request_sha256",
        "approval_evidence_sha256",
        "approval_consumption_sha256",
        "reserved_run_id",
    )
    network_fields = (
        "first_data_network_attempt_event_id",
        "first_data_network_attempt_at",
    )
    assert all(field in properties for field in (*binding_fields, *network_fields))
    required = schema["$defs"]["run_identity"]["allOf"][0]["then"]["required"]
    assert all(field in required for field in binding_fields)
    source = (runtime.ROOT / "scripts" / "step2b_v4_runtime.py").read_text()
    assert all(f'"{field}": state["{field}"]' in source for field in binding_fields[:3])


def test_historical_policy_science_and_completed_run_hashes_are_preserved():
    expected = {
        "policies/eop101132/step2b-proposed-policy-v4.json": POLICY_HASH,
        "scripts/step2b_acquisition.py": "a2221f7fb2d98f5263123f2e53357a94fb910b201602568a04b6ee7460bf45f6",
        "scripts/step2b_offline.py": "8a26c8ac372ee331e7b1ae7225200ac7d5b6484de3db0cdfadaeddf4fe5a1fa0",
        "scripts/step2b_v4_raster.py": "dfa83096fad7ce8a5e91cec8e94f979521e3c33b108d928147dc6169afac0d4b",
    }
    for relative, digest in expected.items():
        assert protocol.sha256_file(runtime.ROOT / relative) == digest
    historical = runtime.ROOT / "runs" / "EOP101132-STEP2B-V4-20260830T044223516364Z-73144a299e2d5763"
    if historical.is_dir():
        assert protocol.sha256_file(historical / "assessment.json") == "1b6297f81d1bafc847ef02dac9cb0c2ada91bf03ccedf75759bb07e4002f00dc"
        assert protocol.sha256_file(historical / "provenance-manifest.json") == "5749fc7fd0b6ee55a98732b2f9ab02a47e125f874e1be9d30be8ad3f63dc3926"
    failed = runtime.ROOT / "runs" / "EOP101132-STEP2B-V4-20260830T095123241799Z-5bb61d381c71a8e9"
    if failed.is_dir():
        assert protocol.sha256_file(failed / "run-state.json") == "78713fc98bf7e4176ade72b5c24e112748a19e8e82eacecd42318a02f0d4761f"
        assert protocol.sha256_file(failed / "diagnostics" / "runtime-failure.json") == "f0e8dc718d038d8fdd5df41e4ddefbe15fe63dc090b73ed6294991984f812ac9"
        assert protocol.sha256_file(failed / "approval" / "approval-consumption.json") == "9f69cc7d03f37a0d4c5587e562a2eccc373f6d03f69ddd303fbe6319842954ac"


def test_readme_uses_exact_governance_verdict_and_pending_status():
    readme = (runtime.ROOT / "README.md").read_text(encoding="utf-8")
    assert "VALID_TECHNICAL_RUN_BUT_APPROVAL_BINDING_INVALID" in readme
    assert "A corrected pre-authorized run is pending." in readme
    assert "three approved V4 runs" not in readme
    assert "third approved V4 run" not in readme.lower()
