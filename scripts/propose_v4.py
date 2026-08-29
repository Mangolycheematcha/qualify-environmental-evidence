from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V3_PATH = ROOT / "policies" / "eop101132" / "step2b-proposed-policy.json"
V4_PATH = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"
V3_SHA256 = "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"
V4_POLICY_ID = "DEMO_QUALIFICATION_POLICY_EOP101132_V4"
V4_CONTRACT_VERSION = "0.5.0"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def proposal_bytes() -> bytes:
    v3_bytes = V3_PATH.read_bytes()
    if sha256_bytes(v3_bytes) != V3_SHA256:
        raise ValueError("immutable V3 policy bytes do not match the approved SHA-256")
    v3 = json.loads(v3_bytes)
    v4: dict[str, Any] = deepcopy(v3)
    v4["policy_schema_version"] = "1.3.0"
    v4["policy_id"] = V4_POLICY_ID
    v4["contract_version"] = V4_CONTRACT_VERSION
    v4["runtime_ready"] = False
    v4["approval_status"] = "PENDING_HUMAN_APPROVAL"
    v4["approval"] = {
        **v4["approval"],
        "status": "PENDING_HUMAN_APPROVAL",
        "sentinel_2_access_permitted": False,
        "approved_policy_sha256": None,
    }
    v4["bounded_claim"]["qualification_policy_version"] = V4_CONTRACT_VERSION
    v4["scene_admissibility"]["application_stage"] = (
        "BEFORE_ADMISSIBLE_ACQUISITION_GROUP_RESOURCE_COUNT_AND_COVERAGE"
    )
    v4["acquisition_grouping"] = {
        "rule_id": "SENTINEL2_METADATA_ONLY_ACQUISITION_GROUPING_V1",
        "independent_acquisition_identity": ["platform", "s2:datatake_id"],
        "required_identity_metadata": [
            "non-empty platform",
            "non-empty s2:datatake_id",
            "authoritative sensing datetime",
            "explicit MGRS tile identity for every spatial component",
        ],
        "identity_inference_prohibited": [
            "item ordering",
            "eo:cloud_cover",
            "filename similarity alone",
            "environmental values",
            "NDVI",
            "visual quality",
            "another item's metadata",
        ],
        "multiple_tile_rule": (
            "Multiple AOI-intersecting MGRS tiles from the same platform and datatake are retained as "
            "spatial components of one independent acquisition and counted once."
        ),
        "overlap_conflict_rule": (
            "Later mosaic and alignment must use the frozen target grid and a pre-registered deterministic "
            "overlap rule; unresolved component conflict fails closed."
        ),
        "processing_representation_identity": ["platform", "s2:datatake_id", "MGRS tile"],
        "processing_representation_priority": [
            "valid source and collection identity",
            "highest valid processing baseline",
            "most recent authoritative processing timestamp where present",
            "lexicographically smallest canonical item ID only when preceding metadata and canonical asset identities are equivalent",
        ],
        "equivalent_conflict_rule": (
            "Equivalent candidates with conflicting canonical asset identities fail closed with "
            "ACQUISITION_REPRESENTATION_AMBIGUOUS."
        ),
        "metadata_admissibility_before_resource_count": [
            "canonical source identity",
            "acquisition identity",
            "processing representation resolution",
            "mean solar zenith angle",
            "processing baseline",
            "B04, B08 and SCL asset presence",
            "required product and granule metadata presence",
            "B04 and B08 radiometry metadata resolvability",
        ],
        "metadata_inadmissible_rule": (
            "Retain every item and exclusion reason in inventory, but do not count a metadata-inadmissible "
            "acquisition group toward the raster-processing limit."
        ),
        "no_environmental_selection_fields": [
            "eo:cloud_cover",
            "AOI valid-pixel fraction",
            "SCL distribution",
            "NDVI",
            "visual appearance",
            "expected disposition",
            "closeness to a preferred result",
        ],
        "all_or_abstain_rule": (
            "Process all metadata-admissible acquisition groups when the count is within the frozen limit; "
            "if it exceeds the limit, abstain before raster access and never truncate, rank, or select a subset."
        ),
        "reason_codes": {
            "identity_unresolved": "ACQUISITION_IDENTITY_UNRESOLVED",
            "representation_ambiguous": "ACQUISITION_REPRESENTATION_AMBIGUOUS",
        },
        "rule_type": "POC_OPERATIONAL_METADATA_AND_RESOURCE_ACCOUNTING_RULE",
        "rationale": (
            "Raster-processing cost and independent-observation count attach to canonical acquisition groups, "
            "not raw STAC metadata rows. This engineering unit correction does not change the number 40, "
            "invalidate V3, or predict a V4 environmental result."
        ),
    }
    guards = v4["runtime_guards"]
    guards.pop("maximum_items_per_window", None)
    guards.pop("item_limit_reason_code", None)
    guards.pop("item_limit_rule", None)
    guards["raw_stac_items_per_window_max"] = 200
    guards["raw_stac_item_limit_stage"] = "AFTER_COMPLETE_STAC_PAGINATION_BEFORE_REMOTE_METADATA_ASSET_OR_RASTER_ACCESS"
    guards["raw_stac_item_limit_reason_codes"] = [
        "METADATA_INVENTORY_LIMIT_EXCEEDED",
        "RESOURCE_LIMIT_EXCEEDED",
    ]
    guards["raw_stac_item_limit_rule"] = (
        "If raw results exceed 200 in either window, preserve the complete count, do not truncate, and return "
        "ABSTAINED/INCONCLUSIVE before remote metadata-asset or raster access. This is a metadata inventory "
        "safety control, not a scientific threshold or scene-selection rule."
    )
    guards["independent_admissible_acquisition_groups_per_window_max"] = 40
    guards["acquisition_group_limit_stage"] = (
        "AFTER_COMPLETE_RAW_INVENTORY_GROUPING_REPRESENTATION_RESOLUTION_AND_METADATA_ADMISSIBILITY_BEFORE_RASTER_ACCESS"
    )
    guards["acquisition_group_limit_reason_code"] = "RESOURCE_LIMIT_EXCEEDED"
    guards["acquisition_group_limit_rule"] = (
        "If more than 40 independent metadata-admissible acquisition groups remain in either window, preserve "
        "all inventory and grouping records, do not truncate or rank, and return ABSTAINED/INCONCLUSIVE before "
        "B04, B08 or SCL raster access."
    )
    guards["resource_accounting_change"] = (
        "The numeric raster-processing limit remains 40. V4 changes only the unit from raw STAC item rows to "
        "independent metadata-admissible acquisition groups."
    )
    guards["metadata_only_before_raster_limit"] = True
    guards["environmental_selection_prohibited"] = True
    v4["qualification"]["qualification_policy_version"] = V4_CONTRACT_VERSION
    v4["qualification"]["operational_policy_id"] = V4_POLICY_ID
    return (json.dumps(v4, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify the deterministic pending V4 policy proposal.")
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in V4 bytes differ.")
    args = parser.parse_args()
    expected = proposal_bytes()
    policy_hash = sha256_bytes(expected)
    if args.check:
        if not V4_PATH.is_file() or V4_PATH.read_bytes() != expected:
            print("V4 policy proposal is missing or differs from deterministic generation", file=sys.stderr)
            return 1
        print(f"V4 policy proposal valid: {policy_hash}")
        return 0
    V4_PATH.write_bytes(expected)
    print(f"Wrote {V4_PATH.relative_to(ROOT).as_posix()}: {policy_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
