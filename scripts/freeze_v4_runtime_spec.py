from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runtime-specs" / "eop101132" / "step2b-v4-runtime-spec.json"
POLICY_SHA256 = "3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd"

IMPLEMENTATION_FILES = (
    ".gitattributes",
    "cases/eop101132/case-spec.json",
    "config/allowed-transformations.json",
    "config/evidence-sources.json",
    "config/forbidden-inferences.json",
    "config/reason-codes.json",
    "config/statement-templates.json",
    "pyproject.toml",
    "requirements-v4-runtime.txt",
    "schemas/assessment-output.schema.json",
    "schemas/claim-contract.schema.json",
    "schemas/provenance-manifest.schema.json",
    "scripts/freeze_v4_runtime_spec.py",
    "scripts/step2b_acquisition.py",
    "scripts/step2b_offline.py",
    "scripts/step2b_runtime.py",
    "scripts/step2b_v4_raster.py",
    "scripts/step2b_v4_runtime.py",
    "scripts/validate_step1_specs.py",
    "uv.lock",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_spec() -> dict[str, Any]:
    policy_path = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"
    if sha256_file(policy_path) != POLICY_SHA256:
        raise ValueError("V4 policy hash drift")
    return {
        "runtime_spec_version": "1.0.0",
        "runtime_spec_id": "EOP101132_STEP2B_V4_RUNTIME_V1",
        "policy_id": "DEMO_QUALIFICATION_POLICY_EOP101132_V4",
        "approved_policy_sha256": POLICY_SHA256,
        "contract_version": "0.5.0",
        "approval_record_version": "2.0.0",
        "allowed_scope": "ONE_EOP101132_V4_PRIMARY_RUN",
        "approval_binding": {
            "required_fields": [
                "approval_record_version",
                "policy_id",
                "approved_policy_sha256",
                "runtime_spec_id",
                "approved_runtime_spec_sha256",
                "approved_git_commit",
                "mode",
                "approval_statement",
                "approval_record_created_at_utc",
                "approver_role",
                "allowed_scope",
                "policy_mutation_permitted",
            ],
            "mode": "QUALIFICATION",
            "approver_role": "HUMAN_PROJECT_OWNER",
            "policy_mutation_permitted": False,
            "statement_template": "批准 QUALIFICATION {policy_sha256} RUNTIME_SPEC {runtime_spec_sha256} COMMIT {git_commit}",
            "readiness_rule": "Exact detached approval, policy bytes, runtime-spec bytes, implementation hashes, package versions, Git commit and clean tree must pass before network access.",
        },
        "runtime_packages": {"numpy": "2.5.2", "rasterio": "1.5.1"},
        "python_runtime": {"implementation": "CPython", "major_minor": "3.14"},
        "implementation_files": {relative: sha256_file(ROOT / relative) for relative in IMPLEMENTATION_FILES},
        "network": {
            "allowed_control_hosts": ["cer.gov.au", "planetarycomputer.microsoft.com"],
            "allowed_data_hosts": ["canonical Azure Blob hosts returned by approved sentinel-2-l2a STAC items"],
            "other_network_prohibited": True,
            "signed_urls_in_memory_only": True,
            "persisted_retrieval_uri": "canonical unsigned URL without query",
        },
        "source_and_search": {
            "project_id": "EOP101132",
            "cea_sha256": "3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2",
            "collection": "sentinel-2-l2a",
            "pre_window": ["2017-06-01", "2017-08-31"],
            "post_window": ["2025-06-01", "2025-08-31"],
            "cloud_cover_query_predicate": False,
            "complete_pagination_required": True,
        },
        "grouping": {
            "rule_id": "SENTINEL2_METADATA_ONLY_ACQUISITION_GROUPING_V1",
            "independent_identity": ["platform", "s2:datatake_id"],
            "component_identity": ["platform", "s2:datatake_id", "s2:mgrs_tile"],
            "representation_priority": ["valid source and collection", "highest processing baseline", "latest s2:generation_time", "lexicographically smallest equivalent item ID"],
            "environmental_selection_fields_prohibited": True,
            "canonical_output": "CANONICAL_JSON_V1",
        },
        "metadata_admissibility": {
            "remote_metadata_assets": ["product-metadata", "granule-metadata"],
            "solar_geometry_cross_check_tolerance_degrees": 1e-6,
            "solar_zenith_maximum_inclusive_degrees": 70.0,
            "radiometry": "Per-item and per-band BOA_QUANTIFICATION_VALUE, BOA_ADD_OFFSET or XML-schema zero default, and NODATA; product XML is cached and cross-checked before raster pixels.",
            "processing_timestamp_field": "s2:generation_time",
        },
        "resource_limits": {
            "raw_stac_items_per_window_max": 200,
            "independent_admissible_acquisition_groups_per_window_max": 40,
            "maximum_grid_width_pixels": 1000,
            "maximum_grid_height_pixels": 1000,
            "maximum_full_aoi_pixels": 200000,
            "truncation_permitted": False,
        },
        "raster": {
            "target_crs": "EPSG:32754",
            "target_resolution_m": 10,
            "target_origin": [0, 10000000],
            "aoi_rule": "pixel centre; all_touched=false",
            "spectral_resampling": "None. A WarpedVRT may only act as a congruence-preserving AOI window adapter where source and target are the identical 10 m EPSG:32754 lattice; interpolation or grid shift fails closed.",
            "scl_resampling": "nearest",
            "valid_scl_classes": [4, 5],
            "numeric_type": "float64",
            "denominator_epsilon": 1e-6,
            "non_target_crs_component_rule": "May be metadata-retained without pixel read only when target-CRS components cover every AOI pixel covered by the group; otherwise fail SCL_ALIGNMENT_FAILED.",
            "overlap_rule": "Sort target-CRS components by MGRS tile and require finite NDVI equality within 1e-12 on overlap; conflicts fail closed.",
            "whole_asset_download_prohibited": True,
        },
        "coverage": {
            "minimum_unique_acquisitions_per_window": 3,
            "minimum_valid_observations_per_pixel_per_window": 3,
            "minimum_joint_aoi_fraction": 0.8,
            "joint_rule": "eligible_pre AND eligible_post",
        },
        "aggregation": {
            "sequence": ["per-acquisition calibrated NDVI", "per-pixel temporal median by window", "joint-eligible restriction", "AOI median PRE", "AOI median POST", "POST minus PRE"],
            "primary_tau": 0.03,
            "sensitivity_tau": [0.01, 0.02, 0.05],
            "delta_distribution": ["q05", "q25", "median", "q75", "q95", "IQR", "MAD"],
            "pixel_bootstrap_prohibited": True,
        },
        "replay": {
            "network_prohibited": True,
            "cache": "Unsigned AOI-level B04 DN, B08 DN, SCL and source-valid arrays plus radiometry metadata and canonical array hashes; NDVI and acquisition mosaics are recomputed during replay.",
            "required_equalities": ["canonical assessment bytes", "assessment SHA-256", "grouping-output SHA-256", "all cached array SHA-256 values"],
        },
        "security": {
            "scan_for": ["signed URL parameters", "authorization headers", "NaN/Infinity", "local machine paths"],
            "failure_resume_same_run_id": False,
            "result_driven_policy_change": False,
        },
        "stop_after": "STEP2B_V4",
    }


def serialise(spec: dict[str, Any]) -> bytes:
    return (json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate or check the frozen V4 runtime specification")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = serialise(build_spec())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    digest = hashlib.sha256(payload).hexdigest()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
            print("frozen V4 runtime spec is missing or has drifted", file=sys.stderr)
            return 1
        print(f"V4 runtime spec valid: {digest}")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(payload)
    print(f"Wrote {OUTPUT.relative_to(ROOT).as_posix()}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
