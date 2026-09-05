from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    import qualification_workflow as workflow
except ModuleNotFoundError:
    from scripts import qualification_workflow as workflow


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
PREFERENCE_KEYS = {"citation_style", "locale", "output_detail"}
SENSITIVE_KEY = re.compile(r"secret|token|password|credential|api.?key", re.IGNORECASE)


def _safe_id(value: str, label: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise workflow.QualificationError(f"unsafe {label}: {value!r}")
    return value


def _write_new_or_equal(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise workflow.QualificationError(f"immutable store collision: {path.name}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


class EvidenceSnapshotStore:
    def __init__(self, root: Path):
        self.root = Path(root) / "evidence"

    def put(self, document: dict[str, Any]) -> str:
        payload = workflow.canonical_bytes(document)
        digest = workflow.sha256_bytes(payload)
        _write_new_or_equal(self.root / f"{digest}.json", payload)
        return digest

    def get(self, digest: str) -> dict[str, Any]:
        _safe_id(digest, "evidence digest")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise workflow.QualificationError("invalid evidence digest")
        value = workflow.load_json(self.root / f"{digest}.json")
        if workflow.sha256_bytes(workflow.canonical_bytes(value)) != digest:
            raise workflow.QualificationError("evidence snapshot hash mismatch")
        return value


class CheckpointStore:
    def __init__(self, root: Path):
        self.root = Path(root) / "checkpoints"

    def put(self, workflow_id: str, sequence: int, state: dict[str, Any]) -> str:
        workflow_id = _safe_id(workflow_id, "workflow id")
        if sequence < 1 or sequence > 999999:
            raise workflow.QualificationError("checkpoint sequence out of range")
        payload = workflow.canonical_bytes(state)
        path = self.root / workflow_id / f"{sequence:06d}.json"
        _write_new_or_equal(path, payload)
        return workflow.sha256_bytes(payload)

    def latest(self, workflow_id: str) -> tuple[int, dict[str, Any]] | None:
        workflow_id = _safe_id(workflow_id, "workflow id")
        directory = self.root / workflow_id
        paths = sorted(directory.glob("[0-9][0-9][0-9][0-9][0-9][0-9].json")) if directory.is_dir() else []
        if not paths:
            return None
        path = paths[-1]
        return int(path.stem), workflow.load_json(path)


class PreferenceStore:
    def __init__(self, root: Path):
        self.root = Path(root) / "preferences"

    def put(self, session_id: str, preferences: dict[str, str]) -> str:
        session_id = _safe_id(session_id, "session id")
        unknown = set(preferences) - PREFERENCE_KEYS
        if unknown or any(SENSITIVE_KEY.search(key) for key in preferences):
            raise workflow.QualificationError("preference contains prohibited or unknown keys")
        if any(not isinstance(value, str) or len(value) > 120 for value in preferences.values()):
            raise workflow.QualificationError("preference values must be short strings")
        payload = workflow.canonical_bytes({"session_id": session_id, "preferences": preferences})
        path = self.root / f"{session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, path)
        return workflow.sha256_bytes(payload)

    def get(self, session_id: str) -> dict[str, str]:
        session_id = _safe_id(session_id, "session id")
        path = self.root / f"{session_id}.json"
        if not path.is_file():
            return {}
        return workflow.load_json(path)["preferences"]


def fact_text(fact: dict[str, Any]) -> str:
    return " ".join((fact["fact_id"], fact["text"], " ".join(fact["tags"]))).lower()


class LocalRetrievalIndex:
    def __init__(self, facts: Iterable[dict[str, Any]]):
        self.facts = sorted((dict(fact) for fact in facts), key=lambda item: item["fact_id"])
        self.tokens = {fact["fact_id"]: workflow.tokenize(fact_text(fact)) for fact in self.facts}
        document_count = len(self.facts)
        frequencies = Counter(token for tokens in self.tokens.values() for token in set(tokens))
        self.idf = {token: math.log((1 + document_count) / (1 + count)) + 1 for token, count in frequencies.items()}
        self.vectors = {fact_id: self._vector(tokens) for fact_id, tokens in self.tokens.items()}

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {token: count * self.idf.get(token, 1.0) for token, count in counts.items()}

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(value * right.get(token, 0.0) for token, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    def rank(
        self,
        question: str,
        mode: str,
        limit: int = 5,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> list[tuple[str, float]]:
        query_tokens = workflow.tokenize(question)
        query_set = set(query_tokens)
        lexical = {
            fact_id: len(query_set & set(tokens)) / max(1, len(query_set | set(tokens)))
            for fact_id, tokens in self.tokens.items()
        }
        query_vector = self._vector(query_tokens)
        vector = {fact_id: self._cosine(query_vector, value) for fact_id, value in self.vectors.items()}
        if mode == "lexical":
            scores = lexical
        elif mode == "vector":
            scores = vector
        elif mode == "hybrid":
            scores = {fact_id: 0.5 * lexical[fact_id] + 0.5 * vector[fact_id] for fact_id in lexical}
        else:
            raise workflow.QualificationError(f"unknown retrieval mode: {mode}")
        allowed = {
            fact["fact_id"] for fact in self.facts
            if (subject_type is None or fact["subject_type"] == subject_type)
            and (subject_id is None or fact["subject_id"] == subject_id)
        }
        return sorted(
            ((fact_id, score) for fact_id, score in scores.items() if fact_id in allowed),
            key=lambda item: (-item[1], item[0]),
        )[:limit]


def build_index(root: Path) -> LocalRetrievalIndex:
    schema = workflow.load_json(root / "schemas" / "evidence-memory-document.schema.json")
    policy = workflow.load_json(root / "config" / "semantic-boundaries.json")
    memory = workflow.EvidenceMemory.from_paths(workflow.default_evidence_paths(root), schema, policy["source_policies"])
    return LocalRetrievalIndex(memory.facts.values())
