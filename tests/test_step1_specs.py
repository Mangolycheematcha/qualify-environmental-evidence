from __future__ import annotations

import copy
import hashlib
import json
import re

import pytest

from scripts import validate_step1_specs as step1


@pytest.fixture(scope="module")
def contracts():
    loaded = step1.load_contracts()
    step1.validate_registries(loaded["registries"])
    return loaded


@pytest.fixture
def fixtures(contracts):
    return copy.deepcopy(step1.build_fixture_pairs(contracts["registries"]))


@pytest.fixture
def fixture_cases():
    return copy.deepcopy(step1.build_fixture_cases())


def rejected(expected, operation):
    with pytest.raises(step1.ContractError, match=expected):
        operation()


def independent_canonical_sha256(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_case(case, contracts):
    step1.validate_case(case, contracts["schemas"], contracts["registries"])


def fixture_case_for(assessment):
    return step1.build_fixture_cases()[assessment["execution_status"]]


def validate_assessment(assessment, contracts, case=None):
    step1.validate_assessment(assessment, case or fixture_case_for(assessment), contracts["schemas"], contracts["registries"])


def validate_manifest(manifest, contracts):
    step1.validate_manifest_structure(manifest, contracts["schemas"], contracts["registries"])


def validate_pair(pair, contracts):
    assessment, manifest = pair
    step1.validate_fixture_pair(
        fixture_case_for(assessment), assessment, manifest, contracts["schemas"], contracts["registries"]
    )


def test_all_registries_are_unique_versioned_and_complete(contracts):
    step1.validate_registries(contracts["registries"])
    assert {registry["registry_version"] for registry in contracts["registries"].values()} == {step1.VERSION}


def test_all_schemas_are_valid_draft_2020_12(contracts):
    step1.validate_schemas(contracts["schemas"])


def test_eop101132_case_validates_in_specification_mode(contracts):
    validate_case(contracts["case"], contracts)
    assert contracts["case"]["runtime_ready"] is False
    assert contracts["case"]["pending_step_2"] == step1.PENDING_STEP_2


def test_transformation_sequence_is_exact(contracts):
    registered = [item["transformation_id"] for item in contracts["registries"]["transformations"]["transformations"]]
    assert registered == step1.TRANSFORMATION_IDS
    assert [item["sequence"] for item in contracts["registries"]["transformations"]["transformations"]] == list(range(1, 13))


@pytest.mark.parametrize("status", ["COMPLETED", "ABSTAINED", "REFUSED", "ERROR"])
def test_valid_linked_fixture_for_every_status(status, fixtures, contracts):
    validate_pair(fixtures[status], contracts)
    assessment, manifest = fixtures[status]
    assert manifest["runtime_mode"] == "SCHEMA_FIXTURE"
    assert assessment["case_id"].startswith("SCHEMA-FIXTURE-")


def test_fixture_provenance_artifacts_and_hashes_are_consistent(fixtures, contracts):
    for assessment, manifest in fixtures.values():
        validate_pair((assessment, manifest), contracts)
        terminal = manifest["terminal_result"]
        assert terminal["assessment_sha256"] == step1.canonical_sha256(assessment)
        artifact_ids = {item["artifact_id"] for item in manifest["artifact_records"]}
        assert terminal["assessment_artifact_ref"] in artifact_ids


def test_rejects_unknown_evidence_source(contracts):
    case = copy.deepcopy(contracts["case"])
    case["evidence_policy"]["allowed_source_ids"].append("UNKNOWN_SOURCE")
    rejected("unknown evidence source", lambda: validate_case(case, contracts))


def test_rejects_duplicate_evidence_source(contracts):
    case = copy.deepcopy(contracts["case"])
    case["evidence_policy"]["allowed_source_ids"].append("CER_PROJECT_RECORD")
    rejected("duplicate evidence source", lambda: validate_case(case, contracts))


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra"])
def test_rejects_invalid_source_binding_cardinality(mutation, contracts):
    case = copy.deepcopy(contracts["case"])
    bindings = case["evidence_policy"]["source_bindings"]
    if mutation == "missing":
        bindings.pop()
    elif mutation == "duplicate":
        bindings.append(copy.deepcopy(bindings[0]))
    else:
        bindings.append({"source_id": "UNKNOWN_SOURCE", "canonical_uri": "urn:fixture:extra", "discovery_uri": None, "binding_status": "FROZEN"})
    rejected("source binding", lambda: validate_case(case, contracts))


def test_rejects_frozen_binding_without_canonical_uri(contracts):
    case = copy.deepcopy(contracts["case"])
    case["evidence_policy"]["source_bindings"][0]["canonical_uri"] = None
    rejected("frozen binding requires canonical_uri", lambda: validate_case(case, contracts))


@pytest.mark.parametrize("mutation", ["missing_discovery", "fabricated_canonical"])
def test_rejects_invalid_pending_binding(mutation, contracts):
    case = copy.deepcopy(contracts["case"])
    binding = case["evidence_policy"]["source_bindings"][2]
    if mutation == "missing_discovery":
        binding["discovery_uri"] = None
    else:
        binding["canonical_uri"] = "https://example.invalid/fabricated-boundary.geojson"
    rejected("pending binding", lambda: validate_case(case, contracts))


def test_rejects_unallowlisted_pending_discovery_uri(contracts):
    case = copy.deepcopy(contracts["case"])
    case["evidence_policy"]["source_bindings"][2]["discovery_uri"] = "https://example.invalid/discovery"
    rejected("exact allowlisted host", lambda: validate_case(case, contracts))


def test_rejects_unknown_transformation(contracts):
    case = copy.deepcopy(contracts["case"])
    case["transformation_policy"]["required_transformation_ids"][4] = "UNKNOWN_TRANSFORMATION"
    rejected("unknown transformation", lambda: validate_case(case, contracts))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [("reordered", "sequence invalid"), ("deleted", "sequence invalid"), ("duplicated", "duplicate transformation")],
)
def test_rejects_invalid_transformation_sequence(mutation, expected, contracts):
    case = copy.deepcopy(contracts["case"])
    ids = case["transformation_policy"]["required_transformation_ids"]
    if mutation == "reordered":
        ids[2], ids[3] = ids[3], ids[2]
    elif mutation == "deleted":
        ids.pop(4)
    else:
        ids[4] = ids[3]
    rejected(expected, lambda: validate_case(case, contracts))


def test_rejects_missing_required_forbidden_inference(contracts):
    case = copy.deepcopy(contracts["case"])
    case["claim_contract"]["forbidden_inferences"].pop()
    rejected("all forbidden inference codes", lambda: validate_case(case, contracts))


@pytest.mark.parametrize("kind", ["unknown", "duplicate"])
def test_rejects_unknown_or_duplicate_assessment_reason_code(kind, fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    if kind == "unknown":
        assessment["reason_codes"] = ["UNKNOWN_REASON"]
    else:
        assessment["reason_codes"].append(assessment["reason_codes"][0])
    rejected(f"{kind} reason code", lambda: validate_assessment(assessment, contracts))


def test_rejects_runtime_ready_with_pending_step2(contracts):
    case = copy.deepcopy(contracts["case"])
    case["runtime_ready"] = True
    rejected("runtime_ready cannot be true", lambda: validate_case(case, contracts))


def test_rejects_abstained_with_corroborating_disposition(fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["evidence_disposition"] = "CORROBORATING"
    rejected("INCONCLUSIVE", lambda: validate_assessment(assessment, contracts))


def test_rejects_refused_with_non_null_disposition(fixtures, contracts):
    assessment, _ = fixtures["REFUSED"]
    assessment["evidence_disposition"] = "INCONCLUSIVE"
    rejected("evidence_disposition.*null", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("mutation", ["inconclusive", "null_statement"])
def test_rejects_invalid_completed_terminal_fields(mutation, fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    if mutation == "inconclusive":
        assessment["evidence_disposition"] = "INCONCLUSIVE"
        expected = "primary evidence_disposition"
    else:
        assessment["supported_statement"] = None
        expected = "string"
    rejected(expected, lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("mutation", ["incomplete_observations", "failed_quality", "mismatched_template"])
def test_rejects_incomplete_or_mismatched_completed_assessment(mutation, fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    if mutation == "incomplete_observations":
        assessment["observations"]["post_window_ndvi_median"] = None
        expected = "COMPLETE requires all measurement fields"
    elif mutation == "failed_quality":
        assessment["quality_checks"]["observation_coverage"] = "FAIL"
        expected = "PASS"
    else:
        assessment["statement_template_id"] = step1.ACTIVE_TEMPLATE_BY_DISPOSITION["CONTRADICTORY"]
        expected = "template does not match disposition"
    rejected(expected, lambda: validate_assessment(assessment, contracts))


def test_rejects_completed_pixel_count_inconsistency(fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    assessment["observations"]["aoi_valid_pixels"] = 101
    rejected("aoi_valid_pixels", lambda: validate_assessment(assessment, contracts))


def test_rejects_completed_fraction_outside_tolerance(fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    assessment["observations"]["aoi_valid_fraction"] = 0.500000000002
    rejected("pixel arithmetic", lambda: validate_assessment(assessment, contracts))


def test_rejects_disposition_ndvi_mismatch(fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    assessment["evidence_disposition"] = "CONTRADICTORY"
    assessment["statement_template_id"] = step1.ACTIVE_TEMPLATE_BY_DISPOSITION["CONTRADICTORY"]
    assessment["supported_statement"] = step1.render_statement(assessment, contracts["registries"])
    rejected("primary evidence_disposition", lambda: validate_assessment(assessment, contracts))


def test_rejects_non_exact_completed_statement(fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    assessment["supported_statement"] += " Extra interpretation."
    rejected("exact registered template render", lambda: validate_assessment(assessment, contracts))


def test_rejects_abstained_statement_template(fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["statement_template_id"] = step1.TEMPLATE_IDS[0]
    rejected("statement_template_id.*null", lambda: validate_assessment(assessment, contracts))


def test_rejects_error_with_evidence_disposition(fixtures, contracts):
    assessment, _ = fixtures["ERROR"]
    assessment["evidence_disposition"] = "INCONCLUSIVE"
    rejected("evidence_disposition.*null", lambda: validate_assessment(assessment, contracts))


def test_rejects_missing_provenance_reference(fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["provenance_manifest_ref"] = ""
    rejected("non-empty provenance reference", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("record_type", ["source", "transformation"])
def test_rejects_unknown_manifest_registry_member(record_type, fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    if record_type == "source":
        manifest["source_records"][0]["source_id"] = "UNKNOWN_SOURCE"
        expected = "unknown source"
    else:
        manifest["transformation_records"][0]["transformation_id"] = "UNKNOWN_TRANSFORMATION"
        expected = "unknown transformation"
    rejected(expected, lambda: validate_manifest(manifest, contracts))


def test_rejects_unresolved_artifact_reference(fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    manifest["transformation_records"][4]["input_artifact_refs"] = ["urn:fixture:artifact:missing"]
    rejected("unresolved artifact reference", lambda: validate_manifest(manifest, contracts))


def test_rejects_non_contiguous_transformation_records(fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    manifest["transformation_records"][3]["sequence"] = 99
    rejected("contiguous sequence", lambda: validate_manifest(manifest, contracts))


@pytest.mark.parametrize("missing", ["parameter", "input", "output"])
def test_rejects_completed_transformation_without_identity_or_lineage(missing, fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    record = manifest["transformation_records"][4]
    if missing == "parameter":
        record["parameter_set_ref"] = "relative/parameters"
        expected = "absolute https URI or URN"
    elif missing == "input":
        record["input_artifact_refs"] = []
        expected = "input/output lineage"
    else:
        record["output_artifact_refs"] = []
        expected = "input/output lineage"
    rejected(expected, lambda: validate_manifest(manifest, contracts))


def test_rejects_completed_assessment_with_incomplete_provenance(fixtures, contracts):
    assessment, manifest = fixtures["COMPLETED"]
    record = manifest["transformation_records"][5]
    record["status"] = "SKIPPED"
    record["input_artifact_refs"] = []
    record["output_artifact_refs"] = []
    record["reason_codes"] = ["SOURCE_UNAVAILABLE"]
    rejected("complete source and transformation provenance", lambda: validate_pair((assessment, manifest), contracts))


@pytest.mark.parametrize("mismatch", ["run_id", "case_id", "status", "reasons", "hash"])
def test_rejects_assessment_manifest_relationship_mismatch(mismatch, fixtures, contracts):
    assessment, manifest = fixtures["ABSTAINED"]
    if mismatch == "run_id":
        manifest["run_id"] = "SCHEMA-FIXTURE-RUN-DIFFERENT"
        expected = "run_id mismatch"
    elif mismatch == "case_id":
        manifest["case_id"] = "SCHEMA-FIXTURE-CASE-DIFFERENT"
        expected = "case_id mismatch"
    elif mismatch == "status":
        manifest["terminal_result"]["execution_status"] = "ERROR"
        expected = "execution status mismatch"
    elif mismatch == "reasons":
        manifest["terminal_result"]["reason_codes"] = ["SOURCE_UNAVAILABLE"]
        expected = "reason codes mismatch"
    else:
        manifest["terminal_result"]["assessment_sha256"] = "0" * 64
        expected = "assessment hash mismatch"
    rejected(expected, lambda: validate_pair((assessment, manifest), contracts))


@pytest.mark.parametrize("parameter", ["sig", "token", "se", "sp", "sv"])
def test_rejects_signed_or_expiring_canonical_uri(parameter, fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    manifest["source_records"][0]["canonical_uri"] = f"https://example.invalid/source?{parameter}=fixture-secret"
    rejected("signed or expiring credential", lambda: validate_manifest(manifest, contracts))


@pytest.mark.parametrize("field", ["reasoning_trace", "chain_of_thought"])
def test_rejects_unexpected_reasoning_property(field, fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment[field] = "must never be stored"
    rejected("Additional properties", lambda: validate_assessment(assessment, contracts))


def test_registry_rejects_duplicate_source(contracts):
    registries = copy.deepcopy(contracts["registries"])
    registries["evidence_sources"]["sources"].append(copy.deepcopy(registries["evidence_sources"]["sources"][0]))
    rejected("duplicate evidence source", lambda: step1.validate_registries(registries))


def test_registry_rejects_duplicate_reason_code(contracts):
    registries = copy.deepcopy(contracts["registries"])
    registries["reason_codes"]["reason_codes"].append(copy.deepcopy(registries["reason_codes"]["reason_codes"][0]))
    rejected("duplicate reason code", lambda: step1.validate_registries(registries))


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_json_loader_rejects_non_standard_numeric_constants(constant, tmp_path):
    path = tmp_path / "non-finite.json"
    path.write_text(f'{{"value": {constant}}}', encoding="utf-8")
    rejected("non-standard JSON numeric constant", lambda: step1.load_json(path))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_programmatic_contract_objects_reject_nested_non_finite_numbers(value, contracts):
    case = copy.deepcopy(contracts["case"])
    case["qualification_policy"]["scl_rule"] = {"nested": [value]}
    rejected("non-finite number", lambda: validate_case(case, contracts))


def test_canonical_json_golden_vectors_are_byte_exact_and_type_sensitive():
    nested = {"z": [3, {"\u00e9": "\u96ea"}], "a": {"b": 2, "a": 1}}
    expected = '{"a":{"a":1,"b":2},"z":[3,{"\u00e9":"\u96ea"}]}'.encode("utf-8")
    assert step1.canonical_json_bytes(nested) == expected
    assert step1.canonical_sha256(nested) == "cbf7bc415d0584a204e08a5013fcadd055013d48875c1872ba17b652573682ab"
    assert step1.canonical_json_bytes(1) == b"1"
    assert step1.canonical_json_bytes(1.0) == b"1.0"
    assert step1.canonical_sha256(1) == "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"
    assert step1.canonical_sha256(1.0) == "d0ff5974b6aa52cf562bea5921840c032a860a91a3512f7fe8f768f6bbe005f6"


def test_canonical_json_rejects_non_finite_programmatic_values():
    rejected("non-finite number", lambda: step1.canonical_json_bytes({"nested": [float("nan")]}))


def test_fixture_hash_oracles_are_static_and_detect_canonicalizer_tampering(fixtures, contracts, monkeypatch):
    assessment, manifest = fixtures["COMPLETED"]
    assert manifest["terminal_result"]["assessment_sha256"] == step1.FIXTURE_ASSESSMENT_SHA256["COMPLETED"]
    independent = independent_canonical_sha256(assessment)
    assert independent == step1.FIXTURE_ASSESSMENT_SHA256["COMPLETED"]
    monkeypatch.setattr(step1, "canonical_json_bytes", lambda _value: b"fixed-canonical-bytes")
    rejected("assessment hash mismatch", lambda: validate_pair((assessment, manifest), contracts))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("evil_suffix", "exact allowlisted host"),
        ("wrong_scheme", "exact scheme"),
        ("userinfo", "userinfo is prohibited"),
        ("fragment", "fragments are prohibited"),
        ("port", "unexpected URI port"),
        ("wrong_collection", "canonical path must equal"),
        ("wrong_project", "canonical project path must equal"),
    ],
)
def test_machine_source_identity_rejects_uri_confusion(mutation, expected, fixture_cases, contracts):
    case = fixture_cases["COMPLETED"]
    binding = case["evidence_policy"]["source_bindings"][3]
    if mutation == "evil_suffix":
        binding["canonical_uri"] = "https://planetarycomputer.microsoft.com.evil.example/dataset/sentinel-2-l2a"
    elif mutation == "wrong_scheme":
        binding["canonical_uri"] = "http://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"
    elif mutation == "userinfo":
        binding["canonical_uri"] = "https://user@planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"
    elif mutation == "fragment":
        binding["canonical_uri"] += "#asset"
    elif mutation == "port":
        binding["canonical_uri"] = "https://planetarycomputer.microsoft.com:443/dataset/sentinel-2-l2a"
    elif mutation == "wrong_collection":
        binding["canonical_uri"] = "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l1c"
    else:
        binding = case["evidence_policy"]["source_bindings"][1]
        binding["canonical_uri"] = binding["canonical_uri"].replace(step1.FIXTURE_PROJECT_ID, "WRONG-PROJECT")
    rejected(expected, lambda: validate_case(case, contracts))


@pytest.mark.parametrize("query", ["sig=azure-sas", "X-Amz-Credential=temp&X-Amz-Signature=secret"])
def test_canonical_identity_rejects_azure_and_aws_signed_parameters(query, fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    manifest["source_records"][3]["canonical_uri"] += f"?{query}"
    rejected("signed or expiring credential", lambda: validate_manifest(manifest, contracts))


def test_signed_retrieval_uri_is_allowed_only_beside_stable_canonical_identity(fixtures, contracts):
    assessment, manifest = fixtures["COMPLETED"]
    case = fixture_case_for(assessment)
    retrieval = "https://storage.example.test/asset.tif?sv=2024-01-01&se=2099-01-01&sp=r&sig=temporary"
    case["evidence_policy"]["source_bindings"][3]["retrieval_uri"] = retrieval
    manifest["source_records"][3]["retrieval_uri"] = retrieval
    step1.validate_fixture_pair(case, assessment, manifest, contracts["schemas"], contracts["registries"])
    case["evidence_policy"]["source_bindings"][3]["canonical_uri"] = None
    rejected("retrieval_uri requires a separately validated canonical_uri|frozen binding requires canonical_uri", lambda: validate_case(case, contracts))


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("aoi_total_pixels", -1, "non-negative integer"),
        ("aoi_valid_pixels", 11, "must not exceed"),
        ("aoi_valid_fraction", 1.1, "within \\[0, 1\\]"),
        ("pre_window_ndvi_median", -1.1, "within \\[-1, 1\\]"),
    ],
)
def test_partial_abstained_observations_enforce_numeric_invariants(field, value, expected, fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["observations"] = {
        "observation_status": "PARTIAL",
        "aoi_total_pixels": 10,
        "aoi_valid_pixels": 5,
        "aoi_valid_fraction": 0.5,
        "pre_window_ndvi_median": 0.1,
        "post_window_ndvi_median": None,
        "delta_ndvi": None,
        "primary_tau": None,
        "delta_distribution": None,
        "sensitivity_results": None,
    }
    assessment["observations"][field] = value
    rejected(expected, lambda: validate_assessment(assessment, contracts))


def test_valid_partial_abstained_observations_are_retained(fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["observations"] = {
        "observation_status": "PARTIAL",
        "aoi_total_pixels": 10,
        "aoi_valid_pixels": 5,
        "aoi_valid_fraction": 0.5,
        "pre_window_ndvi_median": 0.1,
        "post_window_ndvi_median": None,
        "delta_ndvi": None,
        "primary_tau": None,
        "delta_distribution": None,
        "sensitivity_results": None,
    }
    validate_assessment(assessment, contracts)


@pytest.mark.parametrize("status", ["COMPLETED", "ABSTAINED"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_ndvi_is_rejected_for_every_status_that_can_carry_observations(status, value, fixtures, contracts):
    assessment, _ = fixtures[status]
    if status == "ABSTAINED":
        assessment["observations"] = {
            "observation_status": "PARTIAL",
            "aoi_total_pixels": 10,
            "aoi_valid_pixels": 5,
            "aoi_valid_fraction": 0.5,
            "pre_window_ndvi_median": 0.1,
            "post_window_ndvi_median": None,
            "delta_ndvi": None,
            "primary_tau": None,
            "delta_distribution": None,
            "sensitivity_results": None,
        }
    assessment["observations"]["pre_window_ndvi_median"] = value
    rejected("non-finite number", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("status", ["REFUSED", "ERROR"])
def test_refused_and_error_require_null_observations(status, fixtures, contracts):
    assessment, _ = fixtures[status]
    assessment["observations"] = {
        "observation_status": "PARTIAL",
        "aoi_total_pixels": None,
        "aoi_valid_pixels": None,
        "aoi_valid_fraction": None,
        "pre_window_ndvi_median": None,
        "post_window_ndvi_median": None,
        "delta_ndvi": None,
        "primary_tau": None,
        "delta_distribution": None,
        "sensitivity_results": None,
    }
    rejected("observations", lambda: validate_assessment(assessment, contracts))


def test_reproduced_error_observation_payload_fails_closed(fixtures, contracts):
    assessment, _ = fixtures["ERROR"]
    assessment["observations"] = {
        "observation_status": "COMPLETE",
        "aoi_total_pixels": 10,
        "aoi_valid_pixels": 999999,
        "aoi_valid_fraction": 0.5,
        "pre_window_ndvi_median": 0.1,
        "post_window_ndvi_median": 0.2,
        "delta_ndvi": 0.1,
        "primary_tau": 0.03,
        "delta_distribution": {"count": 1, "q05": 0.1, "q25": 0.1, "median": 0.1, "q75": 0.1, "q95": 0.1, "iqr": 0.0, "mad": 0.0},
        "sensitivity_results": step1.step2b_offline.classify_primary_and_sensitivities(0.1)["sensitivities"],
    }
    rejected("aoi_valid_pixels must not exceed", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("field", ["project_id", "pre_window", "post_window"])
def test_completed_statement_scope_is_bound_to_authoritative_case(field, fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    assessment["statement_parameters"][field] = "tampered"
    rejected(f"statement {field} does not match authoritative case", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize("field", ["project_id", "pre_window", "post_window"])
def test_rehashed_false_statement_cannot_override_authoritative_case(field, fixtures, contracts):
    assessment, manifest = fixtures["COMPLETED"]
    assessment["statement_parameters"][field] = "attacker-controlled"
    assessment["supported_statement"] = step1.render_statement(assessment, contracts["registries"])
    forged_hash = independent_canonical_sha256(assessment)
    manifest["terminal_result"]["assessment_sha256"] = forged_hash
    terminal_ref = manifest["terminal_result"]["assessment_artifact_ref"]
    next(item for item in manifest["artifact_records"] if item["artifact_id"] == terminal_ref)["content_sha256"] = forged_hash
    rejected(f"statement {field} does not match authoritative case", lambda: validate_pair((assessment, manifest), contracts))


def test_completed_policy_version_is_fixed_in_statement_assessment_and_case(fixtures, contracts):
    assessment, _ = fixtures["COMPLETED"]
    case = fixture_case_for(assessment)
    assert assessment["statement_parameters"]["qualification_policy_version"] == case["qualification_policy"]["policy_version"]
    assert assessment["qualification_policy_version"] == case["qualification_policy"]["policy_version"]
    assessment["statement_parameters"]["qualification_policy_version"] = "tampered"
    rejected("statement qualification_policy_version", lambda: validate_assessment(assessment, contracts, case))


def test_assessment_and_linked_validation_require_authoritative_context(fixtures, contracts):
    assessment, manifest = fixtures["ABSTAINED"]
    rejected(
        "authoritative case context is required",
        lambda: step1.validate_assessment(assessment, None, contracts["schemas"], contracts["registries"]),
    )
    rejected(
        "contexts are all required",
        lambda: step1.validate_linked_result(None, assessment, manifest, contracts["schemas"], contracts["registries"]),
    )
    assert not hasattr(step1, "validate_manifest")


def test_manifest_structure_rejects_relative_parameter_identity(fixtures, contracts):
    _, manifest = fixtures["COMPLETED"]
    manifest["transformation_records"][0]["parameter_set_ref"] = "relative/parameters"
    rejected("absolute https URI or URN", lambda: validate_manifest(manifest, contracts))


def test_reproduced_completed_manifest_with_empty_sources_and_skipped_stages_fails(fixtures, contracts):
    assessment, manifest = fixtures["COMPLETED"]
    manifest["source_records"] = []
    record = manifest["transformation_records"][4]
    record.update({"status": "SKIPPED", "input_artifact_refs": [], "output_artifact_refs": [], "reason_codes": ["SOURCE_UNAVAILABLE"]})
    rejected("complete source and transformation provenance", lambda: validate_pair((assessment, manifest), contracts))


def test_reason_semantics_reject_temporal_reason_with_passing_temporal_check(fixtures, contracts):
    assessment, _ = fixtures["ABSTAINED"]
    assessment["quality_checks"]["temporal_scope"] = "PASS"
    rejected("quality check temporal_scope", lambda: validate_assessment(assessment, contracts))


@pytest.mark.parametrize(
    ("fixture_status", "reason", "expected"),
    [
        ("ABSTAINED", "AUTHORITY_SCOPE_EXCEEDED", "execution status ABSTAINED is not allowed"),
        ("REFUSED", "DETERMINISTIC_PROCESSING_ERROR", "execution status REFUSED is not allowed"),
    ],
)
def test_reason_semantics_reject_cross_category_terminal_statuses(fixture_status, reason, expected, fixtures, contracts):
    assessment, _ = fixtures[fixture_status]
    assessment["reason_codes"] = [reason]
    rejected(expected, lambda: step1._validate_reason_semantics(assessment, contracts["registries"]))
    rejected("reason_codes", lambda: validate_assessment(assessment, contracts))


def test_authority_and_system_failure_reasons_cannot_share_one_terminal_result(fixtures, contracts):
    assessment, _ = fixtures["ERROR"]
    assessment["reason_codes"] = ["AUTHORITY_SCOPE_EXCEEDED", "DETERMINISTIC_PROCESSING_ERROR"]
    assessment["quality_checks"]["authority_scope"] = "FAIL"
    rejected("incompatible reason codes", lambda: step1._validate_reason_semantics(assessment, contracts["registries"]))
    rejected("incompatible reason codes", lambda: validate_assessment(assessment, contracts))


def test_readme_json_examples_are_deterministically_extracted_and_validated(contracts):
    readme = (step1.ROOT / "qualify-environmental-evidence_README_v0.md").read_text(encoding="utf-8")
    blocks = re.findall(r"~~~json\s*\n(.*?)\n~~~", readme, flags=re.DOTALL)
    assert len(blocks) == 2
    documents = [json.loads(block, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))) for block in blocks]
    validate_case(documents[0], contracts)
    validate_assessment(documents[1], contracts, step1.build_fixture_cases()["ABSTAINED"])
