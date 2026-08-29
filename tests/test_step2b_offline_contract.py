from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict

import pytest

from scripts import step2b_offline as offline
from scripts import validate_step1_specs as contracts


@pytest.fixture(scope="module")
def loaded():
    value = contracts.load_contracts()
    contracts.validate_schemas(value["schemas"])
    contracts.validate_registries(value["registries"])
    return value


def synthetic_item(
    item_id: str = "SYNTHETIC-ITEM-1",
    acquisition: str = "2025-06-15T00:00:00Z",
    baseline: str = "05.11",
    red_offset_dn: float = -1000,
    nir_offset_dn: float = -1000,
) -> dict:
    quantification = 10000.0
    return {
        "id": item_id,
        "datetime": acquisition,
        "platform": "SYNTHETIC-SENTINEL-2-FIXTURE",
        "processing_baseline": baseline,
        "datatake_id": "SYNTHETIC-DATATAKE-1",
        "mean_solar_zenith_angle": 60.0,
        "solar_geometry_metadata_source": "SYNTHETIC_ITEM_METADATA",
        "solar_geometry_cross_check": "PASS",
        "assets": {
            "B04": {
                "canonical_identity": f"https://example.test/{item_id}/B04.tif",
                "retrieval_uri": None,
                "raster": {"scale": 1 / quantification, "offset": red_offset_dn / quantification, "nodata": 0},
            },
            "B08": {
                "canonical_identity": f"https://example.test/{item_id}/B08.tif",
                "retrieval_uri": None,
                "raster": {"scale": 1 / quantification, "offset": nir_offset_dn / quantification, "nodata": 0},
            },
        },
        "product_metadata": {
            "quantification_value": quantification,
            "boa_add_offset": {"B04": red_offset_dn, "B08": nir_offset_dn},
            "nodata": 0,
        },
    }


def complete_assessment_for_delta(delta: float, loaded: dict) -> tuple[dict, dict]:
    case = contracts.build_fixture_cases()["COMPLETED"]
    assessment = copy.deepcopy(contracts.build_fixture_pairs(loaded["registries"])["COMPLETED"][0])
    classification = offline.classify_primary_and_sensitivities(delta)
    primary = classification["primary"]
    assessment.update(
        execution_status=primary["execution_status"],
        evidence_disposition=primary["evidence_disposition"],
        reason_codes=primary["reason_codes"],
        human_review_required=primary["execution_status"] != "COMPLETED",
    )
    observations = assessment["observations"]
    observations.update(
        pre_window_ndvi_median=0.0,
        post_window_ndvi_median=delta,
        delta_ndvi=delta,
        primary_tau=0.03,
        delta_distribution={"count": 3, "q05": delta, "q25": delta, "median": delta, "q75": delta, "q95": delta, "iqr": 0.0, "mad": 0.0},
        sensitivity_results=classification["sensitivities"],
    )
    if primary["execution_status"] == "COMPLETED":
        template = contracts.ACTIVE_TEMPLATE_BY_DISPOSITION[primary["evidence_disposition"]]
        assessment["statement_template_id"] = template
        claim = case["claim_contract"]
        assessment["statement_parameters"] = {
            "project_id": case["project"]["project_id"],
            "analysis_boundary_role": claim["analysis_boundary_role"],
            "pre_window": "2000-01-01/2000-01-31",
            "post_window": "2001-01-01/2001-01-31",
            "seasonal_rule_id": claim["seasonal_rule_id"],
            "aggregation": claim["aggregation"],
            "eligible_population": claim["eligible_population"],
            "pre_value": "0.0",
            "post_value": str(delta),
            "delta_value": str(delta),
            "primary_tau": "0.03",
            "indifference_policy_id": offline.PRIMARY_POLICY_ID,
            "qualification_policy_version": contracts.VERSION,
        }
        assessment["supported_statement"] = contracts.render_statement(assessment, loaded["registries"])
        assessment["human_review_required"] = False
    else:
        assessment["statement_template_id"] = None
        assessment["statement_parameters"] = None
        assessment["supported_statement"] = None
    return case, assessment


@pytest.mark.parametrize(
    ("delta", "status", "disposition", "reasons"),
    [
        (0.031, "COMPLETED", "CORROBORATING", []),
        (-0.031, "COMPLETED", "CONTRADICTORY", []),
        (0.0, "ABSTAINED", "INCONCLUSIVE", ["EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND"]),
        (0.03, "ABSTAINED", "INCONCLUSIVE", ["EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND"]),
        (-0.03, "ABSTAINED", "INCONCLUSIVE", ["EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND"]),
    ],
)
def test_primary_three_way_boundaries_hit_python_guard(delta, status, disposition, reasons, loaded):
    result = offline.classify_delta(delta)
    assert (result["execution_status"], result["evidence_disposition"], result["reason_codes"]) == (status, disposition, reasons)
    case, assessment = complete_assessment_for_delta(delta, loaded)
    contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_delta_and_tau_reject_non_finite_values(value):
    with pytest.raises(offline.OfflineContractError, match="finite"):
        offline.classify_delta(value)
    with pytest.raises(offline.OfflineContractError, match="finite"):
        offline.classify_delta(0.0, value)


@pytest.mark.parametrize(("status", "disposition"), [("COMPLETED", "CORROBORATING"), ("REFUSED", None), ("ERROR", None)])
def test_indifference_reason_forbidden_outside_abstained_by_state_matrix(status, disposition, loaded):
    _, assessment = complete_assessment_for_delta(0.0, loaded)
    assessment["execution_status"] = status
    assessment["evidence_disposition"] = disposition
    with pytest.raises(contracts.ContractError, match=f"execution status {status} is not allowed"):
        contracts._validate_reason_semantics(assessment, loaded["registries"])


def test_inconclusive_wrong_reason_state_is_rejected_by_python_guard(loaded):
    _, assessment = complete_assessment_for_delta(0.0, loaded)
    assessment["reason_codes"] = ["VALID_OBSERVATION_COVERAGE_LOW"]
    with pytest.raises(contracts.ContractError, match="quality check observation_coverage"):
        contracts._validate_reason_semantics(assessment, loaded["registries"])


@pytest.mark.parametrize("field", ["delta_ndvi", "primary_tau"])
def test_indifference_reason_requires_finite_bound_delta_and_tau(field, loaded):
    case, assessment = complete_assessment_for_delta(0.0, loaded)
    assessment["observations"][field] = None
    with pytest.raises(contracts.ContractError, match="COMPLETE requires all measurement fields"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_forbidden_duration_language_is_rejected_in_authoritative_claim(loaded):
    case = copy.deepcopy(loaded["case"])
    case["claim_contract"]["claim_text"] += " This proves persistent vegetation development."
    with pytest.raises(contracts.ContractError, match="forbidden ecological-duration language"):
        contracts.validate_case(case, loaded["schemas"], loaded["registries"])


@pytest.mark.parametrize("field", ["analysis_boundary_role", "seasonal_rule_id", "aggregation", "eligible_population", "indifference_policy_id"])
def test_completed_statement_scope_fields_are_machine_bound(field, loaded):
    case, assessment = complete_assessment_for_delta(0.1, loaded)
    assessment["statement_parameters"][field] = "tampered"
    with pytest.raises(contracts.ContractError, match=f"statement {field}"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_statement_tau_and_policy_version_mismatch_are_rejected(loaded):
    case, assessment = complete_assessment_for_delta(0.1, loaded)
    assessment["statement_parameters"]["primary_tau"] = "0.01"
    with pytest.raises(contracts.ContractError, match="statement_parameters|primary_tau"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])
    _, assessment = complete_assessment_for_delta(0.1, loaded)
    assessment["qualification_policy_version"] = "9.9.9"
    with pytest.raises(contracts.ContractError, match="qualification_policy_version"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_zero_offset_reflectance_and_ndvi_oracle():
    assert offline.ndvi_from_reflectance(0.10, 0.40) == pytest.approx(0.60)
    item = synthetic_item(red_offset_dn=0, nir_offset_dn=0)
    value, metadata = offline.calibrated_ndvi(item, 1000, 4000)
    assert value == pytest.approx(0.60)
    assert metadata[0].offset == metadata[1].offset == 0.0


def test_offset_bearing_dn_uses_per_band_metadata_and_rejects_raw_dn_shortcut():
    item = synthetic_item()
    value, (red_metadata, nir_metadata) = offline.calibrated_ndvi(item, 2000, 5000)
    assert offline.reflectance_from_dn(2000, red_metadata) == pytest.approx(0.10)
    assert offline.reflectance_from_dn(5000, nir_metadata) == pytest.approx(0.40)
    assert value == pytest.approx(0.60)
    raw_dn_shortcut = (5000 - 2000) / (5000 + 2000)
    assert raw_dn_shortcut == pytest.approx(3 / 7)
    assert raw_dn_shortcut != pytest.approx(value)


def test_each_item_in_same_window_uses_its_own_baseline_and_offsets():
    zero = synthetic_item(item_id="SYNTHETIC-ZERO", baseline="03.01", red_offset_dn=0, nir_offset_dn=0)
    offset = synthetic_item(item_id="SYNTHETIC-OFFSET", baseline="05.11", red_offset_dn=-1000, nir_offset_dn=-1000)
    zero_value, zero_meta = offline.calibrated_ndvi(zero, 1000, 4000)
    offset_value, offset_meta = offline.calibrated_ndvi(offset, 2000, 5000)
    assert zero_value == offset_value == pytest.approx(0.60)
    assert zero_meta[0].processing_baseline == "03.01"
    assert offset_meta[0].processing_baseline == "05.11"
    assert zero_meta[0].offset != offset_meta[0].offset


def test_per_item_per_band_radiometry_records_validate_in_provenance(loaded):
    _, metadata = offline.calibrated_ndvi(synthetic_item(), 2000, 5000)
    _, manifest = copy.deepcopy(contracts.build_fixture_pairs(loaded["registries"])["COMPLETED"])
    manifest["radiometry_records"] = [asdict(record) for record in metadata]
    contracts.validate_manifest_structure(manifest, loaded["schemas"], loaded["registries"])
    assert {record["asset_key"] for record in manifest["radiometry_records"]} == {"B04", "B08"}
    manifest["radiometry_records"][0]["retrieval_uri"] = "https://example.test/B04.tif?sig=secret"
    with pytest.raises(contracts.ContractError, match="credential-bearing retrieval URI"):
        contracts.validate_manifest_structure(manifest, loaded["schemas"], loaded["registries"])


def test_historical_date_with_modern_reprocessed_baseline_follows_metadata_not_date():
    item = synthetic_item(acquisition="2017-06-15T00:00:00Z", baseline="05.11")
    value, metadata = offline.calibrated_ndvi(item, 2000, 5000)
    assert value == pytest.approx(0.60)
    assert {record.processing_baseline for record in metadata} == {"05.11"}
    assert all(record.offset == pytest.approx(-0.1) for record in metadata)


@pytest.mark.parametrize("mutation", ["missing_offset", "contradictory_offset", "missing_baseline"])
def test_missing_or_contradictory_radiometry_fails_closed(mutation):
    item = synthetic_item()
    if mutation == "missing_offset":
        del item["assets"]["B04"]["raster"]["offset"]
    elif mutation == "contradictory_offset":
        item["assets"]["B04"]["raster"]["offset"] = 0.0
    else:
        del item["processing_baseline"]
    with pytest.raises(offline.OfflineContractError) as error:
        offline.calibrated_ndvi(item, 2000, 5000)
    assert error.value.reason_code == "RADIOMETRY_METADATA_UNRESOLVED"


def test_resource_limit_never_truncates_and_reports_exact_guard():
    items = list(range(41))
    with pytest.raises(offline.OfflineContractError, match="41 exceeds configured maximum 40") as error:
        offline.enforce_item_limit(items, 40)
    assert error.value.reason_code == "RESOURCE_LIMIT_EXCEEDED"
    assert len(items) == 41


def test_project_boundary_cannot_substitute_for_cea():
    digest = "a" * 64
    offline.require_cea_boundary("CEA", digest, digest)
    with pytest.raises(offline.OfflineContractError, match="must be CEA"):
        offline.require_cea_boundary("PROJECT_BOUNDARY", digest, digest)
    with pytest.raises(offline.OfflineContractError, match="does not match"):
        offline.require_cea_boundary("CEA", "b" * 64, digest)


def test_sensitivity_classification_cannot_overwrite_primary_disposition(loaded):
    case, assessment = complete_assessment_for_delta(0.02, loaded)
    assert assessment["execution_status"] == "ABSTAINED"
    assert assessment["observations"]["sensitivity_results"][0]["evidence_disposition"] == "CORROBORATING"
    assessment["execution_status"] = "COMPLETED"
    assessment["evidence_disposition"] = "CORROBORATING"
    assessment["reason_codes"] = []
    assessment["human_review_required"] = False
    with pytest.raises(contracts.ContractError, match="primary execution_status"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_distribution_fields_reject_non_finite_values(value, loaded):
    case, assessment = complete_assessment_for_delta(0.1, loaded)
    assessment["observations"]["delta_distribution"]["q05"] = value
    with pytest.raises(contracts.ContractError, match="non-finite"):
        contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_independent_acquisitions_use_datatake_identity_not_tile_count():
    first = synthetic_item(item_id="SYNTHETIC-TILE-A")
    second = synthetic_item(item_id="SYNTHETIC-TILE-B")
    third = synthetic_item(item_id="SYNTHETIC-DATATAKE-2")
    third["datatake_id"] = "SYNTHETIC-DATATAKE-2"
    assert offline.independent_acquisition_ids([first, second, third]) == ["SYNTHETIC-DATATAKE-1", "SYNTHETIC-DATATAKE-2"]


def test_grid_congruence_fails_closed_on_shift():
    offline.require_congruent_utm_grid([{"x_resolution": 10, "y_resolution": -10, "x_origin": 738700, "y_origin": 5957830}])
    with pytest.raises(offline.OfflineContractError, match="not congruent"):
        offline.require_congruent_utm_grid([{"x_resolution": 10, "y_resolution": -10, "x_origin": 738705, "y_origin": 5957830}])


def test_policy_has_no_scene_cloud_query_predicate_and_remains_pending(loaded):
    policy = contracts.load_json(contracts.ROOT / "policies" / "eop101132" / "step2b-proposed-policy.json")
    assert policy["approval_status"] == "PENDING_HUMAN_APPROVAL"
    assert policy["proposed_execution_mode"] == "QUALIFICATION"
    assert policy["approval"]["status"] == "PENDING_HUMAN_APPROVAL"
    assert policy["runtime_ready"] is False
    assert policy["approval"]["sentinel_2_access_permitted"] is False
    assert all("cloud" not in predicate.lower() for predicate in policy["stac_source_and_selection"]["query_predicates"])
    assert "Do not send eo:cloud_cover" in policy["stac_source_and_selection"]["scene_cloud_metadata_rule"]


def test_v2_history_and_v3_candidate_hashes_are_frozen(loaded):
    current_bytes = contracts.V3_POLICY_FILE.read_bytes()
    historical_bytes = (contracts.V3_POLICY_FILE.parent / "step2b-proposed-policy-v2.json").read_bytes()
    assert contracts.load_json(contracts.V3_POLICY_FILE)["policy_id"] == "DEMO_QUALIFICATION_POLICY_EOP101132_V3"
    assert loaded["policy"]["policy_id"] == "DEMO_QUALIFICATION_POLICY_EOP101132_V4"
    assert hashlib.sha256(current_bytes).hexdigest() == "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"
    assert hashlib.sha256(historical_bytes).hexdigest() == "014336ca3aa4db16f1e7b26123c75c1e47013d2463381a5dae0379392e994dac"


def test_no_fixture_is_described_as_a_real_sentinel_scene():
    assert "SYNTHETIC" in synthetic_item()["platform"]
    assert not hasattr(offline, "search_stac")
    assert not hasattr(offline, "read_raster")


@pytest.mark.parametrize("value", [69.999, 70.0])
def test_solar_zenith_inclusive_boundary_is_admitted(value):
    item = synthetic_item()
    item["mean_solar_zenith_angle"] = value
    record = offline.resolve_solar_geometry(item, "POST")
    assert record.admissible is True
    assert record.exclusion_reason is None


def test_solar_zenith_above_limit_is_excluded_without_error_state():
    item = synthetic_item()
    item["mean_solar_zenith_angle"] = 70.0001
    record = offline.resolve_solar_geometry(item, "POST")
    assert record.admissible is False
    assert record.exclusion_reason == "SOLAR_GEOMETRY_OUT_OF_RANGE"


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "69.0"])
def test_unresolved_or_unparseable_solar_geometry_is_excluded(value):
    item = synthetic_item()
    item["mean_solar_zenith_angle"] = value
    record = offline.resolve_solar_geometry(item, "POST")
    assert record.admissible is False
    assert record.exclusion_reason == "SOLAR_GEOMETRY_METADATA_UNRESOLVED"


def test_date_latitude_and_season_are_never_solar_geometry_fallbacks():
    item = synthetic_item(acquisition="2025-06-21T00:00:00Z")
    item.pop("mean_solar_zenith_angle")
    item.update(latitude=-36.5, season="JJA")
    record = offline.resolve_solar_geometry(item, "POST")
    assert record.mean_solar_zenith_angle is None
    assert record.exclusion_reason == "SOLAR_GEOMETRY_METADATA_UNRESOLVED"


def _scene(index: int, sza: float | None, ndvi: float = 0.2, coverage: float = 0.9) -> dict:
    item = synthetic_item(item_id=f"SYNTHETIC-SCENE-{index}")
    item["datatake_id"] = f"SYNTHETIC-DATATAKE-{index}"
    item["mean_solar_zenith_angle"] = sza
    item["synthetic_ndvi"] = ndvi
    item["synthetic_coverage"] = coverage
    return item


def test_excluded_item_cannot_count_or_affect_coverage_or_ndvi():
    items = [_scene(1, 60.0, 0.1, 0.8), _scene(2, 61.0, 0.2, 0.9), _scene(3, 62.0, 0.3, 1.0), _scene(4, 71.0, 0.99, 0.0)]
    gate = offline.evaluate_window_gate(items, "POST", admissible_valid_pixel_fraction=0.9)
    assert gate["independent_acquisition_count"] == 3
    assert gate["execution_status"] == "COMPLETED"
    assert offline.admissible_measurement_values(items, "POST", "synthetic_ndvi") == [0.1, 0.2, 0.3]
    assert offline.admissible_measurement_values(items, "POST", "synthetic_coverage") == [0.8, 0.9, 1.0]


def test_solar_exclusions_that_break_minimum_use_exact_abstained_guard():
    items = [_scene(1, 60.0), _scene(2, 61.0), _scene(3, 71.0), _scene(4, None)]
    gate = offline.evaluate_window_gate(items, "PRE", admissible_valid_pixel_fraction=0.95)
    assert gate["independent_acquisition_count"] == 2
    assert gate["execution_status"] == "ABSTAINED"
    assert gate["evidence_disposition"] == "INCONCLUSIVE"
    assert gate["reason_codes"] == ["VALID_OBSERVATION_COVERAGE_LOW"]


def test_solar_provenance_counts_included_and_excluded_items(loaded):
    pre = offline.partition_items_by_solar_geometry([_scene(1, 65.0), _scene(2, 71.0), _scene(3, None)], "PRE")["records"]
    post = offline.partition_items_by_solar_geometry([_scene(4, 60.0), _scene(5, 62.0), _scene(6, 64.0)], "POST")["records"]
    summary = offline.solar_geometry_diagnostic(pre, post)
    assert summary["pre_window"]["discovered"]["count"] == 3
    assert summary["pre_window"]["admitted"]["count"] == 1
    assert summary["pre_window"]["discovered"]["excluded_above_threshold_count"] == 1
    assert summary["pre_window"]["discovered"]["excluded_unresolved_count"] == 1
    _, manifest = copy.deepcopy(contracts.build_fixture_pairs(loaded["registries"])["COMPLETED"])
    manifest["solar_geometry_records"] = pre + post
    manifest["solar_geometry_summary"] = summary
    contracts.validate_manifest_structure(manifest, loaded["schemas"], loaded["registries"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("instrument_detection_limit", True),
        ("ecological_standard", True),
        ("regulatory_standard", True),
        ("assurance_standard", True),
        ("cer_rule", True),
    ],
)
def test_tau_cannot_be_relabelled_as_an_authoritative_threshold(field, value, loaded):
    policy = copy.deepcopy(loaded["policy"])
    policy["operational_indifference_band"][field] = value
    with pytest.raises(contracts.ContractError, match="tau cannot be represented"):
        contracts.validate_policy_proposal(policy, loaded["case"])


def test_primary_years_are_frozen_and_undeclared_year_is_rejected(loaded):
    policy = loaded["policy"]
    scope = policy["temporal_scope"]["baseline_year_scope"]
    assert scope["primary_pre_years"] == [2017]
    assert scope["primary_post_years"] == [2025]
    assert scope["additional_baseline_years"] == []
    mutated = copy.deepcopy(policy)
    mutated["temporal_scope"]["baseline_year_scope"]["additional_baseline_years"] = [2016]
    with pytest.raises(contracts.ContractError, match="baseline-year immutability"):
        contracts.validate_policy_proposal(mutated, loaded["case"])


def test_future_policy_requires_new_run_and_cannot_overwrite_primary():
    with pytest.raises(offline.OfflineContractError, match="new run ID"):
        offline.require_new_run_for_policy("RUN-1", "a" * 64, "RUN-1", "b" * 64)
    offline.require_new_run_for_policy("RUN-1", "a" * 64, "RUN-2", "b" * 64)


def test_pending_policy_cannot_pass_runtime_hash_gate(loaded):
    policy_path = contracts.POLICY_FILE
    with pytest.raises(offline.OfflineContractError, match="network access is prohibited"):
        offline.require_approved_policy_for_runtime(loaded["policy"], None, policy_path.read_bytes())


def test_detached_approval_authorises_exact_pending_policy_without_mutation(loaded):
    policy_bytes = contracts.POLICY_FILE.read_bytes()
    digest = hashlib.sha256(policy_bytes).hexdigest()
    approval = {
        "approval_record_version": "1.0.0",
        "policy_id": loaded["policy"]["policy_id"],
        "approved_policy_sha256": digest,
        "mode": "QUALIFICATION",
        "approval_statement": f"批准 QUALIFICATION {digest}",
        "approval_timestamp_utc": "2026-08-29T00:00:00Z",
        "approver_role": "HUMAN_PROJECT_OWNER",
        "runtime_scope": "ONE_PRIMARY_EOP101132_RUN",
        "policy_mutation_permitted": False,
    }
    assert offline.validate_detached_approval(loaded["policy"], policy_bytes, approval) == digest
    assert loaded["policy"]["approval_status"] == "PENDING_HUMAN_APPROVAL"
    tampered = copy.deepcopy(approval)
    tampered["mode"] = "MEASUREMENT_ONLY"
    with pytest.raises(offline.OfflineContractError, match="mode"):
        offline.validate_detached_approval(loaded["policy"], policy_bytes, tampered)


def test_policy_and_input_hashes_are_immutable_during_an_approved_synthetic_run(loaded):
    policy = copy.deepcopy(loaded["policy"])
    policy["approval_status"] = "APPROVED"
    policy["runtime_ready"] = True
    policy["approval"]["status"] = "APPROVED"
    policy["approval"]["sentinel_2_access_permitted"] = True
    policy_bytes = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    policy_hash = hashlib.sha256(policy_bytes).hexdigest()
    input_hash = "c" * 64
    identity = offline.freeze_run_identity(policy, policy_hash, policy_bytes, input_hash)
    offline.verify_run_identity(identity, policy_bytes, input_hash)
    with pytest.raises(offline.OfflineContractError, match="policy mutated"):
        offline.verify_run_identity(identity, policy_bytes + b" ", input_hash)
    with pytest.raises(offline.OfflineContractError, match="input mutated"):
        offline.verify_run_identity(identity, policy_bytes, "d" * 64)


def test_active_completed_statement_cannot_claim_trend_or_persistence(loaded):
    registries = copy.deepcopy(loaded["registries"])
    registries["statement_templates"]["templates"][2]["template_text"] = registries["statement_templates"]["templates"][2]["template_text"].replace(
        "the {aggregation}", "the multi-year trend in the {aggregation}"
    )
    with pytest.raises(contracts.ContractError, match="forbidden ecological-duration language"):
        contracts.validate_registries(registries)
