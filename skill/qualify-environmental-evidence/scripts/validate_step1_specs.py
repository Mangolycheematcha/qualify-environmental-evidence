from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from string import Formatter
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from jsonschema import Draft202012Validator, FormatChecker

try:
    from scripts import step2b_offline
    from scripts import approval_protocol_v2
except ImportError:  # Packaged validator is imported with the skill scripts directory on sys.path.
    import approval_protocol_v2
    import step2b_offline


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0"

SOURCE_IDS = [
    "CER_ACCU_PROJECT_REGISTER",
    "CER_PROJECT_RECORD",
    "CER_PUBLISHED_CEA",
    "MSPC_SENTINEL2_L2A",
]
TRANSFORMATION_IDS = [
    "VALIDATE_CLAIM_CONTRACT",
    "CHECK_AUTHORITY_SCOPE",
    "RESOLVE_REGISTRY_FACTS",
    "RESOLVE_CEA_BOUNDARY",
    "SEARCH_SENTINEL2_L2A",
    "ALIGN_AOI_RASTERS",
    "APPLY_SCL_VALIDITY_MASK",
    "CALCULATE_AOI_VALID_COVERAGE",
    "CALCULATE_AOI_NDVI",
    "AGGREGATE_SEASONAL_WINDOWS",
    "QUALIFY_OBSERVATIONAL_CLAIM",
    "EMIT_ASSESSMENT_AND_PROVENANCE",
]
FORBIDDEN_CODES = [
    "CAUSAL_ATTRIBUTION",
    "CARBON_QUANTITY",
    "ADDITIONALITY",
    "CREDIT_VALIDITY_OR_QUALITY",
    "REGULATORY_OR_METHODOLOGY_COMPLIANCE",
    "PERMANENCE",
    "PROJECT_PERFORMANCE_BEYOND_BOUNDED_OBSERVATION",
    "GREENWASHING_OR_LEGAL_LIABILITY",
    "FINANCIAL_RECOMMENDATION",
    "TOKENISATION_READINESS",
]
REQUIRED_REASON_CODES = [
    "CLAIM_NOT_BOUNDED",
    "REQUIRED_FIELD_MISSING",
    "RUNTIME_SPECIFICATION_NOT_FROZEN",
    "EVIDENCE_SOURCE_NOT_ALLOWED",
    "TRANSFORMATION_NOT_ALLOWED",
    "TRANSFORMATION_SEQUENCE_INVALID",
    "BOUNDARY_NOT_FROZEN",
    "TEMPORAL_SCOPE_NOT_FROZEN",
    "SEASONAL_RULE_NOT_FROZEN",
    "SOURCE_UNAVAILABLE",
    "SOURCE_VERSION_UNRESOLVED",
    "CANONICAL_IDENTIFIER_UNRESOLVED",
    "ACQUISITION_IDENTITY_UNRESOLVED",
    "ACQUISITION_REPRESENTATION_AMBIGUOUS",
    "AOI_NO_OVERLAP",
    "SCL_ALIGNMENT_FAILED",
    "PROCESSING_BASELINE_UNRESOLVED",
    "RADIOMETRY_METADATA_UNRESOLVED",
    "SOLAR_GEOMETRY_OUT_OF_RANGE",
    "SOLAR_GEOMETRY_METADATA_UNRESOLVED",
    "VALID_OBSERVATION_COVERAGE_LOW",
    "EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND",
    "METADATA_INVENTORY_LIMIT_EXCEEDED",
    "RESOURCE_LIMIT_EXCEEDED",
    "EVIDENCE_CONFLICT_UNRESOLVED",
    "AUTHORITY_SCOPE_EXCEEDED",
    "CAUSALITY_UNSUPPORTED",
    "CARBON_QUANTITY_UNSUPPORTED",
    "CREDIT_VALIDITY_UNSUPPORTED",
    "COMPLIANCE_UNSUPPORTED",
    "FINANCIAL_DECISION_UNSUPPORTED",
    "PROVENANCE_INCOMPLETE",
    "PROVENANCE_HASH_MISMATCH",
    "APPROVAL_BINDING_INVALID",
    "APPROVAL_EVIDENCE_NOT_INDEPENDENT",
    "APPROVAL_IDENTITY_MISMATCH",
    "APPROVAL_RUN_ID_MISMATCH",
    "APPROVAL_EXPIRED",
    "APPROVAL_ALREADY_CONSUMED",
    "APPROVAL_EVIDENCE_UNAVAILABLE",
    "HUMAN_REVIEW_REQUIRED",
    "DETERMINISTIC_PROCESSING_ERROR",
]
TEMPLATE_IDS = [
    "OBSERVATIONAL_COMPARISON_CORROBORATING_V1",
    "OBSERVATIONAL_COMPARISON_CONTRADICTORY_V1",
    "OBSERVATIONAL_COMPARISON_CORROBORATING_V2",
    "OBSERVATIONAL_COMPARISON_CONTRADICTORY_V2",
]
V1_PLACEHOLDERS = [
    "project_id",
    "pre_window",
    "post_window",
    "pre_value",
    "post_value",
    "qualification_policy_version",
]
V2_PLACEHOLDERS = [
    "project_id",
    "analysis_boundary_role",
    "pre_window",
    "post_window",
    "seasonal_rule_id",
    "aggregation",
    "eligible_population",
    "pre_value",
    "post_value",
    "delta_value",
    "primary_tau",
    "indifference_policy_id",
    "qualification_policy_version",
]
TEMPLATE_PLACEHOLDERS = {
    TEMPLATE_IDS[0]: V1_PLACEHOLDERS,
    TEMPLATE_IDS[1]: V1_PLACEHOLDERS,
    TEMPLATE_IDS[2]: V2_PLACEHOLDERS,
    TEMPLATE_IDS[3]: V2_PLACEHOLDERS,
}
ACTIVE_TEMPLATE_BY_DISPOSITION = {
    "CORROBORATING": TEMPLATE_IDS[2],
    "CONTRADICTORY": TEMPLATE_IDS[3],
}
FORBIDDEN_CLAIM_LANGUAGE = re.compile(
    r"\b(?:persistent|persistence|sustained\s+vegetation\s+development|multi-year\s+trend|climatologically\s+typical)\b",
    flags=re.IGNORECASE,
)
PENDING_STEP_2 = [
    "BOUNDARY_FILE_AND_CHECKSUM",
    "PRE_WINDOW",
    "POST_WINDOW",
    "SEASONAL_MATCHING_RULE",
    "SCL_VALIDITY_RULE",
    "OBSERVATION_COVERAGE_POLICY",
]
LIMITATION = (
    "This bounded observation does not establish causality, carbon quantity, "
    "additionality, ACCU validity, project compliance or financial suitability."
)
REGISTRY_FILES = {
    "evidence_sources": ROOT / "config" / "evidence-sources.json",
    "transformations": ROOT / "config" / "allowed-transformations.json",
    "statement_templates": ROOT / "config" / "statement-templates.json",
    "forbidden_inferences": ROOT / "config" / "forbidden-inferences.json",
    "reason_codes": ROOT / "config" / "reason-codes.json",
}
SCHEMA_FILES = {
    "claim": ROOT / "schemas" / "claim-contract.schema.json",
    "assessment": ROOT / "schemas" / "assessment-output.schema.json",
    "provenance": ROOT / "schemas" / "provenance-manifest.schema.json",
    "approval_request_v2": ROOT / "schemas" / "approval-request-v2.schema.json",
    "approval_verification_v2": ROOT / "schemas" / "approval-verification-v2.schema.json",
    "approval_consumption_v2": ROOT / "schemas" / "approval-consumption-v2.schema.json",
    "run_state_v2": ROOT / "schemas" / "run-state-v2.schema.json",
}
CASE_FILE = ROOT / "cases" / "eop101132" / "case-spec.json"
V3_POLICY_FILE = ROOT / "policies" / "eop101132" / "step2b-proposed-policy.json"
POLICY_FILE = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"
V3_POLICY_SHA256 = "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"


class ContractError(ValueError):
    pass


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant {value!r} is not allowed")


def reject_non_finite(value: Any, context: str = "document", path: tuple[Any, ...] = ()) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        location = ".".join(str(part) for part in path) or "<root>"
        raise ContractError(f"{context}: non-finite number at {location}")
    if isinstance(value, dict):
        for key, item in value.items():
            reject_non_finite(item, context, path + (key,))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_non_finite(item, context, path + (index,))


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = approval_protocol_v2.strict_json_loads(path.read_bytes())
        reject_non_finite(value, str(path))
        return value
    except (OSError, json.JSONDecodeError, ValueError, approval_protocol_v2.ApprovalProtocolError) as exc:
        try:
            display_path = path.relative_to(ROOT)
        except ValueError:
            display_path = path
        raise ContractError(f"cannot load {display_path}: {exc}") from exc


def load_contracts() -> dict[str, Any]:
    return {
        "registries": {name: load_json(path) for name, path in REGISTRY_FILES.items()},
        "schemas": {name: load_json(path) for name, path in SCHEMA_FILES.items()},
        "case": load_json(CASE_FILE),
        "policy": load_json(POLICY_FILE),
    }


def _duplicates(values: list[Any]) -> list[Any]:
    return sorted({value for value in values if values.count(value) > 1})


def _require_keys(item: dict[str, Any], expected: set[str], context: str) -> None:
    missing = expected - set(item)
    extra = set(item) - expected
    if missing:
        raise ContractError(f"{context}: missing required fields {sorted(missing)}")
    if extra:
        raise ContractError(f"{context}: unexpected controlled properties {sorted(extra)}")


def _schema_validate(instance: Any, schema: dict[str, Any], context: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ContractError(f"{context} schema validation failed at {path}: {error.message}")


def validate_schemas(schemas: dict[str, Any]) -> None:
    reject_non_finite(schemas, "schemas")
    for name, schema in schemas.items():
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ContractError(f"{name} schema: Draft 2020-12 declaration is required")
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            raise ContractError(f"{name} schema is not valid Draft 2020-12: {exc}") from exc


def validate_registries(registries: dict[str, Any]) -> None:
    reject_non_finite(registries, "registries")
    for name, registry in registries.items():
        if registry.get("registry_version") != VERSION:
            raise ContractError(f"{name}: registry version must be {VERSION}")

    evidence = registries["evidence_sources"]
    _require_keys(evidence, {"registry_version", "sources"}, "evidence registry")
    source_ids = [item.get("source_id") for item in evidence["sources"]]
    if _duplicates(source_ids):
        raise ContractError(f"evidence registry: duplicate evidence source {_duplicates(source_ids)}")
    if source_ids != SOURCE_IDS:
        unknown = sorted(set(source_ids) - set(SOURCE_IDS))
        missing = sorted(set(SOURCE_IDS) - set(source_ids))
        raise ContractError(f"evidence registry: exact source IDs required; unknown={unknown}, missing={missing}")
    evidence_fields = {
        "source_id", "publisher", "evidence_type", "canonical_uri", "authority_scope",
        "permitted_uses", "prohibited_uses", "stable_identifier_strategy",
        "version_resolution_method", "identity_policy", "step1_status",
    }
    identity_fields = {
        "scheme", "allowed_hosts", "canonical_path_rule", "canonical_path_value",
        "discovery_path_rule", "discovery_path_value", "stable_identifier",
        "bind_project_id", "allowed_query_parameters", "allow_retrieval_uri",
    }
    for item in evidence["sources"]:
        _require_keys(item, evidence_fields, f"source {item.get('source_id')}")
        if item["step1_status"] not in {"IDENTITY_FROZEN", "ARTIFACT_PENDING_STEP_2"}:
            raise ContractError(f"source {item['source_id']}: invalid step1_status")
        if not item["canonical_uri"]:
            raise ContractError(f"source {item['source_id']}: canonical discovery URI is required")
        policy = item["identity_policy"]
        _require_keys(policy, identity_fields, f"source {item['source_id']} identity policy")
        if policy["scheme"] != "https":
            raise ContractError(f"source {item['source_id']}: identity scheme must be https")
        if not policy["allowed_hosts"] or any(host != host.lower() for host in policy["allowed_hosts"]):
            raise ContractError(f"source {item['source_id']}: allowed_hosts must contain exact lowercase hosts")
        if policy["canonical_path_rule"] not in {"EXACT", "PROJECT_PATH", "PROJECT_TOKEN"}:
            raise ContractError(f"source {item['source_id']}: invalid canonical_path_rule")
        if policy["discovery_path_rule"] not in {"EXACT", "PROJECT_PATH", "PROJECT_TOKEN"}:
            raise ContractError(f"source {item['source_id']}: invalid discovery_path_rule")
        if policy["allowed_query_parameters"] != []:
            raise ContractError(f"source {item['source_id']}: canonical query parameters must be empty in Step 1")

    transformations = registries["transformations"]
    _require_keys(transformations, {"registry_version", "transformations"}, "transformation registry")
    items = transformations["transformations"]
    ids = [item.get("transformation_id") for item in items]
    if _duplicates(ids):
        raise ContractError(f"transformation registry: duplicate transformation {_duplicates(ids)}")
    if ids != TRANSFORMATION_IDS:
        raise ContractError("transformation registry: exact transformation sequence is required")
    if [item.get("sequence") for item in items] != list(range(1, 13)):
        raise ContractError("transformation registry: sequence numbers must be contiguous 1..12")
    transformation_fields = {
        "sequence", "transformation_id", "purpose", "input_types", "output_types",
        "parameter_source", "implementation_stage", "required_audit_fields", "prohibited_behaviors",
    }
    audit_fields = {
        "implementation_version", "parameter_set_ref", "parameter_set_sha256",
        "input_artifact_refs", "output_artifact_refs", "status",
    }
    for item in items:
        _require_keys(item, transformation_fields, f"transformation {item.get('transformation_id')}")
        if item["parameter_source"] not in {"NONE", "FROZEN_CASE_SPEC", "DETERMINISTIC_DERIVATION"}:
            raise ContractError(f"transformation {item['transformation_id']}: invalid parameter_source")
        if item["implementation_stage"] not in {"STEP_1_CONTRACT_ONLY", "STEP_2_OR_LATER"}:
            raise ContractError(f"transformation {item['transformation_id']}: invalid implementation_stage")
        item_audit_fields = set(item["required_audit_fields"])
        if not audit_fields.issubset(item_audit_fields):
            raise ContractError(f"transformation {item['transformation_id']}: incomplete required audit fields")
        acquisition_audit_fields = {
            "raw_item_counts", "processing_representation_records", "acquisition_group_records",
            "metadata_admissibility_records", "resource_limit_decision",
        }
        expected_audit_fields = audit_fields.union(acquisition_audit_fields) if item["transformation_id"] == "SEARCH_SENTINEL2_L2A" else audit_fields
        if item_audit_fields != expected_audit_fields:
            raise ContractError(f"transformation {item['transformation_id']}: unexpected required audit fields")

    forbidden = registries["forbidden_inferences"]
    _require_keys(forbidden, {"registry_version", "forbidden_inferences"}, "forbidden-inference registry")
    forbidden_ids = [item.get("code") for item in forbidden["forbidden_inferences"]]
    if _duplicates(forbidden_ids):
        raise ContractError(f"forbidden-inference registry: duplicate code {_duplicates(forbidden_ids)}")
    if forbidden_ids != FORBIDDEN_CODES:
        raise ContractError("forbidden-inference registry: exact canonical codes and order are required")
    for item in forbidden["forbidden_inferences"]:
        _require_keys(item, {"code", "description", "outside_authority_reason"}, f"forbidden inference {item.get('code')}")

    reasons = registries["reason_codes"]
    _require_keys(reasons, {"registry_version", "reason_codes", "semantics"}, "reason-code registry")
    reason_ids = [item.get("code") for item in reasons["reason_codes"]]
    if _duplicates(reason_ids):
        raise ContractError(f"reason-code registry: duplicate reason code {_duplicates(reason_ids)}")
    if not set(REQUIRED_REASON_CODES).issubset(reason_ids):
        raise ContractError(f"reason-code registry: missing required codes {sorted(set(REQUIRED_REASON_CODES) - set(reason_ids))}")
    categories = {"SPECIFICATION", "SOURCE_VERSION", "SPATIAL", "TEMPORAL", "OBSERVATION_QUALITY", "QUALIFICATION", "RESOURCE_LIMIT", "EVIDENCE_CONFLICT", "AUTHORITY", "PROVENANCE", "GOVERNANCE", "SYSTEM"}
    for item in reasons["reason_codes"]:
        _require_keys(item, {"code", "category", "description", "default_execution_status", "default_human_review_required"}, f"reason code {item.get('code')}")
        if item["category"] not in categories:
            raise ContractError(f"reason code {item['code']}: unknown category")
        expected_status = "REFUSED" if item["category"] == "AUTHORITY" else "ERROR" if item["category"] == "SYSTEM" else "ABSTAINED"
        if item["default_execution_status"] != expected_status:
            raise ContractError(f"reason code {item['code']}: category must default to {expected_status}")
    semantics = reasons["semantics"]
    if list(semantics) != reason_ids:
        raise ContractError("reason-code registry: semantics must cover every reason once in canonical order")
    semantic_fields = {
        "allowed_execution_statuses", "allowed_dispositions", "quality_check_requirements",
        "incompatible_reason_codes", "human_review_required",
    }
    known_checks = {"claim_contract", "evidence_allowlist", "transformation_allowlist", "spatial_scope", "temporal_scope", "observation_coverage", "evidence_consistency", "authority_scope", "provenance", "system_execution"}
    for code, rule in semantics.items():
        _require_keys(rule, semantic_fields, f"reason semantics {code}")
        if not rule["allowed_execution_statuses"] or not set(rule["allowed_execution_statuses"]).issubset({"ABSTAINED", "REFUSED", "ERROR"}):
            raise ContractError(f"reason semantics {code}: invalid allowed execution statuses")
        if not set(rule["allowed_dispositions"]).issubset({"INCONCLUSIVE", None}):
            raise ContractError(f"reason semantics {code}: invalid allowed dispositions")
        if not set(rule["quality_check_requirements"]).issubset(known_checks):
            raise ContractError(f"reason semantics {code}: unknown quality-check key")
        if any(not set(states).issubset({"PASS", "FAIL", "NOT_RUN"}) for states in rule["quality_check_requirements"].values()):
            raise ContractError(f"reason semantics {code}: invalid quality-check state")
        if code == "EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND":
            if set(rule["quality_check_requirements"]) != known_checks or any(states != ["PASS"] for states in rule["quality_check_requirements"].values()):
                raise ContractError("reason semantics EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND: every upstream check must PASS")
        elif any("PASS" in states for states in rule["quality_check_requirements"].values()):
            raise ContractError(f"reason semantics {code}: only the operational indifference-band reason may require PASS")
        if not set(rule["incompatible_reason_codes"]).issubset(reason_ids):
            raise ContractError(f"reason semantics {code}: unknown incompatible reason code")
        if rule["human_review_required"] is not True:
            raise ContractError(f"reason semantics {code}: terminal reason must require human review")

    templates = registries["statement_templates"]
    _require_keys(templates, {"registry_version", "templates"}, "statement-template registry")
    template_ids = [item.get("template_id") for item in templates["templates"]]
    if _duplicates(template_ids):
        raise ContractError(f"statement-template registry: duplicate template {_duplicates(template_ids)}")
    if template_ids != TEMPLATE_IDS:
        raise ContractError("statement-template registry: exact template IDs and order are required")
    for item in templates["templates"]:
        _require_keys(item, {"template_id", "required_disposition", "template_text", "allowed_placeholders", "mandatory_limitation_text"}, f"template {item.get('template_id')}")
        found = [field for _, field, _, _ in Formatter().parse(item["template_text"]) if field]
        expected_placeholders = TEMPLATE_PLACEHOLDERS[item["template_id"]]
        if item["allowed_placeholders"] != expected_placeholders or sorted(found) != sorted(expected_placeholders):
            raise ContractError(f"template {item['template_id']}: placeholders must match the controlled set")
        if item["mandatory_limitation_text"] != LIMITATION or not item["template_text"].endswith(LIMITATION):
            raise ContractError(f"template {item['template_id']}: exact mandatory limitation is required")
        if item["template_id"] in ACTIVE_TEMPLATE_BY_DISPOSITION.values() and FORBIDDEN_CLAIM_LANGUAGE.search(item["template_text"]):
            raise ContractError(f"template {item['template_id']}: forbidden ecological-duration language")
    required_dispositions = [item["required_disposition"] for item in templates["templates"]]
    if required_dispositions != ["CORROBORATING", "CONTRADICTORY", "CORROBORATING", "CONTRADICTORY"]:
        raise ContractError("statement-template registry: dispositions do not match template IDs")


def _registry_maps(registries: dict[str, Any]) -> dict[str, Any]:
    return {
        "sources": {item["source_id"]: item for item in registries["evidence_sources"]["sources"]},
        "transformations": {item["transformation_id"]: item for item in registries["transformations"]["transformations"]},
        "forbidden": {item["code"]: item for item in registries["forbidden_inferences"]["forbidden_inferences"]},
        "reasons": {item["code"]: item for item in registries["reason_codes"]["reason_codes"]},
        "templates": {item["template_id"]: item for item in registries["statement_templates"]["templates"]},
    }


SIGNED_OR_EXPIRING_PARAMETERS = {
    "sig", "signature", "token", "access_token", "se", "sp", "sr", "st", "sv",
    "policy", "key-pair-id", "expires", "googleaccessid", "x-goog-signature",
}


def _query_parameter_is_credential(name: str) -> bool:
    lowered = name.lower()
    return lowered in SIGNED_OR_EXPIRING_PARAMETERS or lowered.startswith("x-amz-")


def _split_secure_uri(uri: str, context: str):
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError as exc:
        raise ContractError(f"{context}: malformed URI: {exc}") from exc
    if parsed.username is not None or parsed.password is not None:
        raise ContractError(f"{context}: URI userinfo is prohibited")
    if parsed.fragment:
        raise ContractError(f"{context}: URI fragments are prohibited")
    if port is not None:
        raise ContractError(f"{context}: unexpected URI port {port}")
    return parsed


def _validate_temporary_retrieval_uri(uri: str, policy: dict[str, Any], context: str) -> None:
    if not policy["allow_retrieval_uri"]:
        raise ContractError(f"{context}: retrieval_uri is not permitted for this source")
    parsed = _split_secure_uri(uri, context)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ContractError(f"{context}: retrieval_uri must use https with a hostname")


def _validate_evidence_uri(
    uri: str,
    policy: dict[str, Any],
    role: str,
    context: str,
    project_id: str | None = None,
) -> None:
    parsed = _split_secure_uri(uri, context)
    if parsed.scheme.lower() != policy["scheme"]:
        raise ContractError(f"{context}: canonical identity must use exact scheme {policy['scheme']}")
    host = (parsed.hostname or "").lower()
    if host not in policy["allowed_hosts"]:
        raise ContractError(f"{context}: hostname {host!r} is not an exact allowlisted host")
    query_names = [name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)]
    credentials = sorted({name for name in query_names if _query_parameter_is_credential(name)}, key=str.lower)
    if credentials:
        raise ContractError(f"{context}: canonical identity contains signed or expiring credential parameters {credentials}")
    unexpected = sorted({name for name in query_names if name not in policy["allowed_query_parameters"]})
    if unexpected:
        raise ContractError(f"{context}: canonical identity contains unexpected query parameters {unexpected}")

    rule = policy[f"{role}_path_rule"]
    value = policy[f"{role}_path_value"]
    path = parsed.path
    if rule == "EXACT" and path != value:
        raise ContractError(f"{context}: canonical path must equal {value}")
    if rule == "PROJECT_PATH":
        if not project_id:
            raise ContractError(f"{context}: project identity is required for source binding")
        expected = f"{value}{project_id}"
        if path != expected:
            raise ContractError(f"{context}: canonical project path must equal {expected}")
    if rule == "PROJECT_TOKEN":
        if not project_id:
            raise ContractError(f"{context}: project identity is required for source binding")
        token = re.compile(rf"(?<![A-Za-z0-9]){re.escape(project_id)}(?![A-Za-z0-9])")
        if not path.startswith(value) or not token.search(path):
            raise ContractError(f"{context}: canonical artifact path must contain exact project ID {project_id}")
    if rule != "PROJECT_TOKEN" and policy["stable_identifier"].lower() not in path.lower():
        raise ContractError(f"{context}: canonical path is missing stable identifier {policy['stable_identifier']}")


def validate_case(case: dict[str, Any], schemas: dict[str, Any], registries: dict[str, Any]) -> None:
    reject_non_finite(case, "case")
    maps = _registry_maps(registries)
    allowed = case.get("evidence_policy", {}).get("allowed_source_ids", [])
    unknown = sorted(set(allowed) - set(maps["sources"]))
    if unknown:
        raise ContractError(f"case: unknown evidence source {unknown}")
    if _duplicates(allowed):
        raise ContractError(f"case: duplicate evidence source {_duplicates(allowed)}")

    bindings = case.get("evidence_policy", {}).get("source_bindings", [])
    binding_ids = [item.get("source_id") for item in bindings]
    if _duplicates(binding_ids):
        raise ContractError(f"case: duplicate source binding {_duplicates(binding_ids)}")
    missing = sorted(set(allowed) - set(binding_ids))
    extra = sorted(set(binding_ids) - set(allowed))
    if missing or extra:
        raise ContractError(f"case: exactly one source binding is required for each allowed source; missing={missing}, extra={extra}")
    project_id = case.get("project", {}).get("project_id")
    project_registry_url = case.get("project", {}).get("registry_url")
    if project_registry_url:
        project_policy = maps["sources"]["CER_PROJECT_RECORD"]["identity_policy"]
        _validate_evidence_uri(project_registry_url, project_policy, "canonical", "case project registry_url", project_id)
    for binding in bindings:
        source_id = binding.get("source_id")
        if source_id not in maps["sources"]:
            raise ContractError(f"case source binding: unknown evidence source {source_id!r}")
        policy = maps["sources"][source_id]["identity_policy"]
        if binding.get("binding_status") == "PENDING_STEP_2":
            if binding.get("canonical_uri") is not None:
                raise ContractError(f"case source binding {binding.get('source_id')}: pending binding cannot contain a fabricated canonical artifact URI")
            if not binding.get("discovery_uri"):
                raise ContractError(f"case source binding {binding.get('source_id')}: pending binding requires discovery_uri")
            _validate_evidence_uri(binding["discovery_uri"], policy, "discovery", f"case source binding {source_id} discovery_uri", project_id)
        elif binding.get("binding_status") == "FROZEN" and not binding.get("canonical_uri"):
            raise ContractError(f"case source binding {source_id}: frozen binding requires canonical_uri")
        elif binding.get("binding_status") == "FROZEN":
            _validate_evidence_uri(binding["canonical_uri"], policy, "canonical", f"case source binding {source_id} canonical_uri", project_id)
        if binding.get("discovery_uri") and binding.get("binding_status") != "PENDING_STEP_2":
            _validate_evidence_uri(binding["discovery_uri"], policy, "discovery", f"case source binding {source_id} discovery_uri", project_id)
        if binding.get("retrieval_uri"):
            if not binding.get("canonical_uri"):
                raise ContractError(f"case source binding {source_id}: retrieval_uri requires a separately validated canonical_uri")
            _validate_temporary_retrieval_uri(binding["retrieval_uri"], policy, f"case source binding {source_id} retrieval_uri")

    required_transformations = case.get("transformation_policy", {}).get("required_transformation_ids", [])
    unknown_transformations = sorted(set(required_transformations) - set(maps["transformations"]))
    if unknown_transformations:
        raise ContractError(f"case: unknown transformation {unknown_transformations}")
    if _duplicates(required_transformations):
        raise ContractError(f"case: duplicate transformation {_duplicates(required_transformations)}")
    if required_transformations != TRANSFORMATION_IDS:
        raise ContractError("case: transformation sequence invalid; exact registered order is required")

    forbidden = case.get("claim_contract", {}).get("forbidden_inferences", [])
    if forbidden != FORBIDDEN_CODES:
        raise ContractError("case: all forbidden inference codes are required once in canonical order")

    claim = case.get("claim_contract", {})
    if FORBIDDEN_CLAIM_LANGUAGE.search(claim.get("claim_text", "")):
        raise ContractError("case: authoritative claim contains forbidden ecological-duration language")
    policy = case.get("qualification_policy", {})
    band = policy.get("indifference_band", {})
    bindings = {
        "primary_indifference_band_policy_id": band.get("policy_id"),
        "primary_tau": band.get("tau"),
        "metric": band.get("metric"),
    }
    for field, expected in bindings.items():
        if claim.get(field) != expected:
            raise ContractError(f"case: claim {field} does not match qualification policy")
    if policy.get("sensitivity_tau_values") != [0.01, 0.02, 0.05]:
        raise ContractError("case: sensitivity tau values must be the frozen [0.01, 0.02, 0.05]")
    if policy.get("approval_status") == "PENDING_HUMAN_APPROVAL" and case.get("runtime_ready") is not False:
        raise ContractError("case: runtime_ready cannot be true while human approval is pending")
    temporal = case.get("temporal_scope", {})
    if temporal.get("status") == "FROZEN":
        if claim.get("pre_window_identity") != temporal.get("pre_window") or claim.get("post_window_identity") != temporal.get("post_window"):
            raise ContractError("case: claim window identities do not match frozen temporal scope")
    if case.get("spatial_scope", {}).get("status") == "FROZEN" and claim.get("analysis_boundary_role") != "CEA":
        raise ContractError("case: frozen analysis boundary role must be CEA")

    pending = case.get("pending_step_2", [])
    scientific_pending = (
        case.get("spatial_scope", {}).get("status") != "FROZEN"
        or not case.get("spatial_scope", {}).get("boundary_artifact_uri")
        or not case.get("spatial_scope", {}).get("boundary_sha256")
        or case.get("temporal_scope", {}).get("status") != "FROZEN"
        or not case.get("temporal_scope", {}).get("pre_window")
        or not case.get("temporal_scope", {}).get("post_window")
        or case.get("temporal_scope", {}).get("seasonal_rule") in (None, "PENDING_STEP_2")
        or case.get("qualification_policy", {}).get("scl_rule") in (None, "PENDING_STEP_2")
        or case.get("qualification_policy", {}).get("observation_coverage_rule") in (None, "PENDING_STEP_2")
        or case.get("qualification_policy", {}).get("approval_status") != "APPROVED"
    )
    if case.get("runtime_ready") and (pending or scientific_pending):
        raise ContractError("case: runtime_ready cannot be true while Step 2 fields are pending or null")
    if case.get("runtime_ready") is False and not pending and not scientific_pending:
        raise ContractError("case: fully frozen runtime specification must set runtime_ready true")

    _schema_validate(case, schemas["claim"], "case")


def validate_policy_proposal(policy: dict[str, Any], case: dict[str, Any]) -> None:
    reject_non_finite(policy, "Step 2B policy proposal")
    if policy.get("policy_schema_version") != "1.3.0" or policy.get("policy_id") != "DEMO_QUALIFICATION_POLICY_EOP101132_V4":
        raise ContractError("Step 2B policy: unexpected policy identity")
    if policy.get("contract_version") != VERSION or policy.get("runtime_ready") is not False:
        raise ContractError("Step 2B policy: contract version or runtime_ready mismatch")
    approval = policy.get("approval", {})
    if policy.get("approval_status") != "PENDING_HUMAN_APPROVAL" or policy.get("proposed_execution_mode") != "QUALIFICATION":
        raise ContractError("Step 2B policy: top-level approval and proposed mode must remain pending QUALIFICATION")
    if approval.get("status") != policy["approval_status"] or approval.get("proposed_execution_mode") != policy["proposed_execution_mode"]:
        raise ContractError("Step 2B policy: must remain pending with proposed QUALIFICATION mode")
    if approval.get("sentinel_2_access_permitted") is not False:
        raise ContractError("Step 2B policy: Sentinel-2 access must remain prohibited before approval")
    if approval.get("approved_policy_sha256") is not None:
        raise ContractError("Step 2B policy: pending proposal cannot contain an approved policy hash")
    claim = case["claim_contract"]
    bounded_claim = policy.get("bounded_claim", {})
    claim_mapping = {
        "claim_text": "claim_text",
        "analysis_boundary_role": "analysis_boundary_role",
        "seasonal_rule_id": "seasonal_rule_id",
        "metric_id": "metric",
        "aggregation": "aggregation",
        "eligible_population": "eligible_population",
        "primary_tau": "primary_tau",
        "indifference_policy_id": "primary_indifference_band_policy_id",
    }
    for policy_field, case_field in claim_mapping.items():
        if bounded_claim.get(policy_field) != claim.get(case_field):
            raise ContractError(f"Step 2B policy: bounded claim {policy_field} mismatch")
    if bounded_claim.get("qualification_policy_version") != case["qualification_policy"]["policy_version"]:
        raise ContractError("Step 2B policy: bounded claim policy version mismatch")
    temporal = policy.get("temporal_scope", {})
    expected_temporal_fields = {
        "pre_window", "post_window", "seasonal_matching_rule", "rule_type", "citation",
        "rationale", "authority_limitation", "baseline_limitation", "baseline_year_scope",
        "future_extension_rule", "sensitivity_values",
    }
    if set(temporal) != expected_temporal_fields:
        raise ContractError("Step 2B policy: temporal scope contains an undeclared primary or extension field")
    if temporal.get("pre_window") != claim["pre_window_identity"] or temporal.get("post_window") != claim["post_window_identity"]:
        raise ContractError("Step 2B policy: temporal windows do not match the authoritative claim")
    band = policy.get("operational_indifference_band", {})
    expected_band_fields = {
        "policy_id", "metric", "metric_id", "tau", "unit", "lower_boundary_inclusive",
        "upper_boundary_inclusive", "comparison_semantics", "serialization_tolerance",
        "epistemic_status", "ecological_standard", "regulatory_standard",
        "instrument_detection_limit", "assurance_standard", "cer_rule", "selection_rationale",
        "primary_terminal_rule", "sensitivity_tau_values", "sensitivity_rule", "rule_type",
        "rationale", "authority_limitation",
    }
    if set(band) != expected_band_fields:
        raise ContractError("Step 2B policy: indifference-band authoritative fields must match the controlled set")
    expected_band = case["qualification_policy"]["indifference_band"]
    for policy_field, case_field in (("policy_id", "policy_id"), ("metric_id", "metric"), ("tau", "tau"), ("unit", "unit")):
        if band.get(policy_field) != expected_band.get(case_field):
            raise ContractError(f"Step 2B policy: indifference-band {policy_field} mismatch")
    if band.get("sensitivity_tau_values") != case["qualification_policy"]["sensitivity_tau_values"]:
        raise ContractError("Step 2B policy: sensitivity tau values mismatch")
    expected_rationale = {
        "selection_timing": "PRE_OBSERVATION",
        "selection_basis": "CONSERVATIVE_POC_OPERATIONAL_MARGIN",
        "purpose": [
            "prevent sign-only or numerically small NDVI differences from forcing a decisive disposition",
            "provide an explicit abstention region for known residual measurement and processing uncertainty",
        ],
        "motivating_uncertainties": [
            "Sentinel-2 L2A surface-reflectance uncertainty",
            "SCL classification and cloud-edge limitations",
            "residual processing-baseline and radiometric differences",
            "BRDF and illumination-geometry differences",
            "classification-boundary and resampling effects",
        ],
        "quantitatively_derived_detection_limit": False,
        "ecological_threshold": False,
        "regulatory_threshold": False,
        "assurance_standard": False,
        "cer_rule": False,
        "requires_future_domain_validation": True,
    }
    if band.get("selection_rationale") != expected_rationale:
        raise ContractError("Step 2B policy: tau rationale must preserve the exact ex-ante epistemic status")
    for field in ("instrument_detection_limit", "ecological_standard", "regulatory_standard", "assurance_standard", "cer_rule"):
        if band.get(field) is not False:
            raise ContractError(f"Step 2B policy: tau cannot be represented as {field}")
    if band.get("epistemic_status") != "DEMO_OPERATIONAL_RULE":
        raise ContractError("Step 2B policy: tau epistemic status must remain a demo operational rule")
    scene_rule = policy.get("scene_admissibility", {})
    expected_scene_values = {
        "rule_id": "SENTINEL2_MEAN_SOLAR_ZENITH_MAX_V1",
        "field": "mean_solar_zenith_angle",
        "maximum_degrees": 70.0,
        "maximum_inclusive": True,
        "metadata_resolution": "PER_ITEM_OR_GRANULE",
        "inference_from_date_or_location": "FORBIDDEN",
        "application_stage": "BEFORE_ADMISSIBLE_ACQUISITION_GROUP_RESOURCE_COUNT_AND_COVERAGE",
        "scientific_basis": "COPERNICUS_QUANTITATIVE_USE_LIMIT",
    }
    if any(scene_rule.get(field) != expected for field, expected in expected_scene_values.items()):
        raise ContractError("Step 2B policy: solar-zenith scene-admissibility rule mismatch")
    if scene_rule.get("item_level_reason_codes") != {
        "above_maximum": "SOLAR_GEOMETRY_OUT_OF_RANGE",
        "metadata_unresolved": "SOLAR_GEOMETRY_METADATA_UNRESOLVED",
    }:
        raise ContractError("Step 2B policy: solar-geometry reason-code binding mismatch")
    baseline = temporal.get("baseline_year_scope", {})
    expected_baseline = {
        "primary_pre_years": [2017],
        "primary_post_years": [2025],
        "additional_baseline_years": [],
        "interannual_baseline_variability_estimated": False,
        "climatological_typicality_claimed": False,
        "post_result_window_changes_permitted": False,
        "future_additional_years_require_new_policy_id": True,
        "future_additional_years_require_new_run_id": True,
        "future_additional_years_cannot_replace_primary_disposition": True,
    }
    if baseline != expected_baseline:
        raise ContractError("Step 2B policy: baseline-year immutability rule mismatch")
    selection = policy.get("stac_source_and_selection", {})
    if "scene_cloud_prefilter_max_percent" in selection or any("cloud" in value.lower() for value in selection.get("query_predicates", [])):
        raise ContractError("Step 2B policy: eo:cloud_cover must not be a query predicate")
    boundary = policy.get("project_and_boundary", {})
    if boundary.get("analysis_boundary_role") != "CEA" or boundary.get("analysis_boundary_sha256") != boundary.get("boundary_raw_sha256"):
        raise ContractError("Step 2B policy: CEA boundary identity mismatch")
    if policy.get("qualification", {}).get("qualification_policy_version") != VERSION:
        raise ContractError("Step 2B policy: qualification policy version mismatch")
    guards = policy.get("runtime_guards", {})
    if guards.get("approved_policy_hash_required_before_network_access") is not True or guards.get("approved_policy_sha256") is not None:
        raise ContractError("Step 2B policy: pending proposal must require an external approved hash before network access")
    if any(field in guards for field in ("maximum_items_per_window", "item_limit_reason_code", "item_limit_rule")):
        raise ContractError("Step 2B policy: V3 raw-item raster-limit fields must not survive in V4")
    expected_guard_values = {
        "raw_stac_items_per_window_max": 200,
        "raw_stac_item_limit_stage": "AFTER_COMPLETE_STAC_PAGINATION_BEFORE_REMOTE_METADATA_ASSET_OR_RASTER_ACCESS",
        "independent_admissible_acquisition_groups_per_window_max": 40,
        "acquisition_group_limit_stage": "AFTER_COMPLETE_RAW_INVENTORY_GROUPING_REPRESENTATION_RESOLUTION_AND_METADATA_ADMISSIBILITY_BEFORE_RASTER_ACCESS",
        "acquisition_group_limit_reason_code": "RESOURCE_LIMIT_EXCEEDED",
        "metadata_only_before_raster_limit": True,
        "environmental_selection_prohibited": True,
    }
    if any(guards.get(field) != expected for field, expected in expected_guard_values.items()):
        raise ContractError("Step 2B policy: V4 resource-limit values or application stages mismatch")
    if guards.get("raw_stac_item_limit_reason_codes") != [
        "METADATA_INVENTORY_LIMIT_EXCEEDED",
        "RESOURCE_LIMIT_EXCEEDED",
    ]:
        raise ContractError("Step 2B policy: raw metadata inventory reason-code binding mismatch")
    grouping = policy.get("acquisition_grouping", {})
    if grouping.get("rule_id") != "SENTINEL2_METADATA_ONLY_ACQUISITION_GROUPING_V1":
        raise ContractError("Step 2B policy: acquisition grouping rule is missing")
    if grouping.get("independent_acquisition_identity") != ["platform", "s2:datatake_id"]:
        raise ContractError("Step 2B policy: independent acquisition identity mismatch")
    if grouping.get("processing_representation_identity") != ["platform", "s2:datatake_id", "MGRS tile"]:
        raise ContractError("Step 2B policy: processing representation identity mismatch")
    if grouping.get("reason_codes") != {
        "identity_unresolved": "ACQUISITION_IDENTITY_UNRESOLVED",
        "representation_ambiguous": "ACQUISITION_REPRESENTATION_AMBIGUOUS",
    }:
        raise ContractError("Step 2B policy: acquisition reason-code bindings mismatch")
    forbidden_selection = set(grouping.get("no_environmental_selection_fields", []))
    required_forbidden = {
        "eo:cloud_cover",
        "AOI valid-pixel fraction",
        "SCL distribution",
        "NDVI",
        "visual appearance",
        "expected disposition",
        "closeness to a preferred result",
    }
    if forbidden_selection != required_forbidden:
        raise ContractError("Step 2B policy: environmental selection prohibitions mismatch")


def canonical_json_bytes(value: Any) -> bytes:
    reject_non_finite(value, "canonical JSON")
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError(f"canonical JSON serialization failed: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _format_number(value: int | float) -> str:
    return str(value)


def _canonical_decimal(value: Any, field: str):
    try:
        return step2b_offline.canonical_decimal(value, field)
    except step2b_offline.OfflineContractError as exc:
        raise ContractError(str(exc)) from exc


def render_statement(assessment: dict[str, Any], registries: dict[str, Any]) -> str:
    template_id = assessment.get("statement_template_id")
    templates = _registry_maps(registries)["templates"]
    if template_id not in templates:
        raise ContractError(f"assessment: unknown statement template {template_id!r}")
    parameters = assessment.get("statement_parameters")
    if not isinstance(parameters, dict):
        raise ContractError("assessment: completed statement requires controlled statement_parameters")
    observations = assessment.get("observations") or {}
    if parameters.get("pre_value") != _format_number(observations.get("pre_window_ndvi_median")):
        raise ContractError("assessment: statement pre_value does not match observations")
    if parameters.get("post_value") != _format_number(observations.get("post_window_ndvi_median")):
        raise ContractError("assessment: statement post_value does not match observations")
    if parameters.get("delta_value") != _format_number(observations.get("delta_ndvi")):
        raise ContractError("assessment: statement delta_value does not match observations")
    if parameters.get("primary_tau") != _format_number(observations.get("primary_tau")):
        raise ContractError("assessment: statement primary_tau does not match observations")
    if parameters.get("qualification_policy_version") != assessment.get("qualification_policy_version"):
        raise ContractError("assessment: statement qualification policy version mismatch")
    return templates[template_id]["template_text"].format(**parameters)


def _window_label(window: dict[str, Any]) -> str:
    return f"{window['start_date']}/{window['end_date']}"


def _validate_distribution(distribution: dict[str, Any] | None, complete: bool) -> None:
    if distribution is None:
        if complete:
            raise ContractError("assessment observations: COMPLETE requires delta_distribution")
        return
    reject_non_finite(distribution, "assessment delta_distribution")
    if distribution.get("count", 0) < 1:
        raise ContractError("assessment delta_distribution: count must be positive")
    for field in ("q05", "q25", "median", "q75", "q95", "iqr"):
        if isinstance(distribution.get(field), bool) or not isinstance(distribution.get(field), (int, float)):
            raise ContractError(f"assessment delta_distribution: {field} must be finite")
    mad = distribution.get("mad")
    if mad is not None and (isinstance(mad, bool) or not isinstance(mad, (int, float))):
        raise ContractError("assessment delta_distribution: mad must be finite or null")
    if not distribution["q05"] <= distribution["q25"] <= distribution["median"] <= distribution["q75"] <= distribution["q95"]:
        raise ContractError("assessment delta_distribution: quantiles must be ordered")
    if distribution["iqr"] < 0 or (mad is not None and mad < 0):
        raise ContractError("assessment delta_distribution: dispersion must be non-negative")


def _validate_observations(observations: dict[str, Any] | None, status: str, reasons: list[str]) -> None:
    if observations is None:
        return
    reject_non_finite(observations, "assessment observations")
    observation_status = observations.get("observation_status")
    fields = (
        "aoi_total_pixels", "aoi_valid_pixels", "aoi_valid_fraction",
        "pre_window_ndvi_median", "post_window_ndvi_median", "delta_ndvi",
        "primary_tau", "delta_distribution", "sensitivity_results",
    )
    if observation_status == "COMPLETE" and any(observations.get(field) is None for field in fields):
        raise ContractError("assessment observations: COMPLETE requires all measurement fields")
    total = observations.get("aoi_total_pixels")
    valid = observations.get("aoi_valid_pixels")
    fraction = observations.get("aoi_valid_fraction")
    if total is not None and (isinstance(total, bool) or not isinstance(total, int) or total < 0):
        raise ContractError("assessment observations: aoi_total_pixels must be a non-negative integer")
    if valid is not None and (isinstance(valid, bool) or not isinstance(valid, int) or valid < 0):
        raise ContractError("assessment observations: aoi_valid_pixels must be a non-negative integer")
    if total is not None and valid is not None and valid > total:
        raise ContractError("assessment observations: aoi_valid_pixels must not exceed aoi_total_pixels")
    if fraction is not None and not 0 <= fraction <= 1:
        raise ContractError("assessment observations: aoi_valid_fraction must be within [0, 1]")
    if total is not None and valid is not None and fraction is not None and total > 0:
        if abs(fraction - valid / total) > 1e-12:
            raise ContractError("assessment observations: aoi_valid_fraction does not match pixel arithmetic within tolerance 1e-12")
    for field in ("pre_window_ndvi_median", "post_window_ndvi_median"):
        value = observations.get(field)
        if value is not None and not -1 <= value <= 1:
            raise ContractError(f"assessment observations: {field} must be within [-1, 1]")
    delta = observations.get("delta_ndvi")
    if delta is not None and not -2 <= delta <= 2:
        raise ContractError("assessment observations: delta_ndvi must be within [-2, 2]")
    tau = observations.get("primary_tau")
    if tau is not None and _canonical_decimal(tau, "primary_tau") != step2b_offline.PRIMARY_TAU:
        raise ContractError("assessment observations: primary_tau must equal the frozen 0.03")
    _validate_distribution(observations.get("delta_distribution"), observation_status == "COMPLETE")
    sensitivity_results = observations.get("sensitivity_results")
    if observation_status == "COMPLETE" and (not isinstance(sensitivity_results, list) or len(sensitivity_results) != 3):
        raise ContractError("assessment observations: COMPLETE requires three sensitivity results")
    if observation_status == "COMPLETE" and (total is None or total <= 0):
        raise ContractError("assessment observations: COMPLETE requires aoi_total_pixels greater than zero")
    if status == "COMPLETED" and observation_status != "COMPLETE":
        raise ContractError("assessment observations: COMPLETED requires COMPLETE observations")
    if status == "ABSTAINED" and observation_status == "COMPLETE" and reasons != ["EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND"]:
        raise ContractError("assessment observations: COMPLETE abstention is reserved for the operational indifference band")
    if status == "ABSTAINED" and observation_status not in {"PARTIAL", "COMPLETE"}:
        raise ContractError("assessment observations: ABSTAINED observations must be PARTIAL or controlled COMPLETE")
    if status in {"REFUSED", "ERROR"}:
        raise ContractError(f"assessment observations: {status} requires null observations")


def _validate_reason_semantics(assessment: dict[str, Any], registries: dict[str, Any]) -> None:
    reasons = assessment["reason_codes"]
    registry = registries["reason_codes"]
    order = {item["code"]: index for index, item in enumerate(registry["reason_codes"])}
    if reasons != sorted(reasons, key=order.__getitem__):
        raise ContractError("assessment: reason codes must follow canonical registry order")
    status = assessment["execution_status"]
    disposition = assessment["evidence_disposition"]
    checks = assessment["quality_checks"]
    present = set(reasons)
    for code in reasons:
        rule = registry["semantics"][code]
        incompatible = present.intersection(rule["incompatible_reason_codes"])
        if incompatible:
            raise ContractError(f"assessment reason {code}: incompatible reason codes {sorted(incompatible)}")
        if status not in rule["allowed_execution_statuses"]:
            raise ContractError(f"assessment reason {code}: execution status {status} is not allowed")
        if disposition not in rule["allowed_dispositions"]:
            raise ContractError(f"assessment reason {code}: disposition {disposition!r} is not allowed")
        for check, allowed_states in rule["quality_check_requirements"].items():
            if checks[check] not in allowed_states:
                raise ContractError(f"assessment reason {code}: quality check {check} must be one of {allowed_states}")
        if rule["human_review_required"] and assessment["human_review_required"] is not True:
            raise ContractError(f"assessment reason {code}: human review is required")


def _validate_complete_qualification(assessment: dict[str, Any], case: dict[str, Any]) -> None:
    observations = assessment["observations"]
    pre = _canonical_decimal(observations["pre_window_ndvi_median"], "pre_window_ndvi_median")
    post = _canonical_decimal(observations["post_window_ndvi_median"], "post_window_ndvi_median")
    delta = _canonical_decimal(observations["delta_ndvi"], "delta_ndvi")
    if post - pre != delta:
        raise ContractError("assessment: delta_ndvi does not equal canonical post minus pre")
    frozen_tau = _canonical_decimal(case["qualification_policy"]["indifference_band"]["tau"], "case primary tau")
    if _canonical_decimal(observations["primary_tau"], "primary_tau") != frozen_tau:
        raise ContractError("assessment: primary_tau does not match authoritative case policy")
    try:
        classifications = step2b_offline.classify_primary_and_sensitivities(delta)
    except step2b_offline.OfflineContractError as exc:
        raise ContractError(str(exc)) from exc
    primary = classifications["primary"]
    for field in ("execution_status", "evidence_disposition", "reason_codes"):
        if assessment[field] != primary[field]:
            raise ContractError(f"assessment: primary {field} does not match the frozen indifference-band rule")
    if primary["policy_id"] != case["qualification_policy"]["indifference_band"]["policy_id"]:
        raise ContractError("assessment: primary classification policy ID mismatch")
    if observations["sensitivity_results"] != classifications["sensitivities"]:
        raise ContractError("assessment: sensitivity results do not match frozen secondary tau values")


def validate_assessment(
    assessment: dict[str, Any],
    case: dict[str, Any] | None,
    schemas: dict[str, Any],
    registries: dict[str, Any],
) -> None:
    if case is None:
        raise ContractError("assessment: authoritative case context is required")
    reject_non_finite(assessment, "assessment")
    maps = _registry_maps(registries)
    reasons = assessment.get("reason_codes", [])
    unknown = sorted(set(reasons) - set(maps["reasons"]))
    if unknown:
        raise ContractError(f"assessment: unknown reason code {unknown}")
    if _duplicates(reasons):
        raise ContractError(f"assessment: duplicate reason code {_duplicates(reasons)}")
    if not assessment.get("provenance_manifest_ref"):
        raise ContractError("assessment: non-empty provenance reference is required")
    if assessment.get("must_not_claim") != FORBIDDEN_CODES:
        raise ContractError("assessment: must_not_claim must contain all forbidden codes once in canonical order")

    status = assessment.get("execution_status")
    observations = assessment.get("observations")
    if status in {"COMPLETED", "ABSTAINED", "REFUSED", "ERROR"} and (observations is None or isinstance(observations, dict)):
        _validate_observations(observations, status, reasons)
    complete_qualification = isinstance(observations, dict) and observations.get("observation_status") == "COMPLETE"
    if complete_qualification:
        _validate_complete_qualification(assessment, case)
    if status == "COMPLETED" and isinstance(assessment.get("statement_parameters"), dict):
        parameters = assessment["statement_parameters"]
        claim = case["claim_contract"]
        pre_schema_scope = {
            "project_id": case["project"]["project_id"],
            "analysis_boundary_role": claim["analysis_boundary_role"],
            "pre_window": _window_label(claim["pre_window_identity"]),
            "post_window": _window_label(claim["post_window_identity"]),
            "seasonal_rule_id": claim["seasonal_rule_id"],
            "aggregation": claim["aggregation"],
            "eligible_population": claim["eligible_population"],
            "indifference_policy_id": claim["primary_indifference_band_policy_id"],
            "qualification_policy_version": case["qualification_policy"]["policy_version"],
        }
        for field, expected in pre_schema_scope.items():
            if parameters.get(field) != expected:
                raise ContractError(f"assessment: statement {field} does not match authoritative case value {expected}")
    _schema_validate(assessment, schemas["assessment"], "assessment")
    status = assessment["execution_status"]
    _validate_reason_semantics(assessment, registries)
    reason_categories = {maps["reasons"][code]["category"] for code in reasons}
    if assessment["case_id"] != case.get("case_id"):
        raise ContractError("assessment: case identity does not match authoritative case")
    if status == "COMPLETED":
        observations = assessment["observations"]
        disposition = assessment["evidence_disposition"]
        expected_template = ACTIVE_TEMPLATE_BY_DISPOSITION[disposition]
        if assessment["statement_template_id"] != expected_template:
            raise ContractError("assessment: statement template does not match disposition")
        parameters = assessment["statement_parameters"]
        claim = case["claim_contract"]
        expected_scope = {
            "project_id": case["project"]["project_id"],
            "analysis_boundary_role": claim["analysis_boundary_role"],
            "pre_window": _window_label(claim["pre_window_identity"]),
            "post_window": _window_label(claim["post_window_identity"]),
            "seasonal_rule_id": claim["seasonal_rule_id"],
            "aggregation": claim["aggregation"],
            "eligible_population": claim["eligible_population"],
            "indifference_policy_id": claim["primary_indifference_band_policy_id"],
            "qualification_policy_version": case["qualification_policy"]["policy_version"],
        }
        for field, expected in expected_scope.items():
            if parameters.get(field) != expected:
                raise ContractError(f"assessment: statement {field} does not match authoritative case value {expected}")
        if assessment["qualification_policy_version"] != case["qualification_policy"]["policy_version"]:
            raise ContractError("assessment: qualification policy version does not match authoritative case")
        rendered = render_statement(assessment, registries)
        if assessment["supported_statement"] != rendered:
            raise ContractError("assessment: supported_statement is not the exact registered template render")
        if FORBIDDEN_CLAIM_LANGUAGE.search(assessment["supported_statement"]):
            raise ContractError("assessment: supported_statement contains forbidden ecological-duration language")
    elif status == "ABSTAINED":
        insufficiency = {"SPECIFICATION", "SOURCE_VERSION", "SPATIAL", "TEMPORAL", "OBSERVATION_QUALITY", "QUALIFICATION", "RESOURCE_LIMIT", "EVIDENCE_CONFLICT", "PROVENANCE"}
        if not reasons or not reason_categories.intersection(insufficiency):
            raise ContractError("assessment: ABSTAINED requires an insufficiency or evidence-conflict reason")
    elif status == "REFUSED":
        if "AUTHORITY" not in reason_categories:
            raise ContractError("assessment: REFUSED requires an AUTHORITY reason")
    elif status == "ERROR" and "SYSTEM" not in reason_categories:
        raise ContractError("assessment: ERROR requires a SYSTEM reason")


def _validate_stable_reference(value: str, context: str) -> None:
    if not value or any(character.isspace() for character in value):
        raise ContractError(f"{context}: stable absolute parameter_set_ref is required")
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "urn"}:
        raise ContractError(f"{context}: parameter_set_ref must be an absolute https URI or URN")
    if parsed.query or parsed.fragment:
        raise ContractError(f"{context}: parameter_set_ref cannot contain query parameters or fragments")
    if parsed.scheme == "https":
        _split_secure_uri(value, context)


def validate_manifest_structure(manifest: dict[str, Any], schemas: dict[str, Any], registries: dict[str, Any]) -> None:
    reject_non_finite(manifest, "manifest")
    maps = _registry_maps(registries)
    run_identity = manifest.get("run_identity", {})
    policy_hashes = [
        run_identity.get("approved_policy_sha256"),
        run_identity.get("calculated_policy_sha256_at_start"),
        run_identity.get("final_policy_sha256"),
    ]
    if len(set(policy_hashes)) != 1:
        raise ContractError("manifest: approved, start and final policy hashes must be identical")
    if run_identity.get("input_sha256_at_start") != run_identity.get("final_input_sha256"):
        raise ContractError("manifest: start and final input hashes must be identical")
    for record in manifest.get("source_records", []):
        if record.get("source_id") not in maps["sources"]:
            raise ContractError(f"manifest: unknown source {record.get('source_id')!r}")
        if record.get("canonical_uri"):
            context = f"manifest source {record['source_id']} canonical_uri"
            parsed = _split_secure_uri(record["canonical_uri"], context)
            if parsed.scheme.lower() != "https" or not parsed.hostname:
                raise ContractError(f"{context}: stable canonical identity must use https with a hostname")
            query_names = [name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)]
            credentials = sorted({name for name in query_names if _query_parameter_is_credential(name)}, key=str.lower)
            if credentials:
                raise ContractError(f"{context}: canonical identity contains signed or expiring credential parameters {credentials}")
            if query_names:
                raise ContractError(f"{context}: canonical identity contains unexpected query parameters {sorted(set(query_names))}")
        if record.get("retrieval_uri"):
            context = f"manifest source {record['source_id']} retrieval_uri"
            parsed = _split_secure_uri(record["retrieval_uri"], context)
            if parsed.scheme.lower() != "https" or not parsed.hostname:
                raise ContractError(f"{context}: retrieval URI must use https with a hostname")
    for record in manifest.get("radiometry_records", []):
        context = f"manifest radiometry {record.get('item_id')} {record.get('asset_key')}"
        canonical = record.get("canonical_asset_identity")
        if canonical:
            parsed = _split_secure_uri(canonical, f"{context} canonical_asset_identity")
            query_names = [name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)]
            if parsed.scheme.lower() != "https" or not parsed.hostname or query_names:
                raise ContractError(f"{context}: canonical asset identity must be stable https without query parameters")
        retrieval = record.get("retrieval_uri")
        if retrieval:
            parsed = _split_secure_uri(retrieval, f"{context} retrieval_uri")
            query_names = [name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)]
            credentials = [name for name in query_names if _query_parameter_is_credential(name)]
            if credentials:
                raise ContractError(f"{context}: credential-bearing retrieval URI must not be persisted")
        if record.get("cross_check") != "PASS":
            raise ContractError(f"{context}: only successfully cross-checked radiometry may be recorded as usable")
    solar_records = manifest.get("solar_geometry_records", [])
    identities = [(record.get("window"), record.get("item_id")) for record in solar_records]
    if len(set(identities)) != len(identities):
        raise ContractError("manifest: solar-geometry records must identify each discovered item once per window")
    for record in solar_records:
        value = record.get("mean_solar_zenith_angle")
        admissible = record.get("admissible")
        reason = record.get("exclusion_reason")
        if admissible and (value is None or value > step2b_offline.SOLAR_GEOMETRY_MAX_DEGREES or reason is not None or record.get("cross_check") != "PASS"):
            raise ContractError("manifest: admitted solar-geometry item violates the inclusive 70 degree rule")
        if not admissible and reason not in {"SOLAR_GEOMETRY_OUT_OF_RANGE", "SOLAR_GEOMETRY_METADATA_UNRESOLVED"}:
            raise ContractError("manifest: excluded solar-geometry item requires an exact exclusion reason")
        if reason == "SOLAR_GEOMETRY_OUT_OF_RANGE" and (value is None or value <= step2b_offline.SOLAR_GEOMETRY_MAX_DEGREES):
            raise ContractError("manifest: out-of-range solar-geometry reason requires a value above 70 degrees")
    pre_records = [record for record in solar_records if record.get("window") == "PRE"]
    post_records = [record for record in solar_records if record.get("window") == "POST"]
    expected_solar_summary = step2b_offline.solar_geometry_diagnostic(pre_records, post_records)
    if manifest.get("solar_geometry_summary") != expected_solar_summary:
        raise ContractError("manifest: solar-geometry summary does not match the item inventory")
    qualification_records = manifest.get("qualification_records", [])
    primary_records = [record for record in qualification_records if record.get("is_primary") is True]
    if qualification_records:
        if len(primary_records) != 1 or len(qualification_records) != 4:
            raise ContractError("manifest: qualification records require exactly one primary and three sensitivities")
        primary = primary_records[0]
        if primary.get("policy_id") != step2b_offline.PRIMARY_POLICY_ID or _canonical_decimal(primary.get("tau"), "manifest primary tau") != step2b_offline.PRIMARY_TAU:
            raise ContractError("manifest: primary qualification record does not use the frozen policy")
    for record in manifest.get("transformation_records", []):
        if record.get("transformation_id") not in maps["transformations"]:
            raise ContractError(f"manifest: unknown transformation {record.get('transformation_id')!r}")
        unknown_reasons = sorted(set(record.get("reason_codes", [])) - set(maps["reasons"]))
        if unknown_reasons:
            raise ContractError(f"manifest transformation {record.get('transformation_id')}: unknown reason code {unknown_reasons}")

    _schema_validate(manifest, schemas["provenance"], "manifest")
    source_ids = [item["source_id"] for item in manifest["source_records"]]
    if _duplicates(source_ids):
        raise ContractError(f"manifest: duplicate source IDs {_duplicates(source_ids)}")
    artifact_ids = [item["artifact_id"] for item in manifest["artifact_records"]]
    if _duplicates(artifact_ids):
        raise ContractError(f"manifest: duplicate artifact IDs {_duplicates(artifact_ids)}")
    artifact_set = set(artifact_ids)
    records = manifest["transformation_records"]
    sequences = [record["sequence"] for record in records]
    if sequences != list(range(1, len(records) + 1)):
        raise ContractError("manifest: transformation records must have contiguous sequence numbers")
    ids = [record["transformation_id"] for record in records]
    if ids != TRANSFORMATION_IDS:
        raise ContractError("manifest: transformation records must preserve the complete registered order")
    for record in records:
        _validate_stable_reference(record["parameter_set_ref"], f"manifest transformation {record['transformation_id']}")
        refs = record["input_artifact_refs"] + record["output_artifact_refs"]
        unresolved = sorted(set(refs) - artifact_set)
        if unresolved:
            raise ContractError(f"manifest transformation {record['transformation_id']}: unresolved artifact reference {unresolved}")
        if record["status"] == "COMPLETED":
            if not record["parameter_set_ref"] or not record["parameter_set_sha256"]:
                raise ContractError(f"manifest transformation {record['transformation_id']}: completed transformation requires parameter identity")
            if not record["input_artifact_refs"] or not record["output_artifact_refs"]:
                raise ContractError(f"manifest transformation {record['transformation_id']}: completed transformation requires input/output lineage")
        elif not record["reason_codes"]:
            raise ContractError(f"manifest transformation {record['transformation_id']}: {record['status']} requires a reason code")
    terminal_ref = manifest["terminal_result"]["assessment_artifact_ref"]
    if terminal_ref not in artifact_set:
        raise ContractError("manifest: terminal assessment artifact reference is unresolved")
    if manifest["terminal_result"]["execution_status"] == "COMPLETED":
        if manifest["terminal_result"]["reason_codes"]:
            raise ContractError("manifest: COMPLETED terminal result cannot contain reason codes")
        if not manifest["source_records"] or any(record["status"] != "COMPLETED" for record in records):
            raise ContractError("manifest: COMPLETED terminal result requires complete source and transformation provenance")
        if manifest["runtime_mode"] == "EXECUTION" and not solar_records:
            raise ContractError("manifest: completed execution requires per-item solar-geometry provenance")
    if manifest["runtime_mode"] == "EXECUTION":
        environment = manifest["software_environment"]
        if any("FIXTURE" in str(value).upper() for value in environment.values()):
            raise ContractError("manifest: fixture software placeholders are allowed only in SCHEMA_FIXTURE mode")


def validate_linked_result(
    case: dict[str, Any] | None,
    assessment: dict[str, Any] | None,
    manifest: dict[str, Any] | None,
    schemas: dict[str, Any],
    registries: dict[str, Any],
) -> None:
    if case is None or assessment is None or manifest is None:
        raise ContractError("linked result: authoritative case, assessment and manifest contexts are all required")
    validate_case(case, schemas, registries)
    validate_assessment(assessment, case, schemas, registries)
    validate_manifest_structure(manifest, schemas, registries)
    for field in ("run_id", "case_id"):
        if manifest[field] != assessment[field]:
            raise ContractError(f"linked result: assessment/manifest {field} mismatch")
    terminal = manifest["terminal_result"]
    if terminal["execution_status"] != assessment["execution_status"]:
        raise ContractError("linked result: assessment/manifest execution status mismatch")
    if terminal["reason_codes"] != assessment["reason_codes"]:
        raise ContractError("linked result: assessment/manifest reason codes mismatch")
    if terminal["assessment_sha256"] != canonical_sha256(assessment):
        raise ContractError("linked result: terminal assessment hash mismatch under CANONICAL_JSON_V1")
    if assessment["provenance_manifest_ref"] != manifest["manifest_id"]:
        raise ContractError("linked result: provenance_manifest_ref does not identify the linked manifest")
    artifact = next(item for item in manifest["artifact_records"] if item["artifact_id"] == terminal["assessment_artifact_ref"])
    if artifact["content_sha256"] != terminal["assessment_sha256"]:
        raise ContractError("linked result: assessment artifact hash does not match terminal hash")
    observations = assessment.get("observations")
    if isinstance(observations, dict) and observations.get("observation_status") == "COMPLETE":
        records = manifest["qualification_records"]
        primary = next((record for record in records if record["is_primary"]), None)
        if primary is None:
            raise ContractError("linked result: complete observations require a primary qualification provenance record")
        expected_primary = step2b_offline.classify_delta(observations["delta_ndvi"], observations["primary_tau"])
        for field in ("delta_ndvi", "tau", "execution_status", "evidence_disposition", "reason_codes", "comparison_semantics"):
            if primary[field] != expected_primary[field]:
                raise ContractError(f"linked result: primary qualification provenance {field} mismatch")
        sensitivity_records = [record for record in records if not record["is_primary"]]
        if [{key: record[key] for key in ("policy_id", "delta_ndvi", "tau", "execution_status", "evidence_disposition", "reason_codes", "comparison_semantics")} for record in sensitivity_records] != observations["sensitivity_results"]:
            raise ContractError("linked result: sensitivity provenance cannot diverge from assessment sensitivity results")

    maps = _registry_maps(registries)
    binding_map = {binding["source_id"]: binding for binding in case["evidence_policy"]["source_bindings"]}
    allowed = case["evidence_policy"]["allowed_source_ids"]
    for record in manifest["source_records"]:
        source_id = record["source_id"]
        if source_id not in allowed:
            raise ContractError(f"linked result: source {source_id} is not allowed by the authoritative case")
        binding = binding_map[source_id]
        if binding["binding_status"] != "FROZEN" or not binding["canonical_uri"]:
            raise ContractError(f"linked result: source {source_id} lacks a frozen canonical case binding")
        if record["canonical_uri"] != binding["canonical_uri"]:
            raise ContractError(f"linked result: source {source_id} canonical identity does not match authoritative case binding")
        policy = maps["sources"][source_id]["identity_policy"]
        _validate_evidence_uri(record["canonical_uri"], policy, "canonical", f"linked result source {source_id}", case["project"]["project_id"])
        if record["retrieval_uri"]:
            _validate_temporary_retrieval_uri(record["retrieval_uri"], policy, f"linked result source {source_id} retrieval_uri")
    if assessment["execution_status"] == "COMPLETED":
        if [record["source_id"] for record in manifest["source_records"]] != allowed:
            raise ContractError("linked result: COMPLETED assessment requires every case source in canonical order")
        if any(record["status"] != "COMPLETED" for record in manifest["transformation_records"]):
            raise ContractError("linked result: COMPLETED assessment requires complete provenance")
    if isinstance(observations, dict) and observations.get("observation_status") == "COMPLETE":
        if [record["source_id"] for record in manifest["source_records"]] != allowed:
            raise ContractError("linked result: complete measurements require every case source in canonical order")
        if any(record["status"] != "COMPLETED" for record in manifest["transformation_records"]):
            raise ContractError("linked result: complete measurements require complete upstream provenance")
        if manifest["runtime_mode"] == "EXECUTION":
            radiometry_records = manifest["radiometry_records"]
            if not radiometry_records:
                raise ContractError("linked result: execution measurements require per-item/per-band radiometry provenance")
            assets_by_item: dict[str, set[str]] = {}
            for record in radiometry_records:
                assets_by_item.setdefault(record["item_id"], set()).add(record["asset_key"])
            if any(asset_keys != {"B04", "B08"} for asset_keys in assets_by_item.values()):
                raise ContractError("linked result: every measured item requires separate B04 and B08 radiometry records")


def validate_fixture_pair(
    case: dict[str, Any],
    assessment: dict[str, Any],
    manifest: dict[str, Any],
    schemas: dict[str, Any],
    registries: dict[str, Any],
) -> None:
    validate_linked_result(case, assessment, manifest, schemas, registries)
    if manifest["runtime_mode"] != "SCHEMA_FIXTURE":
        raise ContractError("fixture pair: runtime_mode must be SCHEMA_FIXTURE")
    if assessment["case_id"] == "EOP101132-NDVI-001":
        raise ContractError("fixture pair: synthetic completed or terminal fixtures cannot be tied to the EOP case")


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


FIXTURE_PROJECT_ID = "SCHEMA-FIXTURE-PROJECT"
FIXTURE_CANONICAL_URIS = {
    "CER_ACCU_PROJECT_REGISTER": "https://cer.gov.au/markets/reports-and-data/accu-project-and-contract-register",
    "CER_PROJECT_RECORD": f"https://cer.gov.au/schemes/australian-carbon-credit-unit-scheme/accu-project-and-contract-register/project/{FIXTURE_PROJECT_ID}",
    "CER_PUBLISHED_CEA": f"https://cer.gov.au/fixtures/{FIXTURE_PROJECT_ID}/cea.geojson",
    "MSPC_SENTINEL2_L2A": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
}
FIXTURE_ASSESSMENT_SHA256 = {
    "COMPLETED": "cf5059530b94908e522b1978a95c8310c66081943e51852d001ea492678f18cb",
    "ABSTAINED": "61c49b86efa5dc8a5167776d3f635fa5139311c8c35c663b7f747f9b304636a5",
    "REFUSED": "433318cfb099197a78e9f4b3a20fcf9aaaa51f04da42296b7d2ed6e253d911bd",
    "ERROR": "deae4b4c5dc0962d7ad0581dd7294ee5c2b724f565e35c960f766c961ae3ac5a",
}


def _quality(default: str = "PASS", **overrides: str) -> dict[str, str]:
    keys = ["claim_contract", "evidence_allowlist", "transformation_allowlist", "spatial_scope", "temporal_scope", "observation_coverage", "evidence_consistency", "authority_scope", "provenance", "system_execution"]
    values = {key: default for key in keys}
    values.update(overrides)
    return values


def _make_fixture_case(status: str) -> dict[str, Any]:
    case_id = f"SCHEMA-FIXTURE-{status}-001"
    return {
        "schema_version": VERSION,
        "case_id": case_id,
        "runtime_ready": True,
        "project": {
            "project_id": FIXTURE_PROJECT_ID,
            "project_name": "Schema-only contract fixture",
            "registry_url": FIXTURE_CANONICAL_URIS["CER_PROJECT_RECORD"],
            "declared_model_start_date": "2000-02-01",
            "jurisdiction": "Synthetic",
            "state": "Synthetic",
        },
        "claim_contract": {
            "claim_type": "OBSERVATIONAL_COMPARISON",
            "observable": "AOI_SEASONAL_NDVI",
            "claim_text": "Schema-only fixture statement; not an empirical environmental result.",
            "analysis_boundary_role": "CEA",
            "pre_window_identity": {"start_date": "2000-01-01", "end_date": "2000-01-31"},
            "post_window_identity": {"start_date": "2001-01-01", "end_date": "2001-01-31"},
            "seasonal_rule_id": "SCHEMA_FIXTURE_MATCHED_SEASON",
            "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
            "aggregation": "AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI",
            "eligible_population": "Schema-fixture joint eligible pixels",
            "primary_indifference_band_policy_id": step2b_offline.PRIMARY_POLICY_ID,
            "primary_tau": 0.03,
            "authority_ceiling": "OBSERVATIONAL_CONSISTENCY_ONLY",
            "forbidden_inferences": copy.deepcopy(FORBIDDEN_CODES),
        },
        "evidence_policy": {
            "registry_version": VERSION,
            "allowed_source_ids": copy.deepcopy(SOURCE_IDS),
            "source_bindings": [
                {
                    "source_id": source_id,
                    "canonical_uri": uri,
                    "discovery_uri": None,
                    "retrieval_uri": None,
                    "binding_status": "FROZEN",
                }
                for source_id, uri in FIXTURE_CANONICAL_URIS.items()
            ],
        },
        "transformation_policy": {
            "registry_version": VERSION,
            "required_transformation_ids": copy.deepcopy(TRANSFORMATION_IDS),
        },
        "spatial_scope": {
            "status": "FROZEN",
            "boundary_source_id": "CER_PUBLISHED_CEA",
            "boundary_artifact_uri": FIXTURE_CANONICAL_URIS["CER_PUBLISHED_CEA"],
            "boundary_sha256": _sha("schema-fixture-boundary"),
        },
        "temporal_scope": {
            "status": "FROZEN",
            "pre_window": {"start_date": "2000-01-01", "end_date": "2000-01-31"},
            "post_window": {"start_date": "2001-01-01", "end_date": "2001-01-31"},
            "seasonal_rule": {"fixture_contract": "SCHEMA_ONLY"},
        },
        "qualification_policy": {
            "policy_version": VERSION,
            "proposed_execution_mode": "QUALIFICATION",
            "approval_status": "APPROVED",
            "indifference_band": {
                "policy_id": step2b_offline.PRIMARY_POLICY_ID,
                "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
                "tau": 0.03,
                "unit": "NDVI",
                "lower_boundary_inclusive": True,
                "upper_boundary_inclusive": True,
                "epistemic_status": "DEMO_OPERATIONAL_RULE",
                "ecological_standard": False,
                "regulatory_standard": False,
                "instrument_detection_limit": False,
                "assurance_standard": False,
            },
            "sensitivity_tau_values": [0.01, 0.02, 0.05],
            "scl_rule": {"fixture_contract": "SCHEMA_ONLY"},
            "observation_coverage_rule": {"fixture_contract": "SCHEMA_ONLY"},
        },
        "pending_step_2": [],
    }


def _base_assessment(status: str) -> dict[str, Any]:
    run_id = f"SCHEMA-FIXTURE-RUN-{status}"
    manifest_id = f"urn:fixture:manifest:{status.lower()}"
    return {
        "schema_version": VERSION,
        "case_id": f"SCHEMA-FIXTURE-{status}-001",
        "run_id": run_id,
        "execution_status": status,
        "evidence_disposition": None,
        "reason_codes": [],
        "quality_checks": _quality(),
        "observations": None,
        "statement_template_id": None,
        "supported_statement": None,
        "must_not_claim": copy.deepcopy(FORBIDDEN_CODES),
        "human_review_required": True,
        "provenance_manifest_ref": manifest_id,
        "qualification_policy_version": VERSION,
        "statement_parameters": None,
    }


def _make_assessment(status: str, registries: dict[str, Any]) -> dict[str, Any]:
    assessment = _base_assessment(status)
    if status == "COMPLETED":
        assessment.update({
            "evidence_disposition": "CORROBORATING",
            "quality_checks": _quality(),
            "observations": {
                "observation_status": "COMPLETE",
                "aoi_total_pixels": 100,
                "aoi_valid_pixels": 50,
                "aoi_valid_fraction": 0.5,
                "pre_window_ndvi_median": -0.5,
                "post_window_ndvi_median": 0.5,
                "delta_ndvi": 1.0,
                "primary_tau": 0.03,
                "delta_distribution": {"count": 5, "q05": 0.8, "q25": 0.9, "median": 1.0, "q75": 1.1, "q95": 1.2, "iqr": 0.2, "mad": 0.1},
                "sensitivity_results": step2b_offline.classify_primary_and_sensitivities(1.0)["sensitivities"],
            },
            "statement_template_id": ACTIVE_TEMPLATE_BY_DISPOSITION["CORROBORATING"],
            "human_review_required": False,
            "statement_parameters": {
                "project_id": FIXTURE_PROJECT_ID,
                "analysis_boundary_role": "CEA",
                "pre_window": "2000-01-01/2000-01-31",
                "post_window": "2001-01-01/2001-01-31",
                "seasonal_rule_id": "SCHEMA_FIXTURE_MATCHED_SEASON",
                "aggregation": "AOI median of per-pixel temporal-median Sentinel-2 L2A NDVI",
                "eligible_population": "Schema-fixture joint eligible pixels",
                "pre_value": "-0.5",
                "post_value": "0.5",
                "delta_value": "1.0",
                "primary_tau": "0.03",
                "indifference_policy_id": step2b_offline.PRIMARY_POLICY_ID,
                "qualification_policy_version": VERSION,
            },
        })
        assessment["supported_statement"] = render_statement(assessment, registries)
    elif status == "ABSTAINED":
        assessment.update({
            "evidence_disposition": "INCONCLUSIVE",
            "reason_codes": ["TEMPORAL_SCOPE_NOT_FROZEN"],
            "quality_checks": _quality(spatial_scope="NOT_RUN", temporal_scope="FAIL", observation_coverage="NOT_RUN", evidence_consistency="NOT_RUN"),
        })
    elif status == "REFUSED":
        assessment.update({
            "reason_codes": ["AUTHORITY_SCOPE_EXCEEDED"],
            "quality_checks": _quality(spatial_scope="NOT_RUN", temporal_scope="NOT_RUN", observation_coverage="NOT_RUN", evidence_consistency="NOT_RUN", authority_scope="FAIL"),
        })
    elif status == "ERROR":
        assessment.update({
            "reason_codes": ["DETERMINISTIC_PROCESSING_ERROR"],
            "quality_checks": _quality(spatial_scope="NOT_RUN", temporal_scope="NOT_RUN", observation_coverage="NOT_RUN", evidence_consistency="NOT_RUN", system_execution="FAIL"),
        })
    return assessment


def _make_manifest(assessment: dict[str, Any]) -> dict[str, Any]:
    status = assessment["execution_status"]
    reason_codes = assessment["reason_codes"]
    assessment_sha256 = FIXTURE_ASSESSMENT_SHA256[status]
    initial_id = f"urn:fixture:artifact:{status.lower()}:input"
    assessment_id = f"urn:fixture:artifact:{status.lower()}:assessment"
    artifacts = [{
        "artifact_id": initial_id,
        "artifact_type": "SCHEMA_FIXTURE_INPUT",
        "content_sha256": _sha(initial_id),
        "produced_by": "CER_ACCU_PROJECT_REGISTER",
        "media_type": "application/json",
    }]
    transformations = []
    previous_output = initial_id
    stop_after = 12 if status == "COMPLETED" else 2
    fail_at = 3 if status == "ERROR" else None
    timestamp = "2000-01-01T00:00:00Z"
    for sequence, transformation_id in enumerate(TRANSFORMATION_IDS, 1):
        is_emitter = sequence == 12
        if sequence <= stop_after or is_emitter:
            record_status = "COMPLETED"
        elif sequence == fail_at:
            record_status = "FAILED"
        else:
            record_status = "SKIPPED"
        input_refs: list[str] = []
        output_refs: list[str] = []
        if record_status == "COMPLETED":
            input_refs = [previous_output]
            output_id = assessment_id if is_emitter else f"urn:fixture:artifact:{status.lower()}:stage-{sequence}"
            output_refs = [output_id]
            artifacts.append({
                "artifact_id": output_id,
                "artifact_type": "SCHEMA_FIXTURE_ASSESSMENT" if is_emitter else "SCHEMA_FIXTURE_INTERMEDIATE",
                "content_sha256": assessment_sha256 if is_emitter else _sha(output_id),
                "produced_by": transformation_id,
                "media_type": "application/json",
            })
            previous_output = output_id
        elif record_status == "FAILED":
            input_refs = [previous_output]
        record_reasons = [] if record_status == "COMPLETED" else reason_codes
        transformations.append({
            "sequence": sequence,
            "transformation_id": transformation_id,
            "implementation_version": "SCHEMA-FIXTURE-NOT-EXECUTED" if record_status != "COMPLETED" else VERSION,
            "parameter_set_ref": f"urn:fixture:parameters:{sequence}",
            "parameter_set_sha256": _sha(f"fixture-parameters-{sequence}"),
            "input_artifact_refs": input_refs,
            "output_artifact_refs": output_refs,
            "status": record_status,
            "started_at_utc": timestamp,
            "finished_at_utc": timestamp,
            "reason_codes": record_reasons,
        })
    qualification_records: list[dict[str, Any]] = []
    observations = assessment.get("observations")
    if isinstance(observations, dict) and observations.get("observation_status") == "COMPLETE":
        classified = step2b_offline.classify_primary_and_sensitivities(observations["delta_ndvi"])
        qualification_records.append({
            "policy_id": classified["primary"]["policy_id"],
            "is_primary": True,
            "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
            **{key: classified["primary"][key] for key in ("delta_ndvi", "tau", "comparison_semantics", "execution_status", "evidence_disposition", "reason_codes")},
        })
        qualification_records.extend({
            "is_primary": False,
            "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
            "delta_ndvi": observations["delta_ndvi"],
            **record,
        } for record in classified["sensitivities"])
    return {
        "schema_version": VERSION,
        "manifest_id": assessment["provenance_manifest_ref"],
        "run_id": assessment["run_id"],
        "case_id": assessment["case_id"],
        "runtime_mode": "SCHEMA_FIXTURE",
        "created_at_utc": timestamp,
        "run_identity": {
            "approved_policy_sha256": _sha(f"fixture-policy:{status}"),
            "calculated_policy_sha256_at_start": _sha(f"fixture-policy:{status}"),
            "final_policy_sha256": _sha(f"fixture-policy:{status}"),
            "input_sha256_at_start": _sha(f"fixture-input:{status}"),
            "final_input_sha256": _sha(f"fixture-input:{status}"),
        },
        "source_records": [
            {
                "source_id": source_id,
                "canonical_uri": uri,
                "retrieval_uri": None,
                "publisher": "SCHEMA FIXTURE - NOT EMPIRICAL",
                "retrieved_at_utc": timestamp,
                "version_identifier": "SCHEMA-FIXTURE-VERSION",
                "content_sha256": _sha(f"schema-fixture-source:{source_id}"),
                "source_asset_ids": [f"SCHEMA-FIXTURE-ASSET:{source_id}"],
            }
            for source_id, uri in FIXTURE_CANONICAL_URIS.items()
        ],
        "processing_representation_records": [],
        "acquisition_group_records": [],
        "solar_geometry_records": [],
        "solar_geometry_summary": step2b_offline.solar_geometry_diagnostic([], []),
        "radiometry_records": [],
        "qualification_records": qualification_records,
        "artifact_records": artifacts,
        "transformation_records": transformations,
        "policy_versions": {
            "evidence_sources": VERSION,
            "transformations": VERSION,
            "statement_templates": VERSION,
            "forbidden_inferences": VERSION,
            "reason_codes": VERSION,
            "qualification_policy": VERSION,
        },
        "software_environment": {
            "code_revision": "SCHEMA-FIXTURE-NOT-A-REVISION",
            "python_version": "SCHEMA-FIXTURE-PYTHON",
            "package_lock_sha256": "SCHEMA-FIXTURE-NO-LOCKFILE",
            "packages": {"jsonschema": "SCHEMA-FIXTURE", "pytest": "SCHEMA-FIXTURE"},
        },
        "terminal_result": {
            "assessment_artifact_ref": assessment_id,
            "assessment_sha256": assessment_sha256,
            "execution_status": status,
            "reason_codes": copy.deepcopy(reason_codes),
            "canonicalisation_id": "CANONICAL_JSON_V1",
        },
    }


def build_fixture_pairs(registries: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    pairs = {}
    for status in ("COMPLETED", "ABSTAINED", "REFUSED", "ERROR"):
        assessment = _make_assessment(status, registries)
        pairs[status] = (assessment, _make_manifest(assessment))
    return pairs


def build_fixture_cases() -> dict[str, dict[str, Any]]:
    return {status: _make_fixture_case(status) for status in ("COMPLETED", "ABSTAINED", "REFUSED", "ERROR")}


def validate_all() -> dict[str, Any]:
    contracts = load_contracts()
    if hashlib.sha256(V3_POLICY_FILE.read_bytes()).hexdigest() != V3_POLICY_SHA256:
        raise ContractError("immutable V3 policy hash mismatch")
    validate_schemas(contracts["schemas"])
    validate_registries(contracts["registries"])
    validate_case(contracts["case"], contracts["schemas"], contracts["registries"])
    validate_policy_proposal(contracts["policy"], contracts["case"])
    if contracts["case"]["case_id"] != "EOP101132-NDVI-001":
        raise ContractError("EOP101132 case: unexpected case_id")
    if contracts["case"]["runtime_ready"] is not False or contracts["case"]["pending_step_2"] != PENDING_STEP_2:
        raise ContractError("EOP101132 case: must remain specification-only with the exact Step 2 pending list")
    fixtures = build_fixture_pairs(contracts["registries"])
    fixture_cases = build_fixture_cases()
    for status, (assessment, manifest) in fixtures.items():
        try:
            validate_fixture_pair(fixture_cases[status], assessment, manifest, contracts["schemas"], contracts["registries"])
        except ContractError as exc:
            raise ContractError(f"{status} fixture invalid: {exc}") from exc
    return {"contracts": contracts, "fixture_cases": fixture_cases, "fixtures": fixtures}


def main() -> int:
    try:
        result = validate_all()
    except ContractError as exc:
        print(f"Step 1 validation failed: {exc}", file=sys.stderr)
        return 1
    case = result["contracts"]["case"]
    statuses = ", ".join(result["fixtures"])
    pending = ", ".join(case["pending_step_2"])
    print(f"Step 1 contracts valid (version {VERSION}; fixtures: {statuses}).")
    print(f"EOP101132 remains specification-only; pending Step 2: {pending}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
