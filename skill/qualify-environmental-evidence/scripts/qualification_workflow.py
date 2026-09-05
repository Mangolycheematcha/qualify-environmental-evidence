from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_PATHS = (
    ROOT / "data" / "cer" / "eop101132-project-record.json",
    ROOT / "data" / "cer" / "accu-smc-public-definitions.json",
    ROOT / "examples" / "qualification" / "eop101132-frozen-observation.json",
)
TOKEN_RE = re.compile(r"[a-z0-9]+")


class QualificationError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise QualificationError(f"non-standard JSON numeric constant: {value}")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QualificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: Any, path: str = "document") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise QualificationError(f"non-finite number at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{path}[{index}]")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicates,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{path}: top-level JSON value must be an object")
    _reject_non_finite(value)
    return value


def canonical_bytes(value: Any) -> bytes:
    _reject_non_finite(value)
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_schema(instance: dict[str, Any], schema: dict[str, Any], context: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise QualificationError(f"{context} schema error at {location}: {error.message}")


def tokenize(text: str) -> list[str]:
    return sorted(set(TOKEN_RE.findall(text.lower())))


class EvidenceMemory:
    def __init__(
        self,
        documents: Iterable[tuple[Path, dict[str, Any]]],
        schema: dict[str, Any],
        source_policies: dict[str, dict[str, str]],
    ):
        self.documents: dict[str, dict[str, Any]] = {}
        self.facts: dict[str, dict[str, Any]] = {}
        snapshot: list[dict[str, str]] = []
        for path, document in documents:
            validate_schema(document, schema, f"evidence document {path}")
            evidence_id = document["evidence_id"]
            if evidence_id in self.documents:
                raise QualificationError(f"duplicate evidence_id: {evidence_id}")
            source = document["source"]
            source_policy = source_policies.get(source["source_id"])
            if source_policy is None:
                raise QualificationError(f"unregistered evidence source: {source['source_id']}")
            if source["canonical_uri"] != source_policy["canonical_uri"]:
                raise QualificationError(f"canonical URI mismatch for source: {source['source_id']}")
            if source["authority_scope"] != source_policy["authority_scope"]:
                raise QualificationError(f"authority scope mismatch for source: {source['source_id']}")
            document_hash = sha256_bytes(path.read_bytes())
            record = {**document, "_path": str(path), "_sha256": document_hash}
            self.documents[evidence_id] = record
            snapshot.append({"evidence_id": evidence_id, "document_sha256": document_hash})
            for fact in document["facts"]:
                fact_id = fact["fact_id"]
                if fact_id in self.facts:
                    raise QualificationError(f"duplicate fact_id: {fact_id}")
                if fact["authority_scope"] != source["authority_scope"]:
                    raise QualificationError(f"fact authority differs from source authority: {fact_id}")
                self.facts[fact_id] = {
                    **fact,
                    "_evidence_id": evidence_id,
                    "_source": document["source"],
                    "_document_sha256": document_hash,
                }
        self.snapshot_sha256 = sha256_bytes(canonical_bytes(sorted(snapshot, key=lambda x: x["evidence_id"])))

    @classmethod
    def from_paths(
        cls,
        paths: Iterable[Path],
        schema: dict[str, Any],
        source_policies: dict[str, dict[str, str]],
    ) -> "EvidenceMemory":
        resolved = [Path(path).resolve() for path in paths]
        if not resolved:
            raise QualificationError("at least one evidence document is required")
        return cls(((path, load_json(path)) for path in resolved), schema, source_policies)

    def retrieve(
        self,
        *,
        project_id: str,
        claim_family: str,
        question: str,
        required_tags: list[str],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        query_tokens = tokenize(question)
        required = set(required_tags)
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        for fact_id, fact in self.facts.items():
            if claim_family not in fact["claim_families"]:
                continue
            if fact["project_id"] not in {None, project_id}:
                continue
            tags = set(fact["tags"])
            fact_tokens = set(tokenize(fact["text"] + " " + " ".join(fact["tags"])))
            score = 100 * len(tags & required)
            score += 20 if fact["project_id"] == project_id else 0
            score += len(set(query_tokens) & fact_tokens)
            candidates.append((score, fact_id, fact))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        selected = [item[2] for item in candidates if set(item[2]["tags"]) & required]
        trace = {
            "query_tokens": query_tokens,
            "required_tags": sorted(required),
            "candidate_fact_count": len(candidates),
            "selected_fact_ids": [fact["fact_id"] for fact in selected],
        }
        return selected, trace


def default_evidence_paths(root: Path = ROOT) -> tuple[Path, ...]:
    return (
        root / "data" / "cer" / "eop101132-project-record.json",
        root / "data" / "cer" / "accu-smc-public-definitions.json",
        root / "examples" / "qualification" / "eop101132-frozen-observation.json",
    )


def _check_frozen_reference(facts: list[dict[str, Any]], policy: dict[str, Any]) -> bool:
    reference = policy["frozen_step2b_reference"]
    integrity = next((fact for fact in facts if fact["fact_id"] == "EOP101132_V4.INTEGRITY"), None)
    observation = next((fact for fact in facts if fact["fact_id"] == "EOP101132_V4.OBSERVATION"), None)
    if integrity is None or observation is None:
        return False
    return (
        integrity["attributes"].get("executable_commit") == reference["executable_commit"]
        and integrity["attributes"].get("policy_sha256") == reference["policy_sha256"]
        and integrity["attributes"].get("runtime_spec_sha256") == reference["runtime_spec_sha256"]
        and integrity["attributes"].get("assessment_sha256") == reference["assessment_sha256"]
        and integrity["attributes"].get("provenance_sha256") == reference["provenance_sha256"]
        and integrity["attributes"].get("closure") == reference["closure"]
        and observation["attributes"].get("run_id") == reference["run_id"]
    )


def _evidence_refs(facts: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "evidence_id": fact["_evidence_id"],
            "fact_id": fact["fact_id"],
            "source_id": fact["_source"]["source_id"],
            "canonical_uri": fact["_source"]["canonical_uri"],
            "document_sha256": fact["_document_sha256"],
            "authority_scope": fact["authority_scope"],
        }
        for fact in facts
    ]


def _build_statement(claim_family: str, facts: list[dict[str, Any]]) -> tuple[str, str, str, list[str]]:
    by_id = {fact["fact_id"]: fact for fact in facts}
    if claim_family == "REGISTRY_FACTS":
        identity = by_id["CER_EOP101132.IDENTITY"]["attributes"]
        timing = by_id["CER_EOP101132.TIMING"]["attributes"]
        statement = (
            f"The CER public record identifies {identity['project_id']} as {identity['project_name']}, "
            f"a {identity['method_type']} project in {identity['project_location']}, with model start date "
            f"{timing['model_start_date']}. This is a registry-fact restatement, not a project-quality conclusion."
        )
        return "QUALIFIED", "SUPPORTED", statement, []
    if claim_family == "ACCU_SMC_SEMANTIC_BOUNDARY":
        statement = (
            "CER public definitions treat ACCUs and SMCs as distinct concepts: an ACCU relates to emissions "
            "that would otherwise have been released into the atmosphere, while an SMC relates to a Safeguard facility's "
            "emissions below its baseline and is not an offset. This does not establish interchangeability, "
            "equivalent quality, relative price, or trading suitability."
        )
        return "QUALIFIED", "SUPPORTED", statement, []
    observation = by_id["EOP101132_V4.OBSERVATION"]["attributes"]
    statement = (
        f"For EOP101132, the frozen Step 2B assessment recorded PRE median NDVI "
        f"{observation['pre_median_ndvi']}, POST median NDVI {observation['post_median_ndvi']}, and "
        f"POST-minus-PRE delta {observation['delta_ndvi']}. Under the frozen primary tau of "
        f"{observation['primary_tau']}, the evidence disposition is INCONCLUSIVE. This is a bounded "
        "observational result and does not establish causality, carbon quantity, credit quality, compliance, "
        "or financial suitability."
    )
    return "ABSTAINED", "INCONCLUSIVE", statement, [observation["reason_code"]]


def _finalize(result: dict[str, Any], result_schema: dict[str, Any]) -> dict[str, Any]:
    result["result_sha256"] = sha256_bytes(canonical_bytes(result))
    validate_schema(result, result_schema, "qualification result")
    return result


def run_qualification(
    request: dict[str, Any],
    *,
    evidence_paths: Iterable[Path] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    request_schema = load_json(root / "schemas" / "qualification-request.schema.json")
    document_schema = load_json(root / "schemas" / "evidence-memory-document.schema.json")
    result_schema = load_json(root / "schemas" / "qualification-result.schema.json")
    policy = load_json(root / "config" / "semantic-boundaries.json")
    validate_schema(request, request_schema, "qualification request")
    memory = EvidenceMemory.from_paths(
        evidence_paths or default_evidence_paths(root),
        document_schema,
        policy["source_policies"],
    )
    claim_family = request["claim_family"]
    common = {
        "schema_version": "1.0.0",
        "request_id": request["request_id"],
        "project_id": request["project_id"],
        "claim_family": claim_family,
        "must_not_claim": policy["must_not_claim"],
        "human_review_required": True,
        "memory_snapshot_sha256": memory.snapshot_sha256,
    }
    if claim_family in policy["refused_claim_families"]:
        result = {
            **common,
            "workflow_status": "REFUSED",
            "qualification": None,
            "reason_codes": [policy["refused_claim_families"][claim_family]],
            "bounded_statement": None,
            "evidence_refs": [],
            "retrieval_trace": {
                "query_tokens": tokenize(request["question"]),
                "required_tags": [],
                "candidate_fact_count": 0,
                "selected_fact_ids": [],
            },
            "assurance_checks": {
                "request_schema": "PASS",
                "semantic_authority": "FAIL",
                "evidence_identity": "NOT_RUN",
                "source_authority": "NOT_RUN",
                "evidence_completeness": "NOT_RUN",
                "non_inference": "PASS",
                "frozen_result_integrity": "NOT_RUN",
                "deterministic_serialization": "PASS",
            },
            "limitations": [
                "The requested conclusion exceeds the evidence-qualification authority ceiling.",
                "No evidence retrieval or environmental processing was performed for the refused claim."
            ],
        }
        return _finalize(result, result_schema)

    rule = policy["allowed_claim_families"][claim_family]
    facts, trace = memory.retrieve(
        project_id=request["project_id"],
        claim_family=claim_family,
        question=request["question"],
        required_tags=rule["required_fact_tags"],
    )
    observed_tags = {tag for fact in facts for tag in fact["tags"]}
    complete = set(rule["required_fact_tags"]).issubset(observed_tags)
    allowed_authority = {
        "REGISTRY_FACTS": {"PUBLIC_REGISTRY_FACTS"},
        "OBSERVATIONAL_CONSISTENCY": {"PUBLIC_REGISTRY_FACTS", "BOUNDED_OBSERVATION_ONLY"},
        "ACCU_SMC_SEMANTIC_BOUNDARY": {"PUBLIC_UNIT_DEFINITION"},
    }[claim_family]
    source_authority_ok = bool(facts) and all(fact["authority_scope"] in allowed_authority for fact in facts)
    frozen_ok = claim_family != "OBSERVATIONAL_CONSISTENCY" or _check_frozen_reference(facts, policy)
    if not complete or not source_authority_ok or not frozen_ok:
        reason = "PROVENANCE_HASH_MISMATCH" if not frozen_ok else "EVIDENCE_SOURCE_NOT_ALLOWED" if not source_authority_ok else "REQUIRED_EVIDENCE_MISSING"
        result = {
            **common,
            "workflow_status": "ERROR",
            "qualification": None,
            "reason_codes": [reason],
            "bounded_statement": None,
            "evidence_refs": _evidence_refs(facts),
            "retrieval_trace": trace,
            "assurance_checks": {
                "request_schema": "PASS",
                "semantic_authority": "PASS",
                "evidence_identity": "PASS" if facts else "FAIL",
                "source_authority": "PASS" if source_authority_ok else "FAIL",
                "evidence_completeness": "PASS" if complete else "FAIL",
                "non_inference": "PASS",
                "frozen_result_integrity": "PASS" if frozen_ok else "FAIL",
                "deterministic_serialization": "PASS",
            },
            "limitations": ["Qualification stopped because required evidence controls did not pass."],
        }
        return _finalize(result, result_schema)

    status, qualification, statement, reasons = _build_statement(claim_family, facts)
    limitations = [
        "Output is limited to the cited public facts and frozen observational evidence.",
        "Human review is required before use in a regulated financial workflow.",
    ]
    if claim_family == "OBSERVATIONAL_CONSISTENCY":
        limitations.extend([
            "The diagnostic projected-area defect did not affect the scientific path.",
            "GDAL request-level transport provenance is partial and frozen retry semantics were noncompliant.",
        ])
    result = {
        **common,
        "workflow_status": status,
        "qualification": qualification,
        "reason_codes": reasons,
        "bounded_statement": statement,
        "evidence_refs": _evidence_refs(facts),
        "retrieval_trace": trace,
        "assurance_checks": {
            "request_schema": "PASS",
            "semantic_authority": "PASS",
            "evidence_identity": "PASS",
            "source_authority": "PASS",
            "evidence_completeness": "PASS",
            "non_inference": "PASS",
            "frozen_result_integrity": "PASS" if claim_family == "OBSERVATIONAL_CONSISTENCY" else "NOT_RUN",
            "deterministic_serialization": "PASS",
        },
        "limitations": limitations,
    }
    return _finalize(result, result_schema)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the offline deterministic evidence-qualification workflow.")
    parser.add_argument("request", type=Path, help="Qualification request JSON.")
    parser.add_argument("--evidence", action="append", type=Path, help="Evidence document JSON; repeat as needed.")
    parser.add_argument("--json", action="store_true", help="Emit compact machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        request = load_json(args.request.resolve())
        result = run_qualification(request, evidence_paths=args.evidence)
    except QualificationError as exc:
        payload = {"outcome": "INVALID_QUALIFICATION_INPUT", "detail": str(exc)}
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(payload, indent=2))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(result, indent=2))
    return 3 if result["workflow_status"] == "REFUSED" else 4 if result["workflow_status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
