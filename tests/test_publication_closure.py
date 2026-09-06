import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "47bbeaf5375c365eee758bbf8f6eda9f0c217dbe"
BODY_SHA256 = "f1ed5718e6bffa713f6c252e254c60f32e496d9c5ac510a09bccb36dd7eb694e"
SAFE_SNAPSHOT_SHA256 = "9e6eabf2d54554bf15f634531c36b9e089db29daeece38d21d1898d29894613f"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_release_authorization_record_is_bounded_and_hash_linked():
    record = read("docs/PUBLIC_RELEASE_AUTHORIZATION.md")
    assert "https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/3" in record
    assert "`User` / `OWNER`" in record
    assert BASELINE in record
    assert BODY_SHA256 in record
    assert SAFE_SNAPSHOT_SHA256 in record
    assert "does not extend to third-party material" in record
    assert "fully canonical claim" in record


def test_safe_issue_snapshot_hash_definition_recomputes():
    snapshot = {
        "author_association": "OWNER",
        "body_sha256": BODY_SHA256,
        "created_at": "2026-09-06T10:51:21Z",
        "html_url": "https://github.com/Mangolycheematcha/qualify-environmental-evidence/issues/3",
        "number": 3,
        "repository_url": "https://api.github.com/repos/Mangolycheematcha/qualify-environmental-evidence",
        "state": "open",
        "title": "Public release authorization \uff1brights and email disclosure",
        "updated_at": "2026-09-06T10:51:21Z",
        "user": {"login": "Mangolycheematcha", "type": "User"},
    }
    payload = json.dumps(snapshot, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(payload).hexdigest() == SAFE_SNAPSHOT_SHA256


def test_publication_claims_keep_required_boundaries():
    readme = read("README.md")
    adr = read("docs/adr/0001-workflow-framework.md")
    status = json.loads(read("evaluation/results/model-comparison-status.json"))
    assert "### Data boundary" in readme
    assert "does not train a machine-learning model" in readme
    assert "Future research or partner deployments may operate in private" in readme
    assert "informational references only" in adr
    assert not re.search(r"langgraph==|last updated|release page.*displayed", adr, re.IGNORECASE)
    assert all(arm == {"planned_cases": 27, "completed_cases": 0, "status": "NOT_EXECUTED"} for arm in status["arms"].values())
    assert status["human_evaluation"]["status"] == "NOT_EXECUTED"
    assert status["human_evaluation"]["completed_cases"] == 0


def test_handoff_uses_stable_commit_anchors():
    handoff = read("HANDOFF.md")
    assert f"`implementation_baseline_commit`: `{BASELINE}`" in handoff
    assert f"`handoff_parent_commit`: `{BASELINE}`" in handoff
    assert "resolve with `git log -1 --format=%H -- HANDOFF.md`" in handoff
    assert "prediction of the commit" in handoff
