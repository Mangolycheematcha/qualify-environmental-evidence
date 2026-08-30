from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from scripts import step2b_v4_raster as raster
from scripts import step2b_v4_runtime as runtime
from scripts import validate_step1_specs as contracts

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"


def _approval(spec_hash: str, commit: str = "a" * 40) -> dict:
    return {
        "approval_record_version": "2.0.0",
        "policy_id": runtime.POLICY_ID,
        "approved_policy_sha256": runtime.APPROVED_POLICY_SHA256,
        "runtime_spec_id": runtime.RUNTIME_SPEC_ID,
        "approved_runtime_spec_sha256": spec_hash,
        "approved_git_commit": commit,
        "mode": "QUALIFICATION",
        "approval_statement": runtime.approval_statement(runtime.APPROVED_POLICY_SHA256, spec_hash, commit),
        "approval_record_created_at_utc": "2026-08-30T00:00:00Z",
        "approver_role": "HUMAN_PROJECT_OWNER",
        "allowed_scope": runtime.APPROVAL_SCOPE,
        "policy_mutation_permitted": False,
    }


def test_v4_policy_bytes_remain_unchanged():
    assert hashlib.sha256(POLICY.read_bytes()).hexdigest() == runtime.APPROVED_POLICY_SHA256


def test_exact_three_way_approval_binding():
    approval = _approval("b" * 64)
    runtime.validate_detached_approval(approval, runtime_spec_hash="b" * 64, git_commit="a" * 40)
    approval["allowed_scope"] = "ONE_PRIMARY_EOP101132_RUN"
    with pytest.raises(runtime.V4RuntimeFailure, match="allowed_scope"):
        runtime.validate_detached_approval(approval, runtime_spec_hash="b" * 64, git_commit="a" * 40)


def test_frozen_runtime_spec_and_all_implementation_hashes_validate():
    digest = hashlib.sha256(runtime.RUNTIME_SPEC_PATH.read_bytes()).hexdigest()
    spec, actual = runtime.verify_runtime_spec(digest, verify_packages=False)
    assert actual == digest
    assert spec["approved_policy_sha256"] == runtime.APPROVED_POLICY_SHA256
    assert spec["approval_binding"]["statement_template"].endswith("{git_commit}")


def test_snapped_grid_uses_frozen_lattice():
    grid = raster.snapped_grid((123.1, 9_999_876.1, 149.9, 9_999_899.1))
    assert grid["bounds"] == [120.0, 9_999_870.0, 150.0, 9_999_900.0]
    assert grid["width"] == grid["height"] == 3
    assert grid["transform"] == [10.0, 0.0, 120.0, 0.0, -10.0, 9_999_900.0]


def test_per_item_offsets_are_applied_before_ndvi():
    red = np.array([[2000, 2000, 0]])
    nir = np.array([[5000, 5000, 5000]])
    scl = np.array([[4, 9, 4]])
    result = raster.calibrated_ndvi_array(
        red,
        nir,
        scl,
        red_scale=0.0001,
        red_offset=-0.1,
        nir_scale=0.0001,
        nir_offset=-0.1,
        red_nodata=0,
        nir_nodata=0,
    )
    assert result[0, 0] == pytest.approx(0.6)
    assert np.isnan(result[0, 1])
    assert np.isnan(result[0, 2])


def test_component_mosaic_is_order_independent_and_conflicts_fail_closed():
    left = np.array([[0.1, np.nan]])
    right = np.array([[0.1, 0.2]])
    expected = np.array([[0.1, 0.2]])
    assert np.allclose(raster.mosaic_acquisition_components([("55HBV", right), ("54HYE", left)]), expected)
    with pytest.raises(raster.RasterContractError, match="conflicts") as error:
        raster.mosaic_acquisition_components([("54HYE", left), ("55HBV", np.array([[0.11, 0.2]]))])
    assert error.value.reason_code == "EVIDENCE_CONFLICT_UNRESOLVED"


def test_aggregation_uses_independent_acquisitions_and_joint_mask():
    aoi = np.ones((2, 2), dtype=bool)
    pre = [np.full((2, 2), value) for value in (0.1, 0.2, 0.3)]
    post = [np.full((2, 2), value) for value in (0.2, 0.3, 0.4)]
    result = raster.aggregate_windows(pre, post, aoi)
    assert result["coverage_passed"] is True
    assert result["aoi_valid_fraction"] == 1.0
    assert result["pre_window_ndvi_median"] == pytest.approx(0.2)
    assert result["post_window_ndvi_median"] == pytest.approx(0.3)
    assert result["delta_ndvi"] == pytest.approx(0.1)
    assert result["delta_distribution"]["count"] == 4
    qualified = raster.qualification_from_aggregation(result)
    assert qualified["execution_status"] == "COMPLETED"
    assert qualified["evidence_disposition"] == "CORROBORATING"


def test_low_joint_coverage_preserves_measurements_but_does_not_qualify():
    aoi = np.ones((2, 2), dtype=bool)
    pre = [np.array([[0.1, np.nan], [np.nan, np.nan]]) for _ in range(3)]
    post = [np.array([[0.2, np.nan], [np.nan, np.nan]]) for _ in range(3)]
    result = raster.aggregate_windows(pre, post, aoi)
    assert result["coverage_passed"] is False
    assert result["aoi_valid_fraction"] == 0.25
    assert result["delta_ndvi"] == pytest.approx(0.1)
    qualified = raster.qualification_from_aggregation(result)
    assert qualified == {
        "execution_status": "ABSTAINED",
        "evidence_disposition": "INCONCLUSIVE",
        "reason_codes": ["VALID_OBSERVATION_COVERAGE_LOW"],
        "primary": None,
        "sensitivities": None,
    }


def test_product_xml_radiometry_is_per_band_and_cross_checked():
    xml = b"""<root><BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>
    <BOA_ADD_OFFSET band_id="3">-1000</BOA_ADD_OFFSET><BOA_ADD_OFFSET band_id="7">-500</BOA_ADD_OFFSET>
    <Special_Values><SPECIAL_VALUE_TEXT>NODATA</SPECIAL_VALUE_TEXT><SPECIAL_VALUE_INDEX>0</SPECIAL_VALUE_INDEX></Special_Values></root>"""
    assert runtime._parse_radiometry(xml, "B04")["offset"] == -0.1
    assert runtime._parse_radiometry(xml, "B08")["offset"] == -0.05
    assert runtime._parse_radiometry(xml, "B04")["scale"] == 0.0001


def test_complete_assessment_passes_contract_validator():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    aoi = np.ones((2, 2), dtype=bool)
    pre = [np.full((2, 2), value) for value in (0.1, 0.2, 0.3)]
    post = [np.full((2, 2), value) for value in (0.2, 0.3, 0.4)]
    aggregation = raster.aggregate_windows(pre, post, aoi)
    assessment = runtime.build_assessment("SYNTHETIC-V4-RUN", policy, aggregation)
    loaded = contracts.load_contracts()
    case = deepcopy(loaded["case"])
    contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_coverage_failure_assessment_is_partial_and_contract_valid():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    aoi = np.ones((2, 2), dtype=bool)
    values = [np.array([[0.1, np.nan], [np.nan, np.nan]]) for _ in range(3)]
    aggregation = raster.aggregate_windows(values, [value + 0.1 for value in values], aoi)
    assessment = runtime.build_assessment("SYNTHETIC-V4-LOW-COVERAGE", policy, aggregation)
    assert assessment["observations"]["observation_status"] == "PARTIAL"
    loaded = contracts.load_contracts()
    case = deepcopy(loaded["case"])
    contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])


def test_runtime_manifest_carries_three_way_identity_and_validates(tmp_path):
    run_dir = tmp_path / "SYNTHETIC-V4-RUN"
    for name in ("approval", "frozen", "source", "grouping", "diagnostics"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    (run_dir / "frozen" / "policy.json").write_bytes(POLICY.read_bytes())
    (run_dir / "frozen" / "runtime-spec.json").write_bytes(runtime.RUNTIME_SPEC_PATH.read_bytes())
    runtime.write_json(run_dir / "approval" / "approval.json", _approval("b" * 64))
    runtime.legacy_io._runtime_case(run_dir, policy)
    project_raw = b"synthetic project record"
    runtime.write_json(
        run_dir / "source" / "cer-project-page.metadata.json",
        {"retrieved_at_utc": "2026-08-30T00:00:00Z", "response_sha256": hashlib.sha256(project_raw).hexdigest()},
    )
    runtime.write_json(
        run_dir / "source" / "eop101132-cea.metadata.json",
        {"retrieved_at_utc": "2026-08-30T00:00:00Z"},
    )
    item = {"type": "Feature", "collection": "sentinel-2-l2a", "id": "SYNTHETIC", "properties": {"datetime": "2025-06-01T00:00:00Z"}}
    for window in ("pre", "post"):
        runtime.write_json(
            run_dir / "source" / f"stac-{window}-requests.json",
            [{"retrieved_at_utc": "2026-08-30T00:00:00Z", "response_sha256": hashlib.sha256(window.encode()).hexdigest()}],
        )
        runtime.write_json(run_dir / "source" / f"stac-{window}.raw.json", {"type": "FeatureCollection", "features": [item]}, canonical=True)
    aoi = np.ones((2, 2), dtype=bool)
    aggregation = raster.aggregate_windows(
        [np.full((2, 2), value) for value in (0.1, 0.2, 0.3)],
        [np.full((2, 2), value) for value in (0.2, 0.3, 0.4)],
        aoi,
    )
    assessment = runtime.build_assessment(run_dir.name, policy, aggregation)
    runtime.write_json(run_dir / "assessment.json", assessment, canonical=True)
    runtime.write_json(run_dir / "sensitivity.json", {"results": assessment["observations"]["sensitivity_results"]}, canonical=True)
    runtime.write_json(
        run_dir / "diagnostics" / "solar-geometry-records.json",
        [
            {
                "window": window,
                "item_id": f"SYNTHETIC-{window}",
                "acquisition_datetime": "2025-06-01T00:00:00Z",
                "platform": "Sentinel-2A",
                "datatake_id": f"SYNTHETIC-{window}",
                "mean_solar_zenith_angle": 50.0,
                "metadata_source": "SYNTHETIC-TEST",
                "cross_check": "PASS",
                "admissible": True,
                "exclusion_reason": None,
                "processing_baseline": "05.11",
            }
            for window in ("PRE", "POST")
        ],
        canonical=True,
    )
    runtime.write_json(
        run_dir / "run-state.json",
        {
            "run_id": run_dir.name,
            "case_id": "EOP101132-NDVI-001",
            "policy_sha256": runtime.APPROVED_POLICY_SHA256,
            "runtime_spec_sha256": "b" * 64,
            "approval_sha256": hashlib.sha256((run_dir / "approval" / "approval.json").read_bytes()).hexdigest(),
            "git_commit": "a" * 40,
            "created_at_utc": "2026-08-30T00:00:00Z",
            "stage": "RASTER_AGGREGATION_COMPLETE",
        },
    )
    manifest = runtime.build_manifest(run_dir, assessment)
    runtime.write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    runtime.validate_runtime_outputs(run_dir)
    identity = manifest["run_identity"]
    assert identity["approved_runtime_spec_sha256"] == "b" * 64
    assert identity["git_commit"] == "a" * 40
    assert identity["detached_approval_sha256"] == runtime.sha256_file(run_dir / "approval" / "approval.json")


def test_offline_replay_recomputes_ndvi_from_safe_aoi_inputs(tmp_path):
    (tmp_path / "cache").mkdir()
    aoi = np.ones((1, 1), dtype=bool)
    np.save(tmp_path / "cache" / "aoi-mask.npy", aoi, allow_pickle=False)
    records = []
    for window, values in (("PRE", (2000, 5000)), ("POST", (2000, 6000))):
        for sequence in range(3):
            red = np.array([[values[0]]])
            nir = np.array([[values[1]]])
            scl = np.array([[4]])
            valid = np.array([[True]])
            component_path = f"cache/{window.lower()}-{sequence}.npz"
            np.savez_compressed(tmp_path / component_path, red_dn=red, nir_dn=nir, scl=scl, source_valid=valid)
            radiometry = {"scale": 0.0001, "offset": -0.1, "quantification_value": 10000, "nodata": 0, "metadata_source": "TEST", "cross_check": "PASS"}
            ndvi = raster.calibrated_ndvi_array(
                red,
                nir,
                scl,
                red_scale=radiometry["scale"],
                red_offset=radiometry["offset"],
                nir_scale=radiometry["scale"],
                nir_offset=radiometry["offset"],
                red_nodata=0,
                nir_nodata=0,
                source_valid_mask=valid,
            )
            records.append(
                {
                    "window": window,
                    "path": f"cache/derived-{window.lower()}-{sequence}.npy",
                    "array_sha256": raster.canonical_array_sha256(ndvi),
                    "components": [
                        {
                            "path": component_path,
                            "mgrs_tile": "54HYE",
                            "red_dn_sha256": raster.canonical_array_sha256(red),
                            "nir_dn_sha256": raster.canonical_array_sha256(nir),
                            "scl_sha256": raster.canonical_array_sha256(scl),
                            "source_valid_sha256": raster.canonical_array_sha256(valid),
                            "red_radiometry": radiometry,
                            "nir_radiometry": radiometry,
                        }
                    ],
                }
            )
    runtime.write_json(tmp_path / "cache" / "index.json", records, canonical=True)
    result = runtime._replay_aggregation(
        tmp_path,
        {"coverage": {"minimum_valid_observations_per_pixel_per_window": 3, "minimum_joint_aoi_fraction": 0.8}},
    )
    assert result["coverage_passed"] is True
    assert result["delta_ndvi"] > 0


def test_failure_messages_strip_signed_query_strings():
    error = RuntimeError("failed https://blob.example.test/a.tif?se=expiry&sig=secret")
    assert runtime._safe_error_message(error) == "failed https://blob.example.test/a.tif"


def test_network_retry_is_bounded_and_audited(monkeypatch):
    calls = []
    sleeps = []

    def transient_request(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) < 3:
            raise runtime.legacy_io.RuntimeFailure("temporary timeout", "SOURCE_UNAVAILABLE")
        return b"ok", {"http_status": 200}

    monkeypatch.setattr(runtime.legacy_io, "http_request", transient_request)
    monkeypatch.setattr(runtime.time, "sleep", sleeps.append)
    raw, metadata = runtime._http_request("https://planetarycomputer.microsoft.com/test")
    assert raw == b"ok"
    assert len(calls) == 3
    assert sleeps == [2, 5]
    assert metadata["request_attempt_count"] == 3
    assert metadata["retry_delays_seconds"] == [0, 2, 5]


def test_raw_timeout_error_uses_frozen_retry_policy(monkeypatch):
    calls = []
    sleeps = []

    def timeout_then_succeed(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            raise TimeoutError("The read operation timed out")
        return b"ok", {"http_status": 200}

    monkeypatch.setattr(runtime.legacy_io, "http_request", timeout_then_succeed)
    monkeypatch.setattr(runtime.time, "sleep", sleeps.append)
    raw, metadata = runtime._http_request("https://planetarycomputer.microsoft.com/test")
    assert raw == b"ok"
    assert len(calls) == 2
    assert sleeps == [2]
    assert metadata["request_attempt_count"] == 2
    assert metadata["retry_delays_seconds"] == [0, 2]


def test_network_access_is_persisted_before_first_request(tmp_path, monkeypatch):
    state = {"stage": "INITIALIZED", "network_accessed": False}
    policy = {"project_and_boundary": {"project_page": "https://cer.gov.au/test"}}
    runtime.write_json(tmp_path / "frozen" / "policy.json", policy)
    monkeypatch.setattr(runtime, "_run_guard", lambda _run_dir: (state, {}, {}))
    monkeypatch.setattr(
        runtime,
        "_http_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime.V4RuntimeFailure("source unavailable", "SOURCE_UNAVAILABLE")
        ),
    )
    with pytest.raises(runtime.V4RuntimeFailure, match="source unavailable"):
        runtime.fetch_sources(tmp_path)
    persisted = runtime.read_json(tmp_path / "run-state.json")
    assert persisted["stage"] == "SOURCE_FETCH_STARTED"
    assert persisted["network_accessed"] is True


def test_json_security_scan_distinguishes_strings_from_non_finite_values(tmp_path):
    safe = tmp_path / "runtime-spec.json"
    safe.write_text('{"scan_for":"NaN/Infinity"}\n', encoding="utf-8")
    (tmp_path / "source-metadata.xml").write_text("<value>NaN</value>\n", encoding="utf-8")
    runtime._security_scan(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(runtime.V4RuntimeFailure, match="non-finite JSON value"):
        runtime._security_scan(tmp_path)


def test_failure_sealing_does_not_replace_primary_error(tmp_path, monkeypatch):
    (tmp_path / "diagnostics").mkdir()
    runtime.write_json(tmp_path / "run-state.json", {"stage": "INITIALIZED", "network_accessed": True})

    def sealing_failure(_run_dir):
        raise runtime.V4RuntimeFailure("secondary scan error", "PROVENANCE_INCOMPLETE")

    monkeypatch.setattr(runtime, "_security_scan", sealing_failure)
    primary = runtime.V4RuntimeFailure(
        "primary timeout",
        "SOURCE_UNAVAILABLE",
        details={"network_attempts": [{"attempt": 1}]},
    )
    runtime.record_failure(tmp_path, primary)
    failure = runtime.read_json(tmp_path / "diagnostics" / "runtime-failure.json")
    sealing = runtime.read_json(tmp_path / "diagnostics" / "failure-sealing-errors.json")
    state = runtime.read_json(tmp_path / "run-state.json")
    assert failure["reason_code"] == "SOURCE_UNAVAILABLE"
    assert failure["details"] == {"network_attempts": [{"attempt": 1}]}
    assert sealing[0]["reason_code"] == "PROVENANCE_INCOMPLETE"
    assert state["terminal_reason_codes"] == ["SOURCE_UNAVAILABLE"]


def test_checksum_sealing_does_not_replace_primary_error(tmp_path, monkeypatch):
    (tmp_path / "diagnostics").mkdir()
    runtime.write_json(tmp_path / "run-state.json", {"stage": "INITIALIZED", "network_accessed": True})
    monkeypatch.setattr(runtime, "_security_scan", lambda _run_dir: None)
    monkeypatch.setattr(
        runtime,
        "_write_checksums",
        lambda _run_dir: (_ for _ in ()).throw(OSError("checksum write failed")),
    )
    runtime.record_failure(tmp_path, runtime.V4RuntimeFailure("primary timeout", "SOURCE_UNAVAILABLE"))
    failure = runtime.read_json(tmp_path / "diagnostics" / "runtime-failure.json")
    sealing = runtime.read_json(tmp_path / "diagnostics" / "failure-sealing-errors.json")
    assert failure["reason_code"] == "SOURCE_UNAVAILABLE"
    assert sealing == [
        {
            "operation": "write_checksums",
            "exception_type": "OSError",
            "reason_code": "DETERMINISTIC_PROCESSING_ERROR",
            "message": "checksum write failed",
        }
    ]
