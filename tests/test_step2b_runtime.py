from __future__ import annotations

import copy

import pytest

from scripts import step2b_runtime as runtime


def test_runtime_policy_hash_and_approval_statement_are_exact():
    assert runtime.sha256_file(runtime.POLICY_PATH) == runtime.APPROVED_POLICY_SHA256
    assert runtime.APPROVAL_STATEMENT == f"批准 QUALIFICATION {runtime.APPROVED_POLICY_SHA256}"


def test_network_allowlist_rejects_unrelated_and_credentialed_hosts():
    assert runtime._safe_host("https://cer.gov.au/example") == "cer.gov.au"
    with pytest.raises(runtime.RuntimeFailure, match="not allowlisted"):
        runtime._safe_host("https://example.com/unrelated")
    with pytest.raises(runtime.RuntimeFailure, match="not allowlisted"):
        runtime._safe_host("https://user:secret@cer.gov.au/example")


def test_stac_deduplication_is_deterministic_and_conflicts_fail_closed():
    item = {"collection": "sentinel-2-l2a", "id": "ITEM-1", "properties": {"datetime": "2025-01-01T00:00:00Z"}}
    result, duplicates = runtime._deduplicate_items([item, copy.deepcopy(item)])
    assert result == [item]
    assert duplicates == 1
    changed = copy.deepcopy(item)
    changed["properties"]["datetime"] = "2025-01-02T00:00:00Z"
    with pytest.raises(runtime.RuntimeFailure, match="conflicting duplicate"):
        runtime._deduplicate_items([item, changed])


def test_closed_boundary_area_and_geojson_are_deterministic():
    ring = [[141.0, -36.0], [141.001, -36.0], [141.001, -36.001], [141.0, -36.001], [141.0, -36.0]]
    assert abs(runtime.signed_area(ring)) > 0
    assert runtime.boundary_geojson([[ring]]) == {"type": "MultiPolygon", "coordinates": [[[ring[0], ring[1], ring[2], ring[3], ring[4]]]]}


def test_resource_limit_assessment_is_canonical_and_has_no_measurement():
    assessment = runtime._resource_limit_assessment("RUN-1", "urn:test:manifest")
    assert assessment["execution_status"] == "ABSTAINED"
    assert assessment["evidence_disposition"] == "INCONCLUSIVE"
    assert assessment["reason_codes"] == ["RESOURCE_LIMIT_EXCEEDED"]
    assert assessment["observations"] is None
    assert runtime.canonical_bytes(assessment) == runtime.canonical_bytes(copy.deepcopy(assessment))


def test_canonical_json_rejects_non_finite_values():
    with pytest.raises(ValueError):
        runtime.canonical_bytes({"value": float("nan")})
