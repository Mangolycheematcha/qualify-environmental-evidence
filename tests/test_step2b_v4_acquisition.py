from __future__ import annotations

import hashlib
import json
import socket
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import step2b_acquisition as acquisition
from scripts import step2b_offline


ROOT = Path(__file__).resolve().parents[1]
V3_POLICY = ROOT / "policies" / "eop101132" / "step2b-proposed-policy.json"
V4_POLICY = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"
CURATED = ROOT / "examples" / "eop101132-v3-abstained"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item(
    index: int,
    *,
    datatake: str | None = None,
    tile: str = "54HYE",
    baseline: str = "05.11",
    processing_datetime: str | None = "2025-09-01T00:00:00Z",
) -> dict:
    datatake_id = datatake or f"DT-{index:03d}"
    item_id = f"ITEM-{index:03d}-{tile}-{baseline}"
    return {
        "id": item_id,
        "collection": "sentinel-2-l2a",
        "platform": "Sentinel-2A",
        "datatake_id": datatake_id,
        "datetime": f"2025-06-{index % 28 + 1:02d}T00:00:00Z",
        "mgrs_tile": tile,
        "processing_baseline": baseline,
        "processing_datetime": processing_datetime,
        "eo:cloud_cover": float(index % 100),
        "mean_solar_zenith_angle": 60.0,
        "assets": {
            "B04": f"https://example.test/{item_id}/B04.tif",
            "B08": f"https://example.test/{item_id}/B08.tif",
            "SCL": f"https://example.test/{item_id}/SCL.tif",
            "product-metadata": f"https://example.test/{item_id}/product.xml",
            "granule-metadata": f"https://example.test/{item_id}/granule.xml",
        },
        "radiometry": {
            band: {
                "scale": 0.0001,
                "offset": -0.1,
                "quantification_value": 10000.0,
                "nodata": 0.0,
                "metadata_source": f"{item_id}/product.xml",
                "cross_check": "PASS",
            }
            for band in ("B04", "B08")
        },
    }


def independent_items(count: int) -> list[dict]:
    return [item(index) for index in range(count)]


def test_44_raw_items_grouped_into_22_acquisitions_do_not_hit_40_limit():
    items = []
    for index in range(22):
        datatake = f"DT-{index:03d}"
        first = item(index, datatake=datatake, tile="54HYE")
        second = item(index, datatake=datatake, tile="55HBV")
        second["datetime"] = first["datetime"]
        items.extend((first, second))
    result = acquisition.evaluate_window_metadata(items)
    assert result["raw_item_count"] == 44
    assert result["admissible_acquisition_group_count"] == 22
    assert result["status"] == "READY_FOR_RASTER_LIMITED_PROCESSING"


def test_44_independent_admissible_acquisitions_hit_40_limit():
    result = acquisition.evaluate_window_metadata(independent_items(44))
    assert result["admissible_acquisition_group_count"] == 44
    assert result["status"] == "ABSTAINED"
    assert result["reason_codes"] == ["RESOURCE_LIMIT_EXCEEDED"]
    assert result["raster_access_permitted"] is False


def test_multiple_tiles_from_one_datatake_count_once():
    first = item(1, datatake="SAME", tile="54HYE")
    second = item(1, datatake="SAME", tile="55HBV")
    second["datetime"] = first["datetime"]
    result = acquisition.evaluate_window_metadata([first, second])
    assert result["admissible_acquisition_group_count"] == 1
    assert result["acquisition_groups"][0]["mgrs_tiles"] == ["54HYE", "55HBV"]


def test_multiple_processing_representations_count_once_after_resolution():
    old = item(1, datatake="SAME", baseline="02.12", processing_datetime="2021-01-01T00:00:00Z")
    new = item(1, datatake="SAME", baseline="05.11", processing_datetime="2025-01-01T00:00:00Z")
    result = acquisition.evaluate_window_metadata([old, new])
    assert result["admissible_acquisition_group_count"] == 1
    assert acquisition.selected_item_ids(result) == [new["id"]]
    excluded = next(record for record in result["inventory"] if record["id"] == old["id"])
    assert excluded["exclusion_reasons"] == ["SUPERSEDED_PROCESSING_REPRESENTATION"]


def test_input_order_does_not_change_grouping_or_selection():
    old = item(1, datatake="SAME", baseline="02.12", processing_datetime="2021-01-01T00:00:00Z")
    new = item(1, datatake="SAME", baseline="05.11", processing_datetime="2025-01-01T00:00:00Z")
    forward = acquisition.evaluate_window_metadata([old, new])
    reverse = acquisition.evaluate_window_metadata([new, old])
    assert forward["acquisition_groups"] == reverse["acquisition_groups"]
    assert acquisition.selected_item_ids(forward) == acquisition.selected_item_ids(reverse)


def test_cloud_cover_cannot_affect_grouping_or_selection():
    old = item(1, datatake="SAME", baseline="02.12", processing_datetime="2021-01-01T00:00:00Z")
    new = item(1, datatake="SAME", baseline="05.11", processing_datetime="2025-01-01T00:00:00Z")
    old["eo:cloud_cover"], new["eo:cloud_cover"] = 0.0, 100.0
    first = acquisition.evaluate_window_metadata([old, new])
    old["eo:cloud_cover"], new["eo:cloud_cover"] = 100.0, 0.0
    second = acquisition.evaluate_window_metadata([old, new])
    assert acquisition.selected_item_ids(first) == acquisition.selected_item_ids(second) == [new["id"]]


def test_ndvi_and_raster_values_are_ignored_by_grouping():
    base = independent_items(2)
    decorated = deepcopy(base)
    decorated[0]["ndvi"] = 0.99
    decorated[0]["raster_values"] = [1, 2, 3]
    decorated[1]["aoi_valid_pixel_fraction"] = 0.01
    assert acquisition.evaluate_window_metadata(base)["acquisition_groups"] == acquisition.evaluate_window_metadata(decorated)["acquisition_groups"]
    assert "ndvi" in acquisition.forbidden_environmental_selection_fields()


def test_missing_datatake_identity_fails_closed():
    candidate = item(1)
    candidate["datatake_id"] = None
    with pytest.raises(acquisition.AcquisitionPolicyError, match="datatake_id") as exc:
        acquisition.evaluate_window_metadata([candidate])
    assert exc.value.reason_code == "ACQUISITION_IDENTITY_UNRESOLVED"


def test_conflicting_acquisition_identity_fails_closed():
    first = item(1, datatake="SAME", tile="54HYE")
    second = item(2, datatake="SAME", tile="55HBV")
    with pytest.raises(acquisition.AcquisitionPolicyError, match="contradictory sensing") as exc:
        acquisition.evaluate_window_metadata([first, second])
    assert exc.value.reason_code == "ACQUISITION_IDENTITY_UNRESOLVED"


def test_conflicting_equivalent_processing_representations_fail_closed():
    first = item(1, datatake="SAME")
    second = deepcopy(first)
    second["id"] = "ITEM-EQUIVALENT-B"
    second["assets"]["B04"] = "https://example.test/conflicting/B04.tif"
    with pytest.raises(acquisition.AcquisitionPolicyError, match="conflicting canonical assets") as exc:
        acquisition.evaluate_window_metadata([first, second])
    assert exc.value.reason_code == "ACQUISITION_REPRESENTATION_AMBIGUOUS"


def test_more_than_200_raw_items_hits_metadata_inventory_limit_without_truncation():
    result = acquisition.evaluate_window_metadata(independent_items(201))
    assert result["raw_item_count"] == 201
    assert len(result["inventory"]) == 201
    assert result["truncated"] is False
    assert result["reason_codes"] == ["METADATA_INVENTORY_LIMIT_EXCEEDED", "RESOURCE_LIMIT_EXCEEDED"]
    assert result["admissible_acquisition_group_count"] is None


def test_exactly_200_raw_items_proceed_to_grouping():
    result = acquisition.evaluate_window_metadata(independent_items(200))
    assert result["raw_item_count"] == 200
    assert len(result["acquisition_groups"]) == 200
    assert "METADATA_INVENTORY_LIMIT_EXCEEDED" not in result["reason_codes"]


def test_exactly_40_admissible_acquisition_groups_are_allowed():
    result = acquisition.evaluate_window_metadata(independent_items(40))
    assert result["admissible_acquisition_group_count"] == 40
    assert result["raster_access_permitted"] is True


def test_more_than_40_admissible_groups_abstains_before_raster_access():
    result = acquisition.evaluate_window_metadata(independent_items(41))
    assert result["status"] == "ABSTAINED"
    assert result["raster_access_permitted"] is False
    assert result["truncated"] is False


def test_metadata_inadmissible_items_remain_but_do_not_count():
    valid, invalid = independent_items(2)
    invalid["mean_solar_zenith_angle"] = 71.0
    result = acquisition.evaluate_window_metadata([valid, invalid])
    assert len(result["inventory"]) == 2
    assert result["admissible_acquisition_group_count"] == 1
    record = next(entry for entry in result["inventory"] if entry["id"] == invalid["id"])
    assert record["metadata_admissible"] is False
    assert record["exclusion_reasons"] == ["SOLAR_GEOMETRY_OUT_OF_RANGE"]


def test_v3_policy_assessment_and_provenance_hashes_remain_immutable():
    assert sha256(V3_POLICY) == "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"
    assert sha256(CURATED / "assessment.json") == "f46822f29ef00c511fdc340c3adf240b5255aa6aec9e9a32e0dd692d1217dcf9"
    assert sha256(CURATED / "provenance-manifest.json") == "69d3e3c0b054dc9f4ba2ac9610332a78e6ed104b53e115cb5539be39f434e407"


def test_v4_cannot_use_v3_detached_approval():
    policy_bytes = V4_POLICY.read_bytes()
    policy = json.loads(policy_bytes)
    v3_approval = {
        "approval_record_version": "1.0.0",
        "policy_id": "DEMO_QUALIFICATION_POLICY_EOP101132_V3",
        "approved_policy_sha256": "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59",
        "mode": "QUALIFICATION",
        "approval_statement": "批准 QUALIFICATION 4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59",
        "approval_timestamp_utc": "2026-08-29T00:00:00Z",
        "approver_role": "HUMAN_PROJECT_OWNER",
        "runtime_scope": "ONE_PRIMARY_EOP101132_RUN",
        "policy_mutation_permitted": False,
    }
    with pytest.raises(step2b_offline.OfflineContractError):
        step2b_offline.validate_detached_approval(policy, policy_bytes, v3_approval)


def test_v4_remains_pending_and_not_runtime_ready():
    policy = json.loads(V4_POLICY.read_text(encoding="utf-8"))
    assert policy["policy_id"] == "DEMO_QUALIFICATION_POLICY_EOP101132_V4"
    assert policy["runtime_ready"] is False
    assert policy["approval_status"] == "PENDING_HUMAN_APPROVAL"
    assert policy["approval"]["approved_policy_sha256"] is None
    assert not (ROOT / "approvals" / "eop101132-v4.json").exists()


def test_offline_grouping_does_not_open_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", blocked)
    result = acquisition.evaluate_window_metadata(independent_items(3))
    assert result["status"] == "READY_FOR_RASTER_LIMITED_PROCESSING"


def test_readme_and_packaged_v4_resources_are_present():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "No licence has yet been selected. Private repository only." in readme
    assert "Real raster and NDVI path | Not yet executed" in readme
    assert (ROOT / "skill" / "qualify-environmental-evidence" / "policies" / "eop101132" / "step2b-proposed-policy-v4.json").is_file()
    assert (ROOT / "skill" / "qualify-environmental-evidence" / "scripts" / "step2b_acquisition.py").is_file()
