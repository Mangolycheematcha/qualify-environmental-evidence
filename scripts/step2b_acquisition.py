from __future__ import annotations

import math
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence


RAW_STAC_ITEMS_PER_WINDOW_MAX = 200
INDEPENDENT_ADMISSIBLE_ACQUISITION_GROUPS_PER_WINDOW_MAX = 40
REQUIRED_ASSET_KEYS = ("B04", "B08", "SCL", "product-metadata", "granule-metadata")
RADIOMETRY_ASSET_KEYS = ("B04", "B08")


class AcquisitionPolicyError(ValueError):
    def __init__(self, message: str, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _required_text(value: Any, field: str, reason_code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcquisitionPolicyError(f"{field} must be a non-empty string", reason_code)
    return value.strip()


def _finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _parse_datetime(value: Any, field: str, reason_code: str, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    text = _required_text(value, field, reason_code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcquisitionPolicyError(f"{field} is not an authoritative ISO-8601 datetime", reason_code) from exc
    if parsed.tzinfo is None:
        raise AcquisitionPolicyError(f"{field} must include an explicit timezone", reason_code)
    return parsed.astimezone(timezone.utc)


def _parse_baseline(value: Any) -> tuple[int, ...]:
    text = _required_text(value, "processing_baseline", "PROCESSING_BASELINE_UNRESOLVED")
    try:
        parts = tuple(int(part) for part in text.split("."))
    except ValueError as exc:
        raise AcquisitionPolicyError(
            "processing_baseline must contain dot-separated integers",
            "PROCESSING_BASELINE_UNRESOLVED",
        ) from exc
    if not parts:
        raise AcquisitionPolicyError("processing_baseline is empty", "PROCESSING_BASELINE_UNRESOLVED")
    return parts


def _canonical_asset_identities(item: dict[str, Any]) -> tuple[str, ...]:
    assets = item.get("assets")
    if not isinstance(assets, dict):
        raise AcquisitionPolicyError("assets must be an object", "RADIOMETRY_METADATA_UNRESOLVED")
    identities: list[str] = []
    for key in REQUIRED_ASSET_KEYS:
        identities.append(_required_text(assets.get(key), f"assets.{key}", "RADIOMETRY_METADATA_UNRESOLVED"))
    return tuple(identities)


def _radiometry_reasons(item: dict[str, Any]) -> list[str]:
    radiometry = item.get("radiometry")
    if not isinstance(radiometry, dict):
        return ["RADIOMETRY_METADATA_UNRESOLVED"]
    for asset_key in RADIOMETRY_ASSET_KEYS:
        record = radiometry.get(asset_key)
        if not isinstance(record, dict):
            return ["RADIOMETRY_METADATA_UNRESOLVED"]
        for field in ("scale", "offset", "quantification_value", "nodata"):
            if not _finite_number(record.get(field)):
                return ["RADIOMETRY_METADATA_UNRESOLVED"]
        if record["quantification_value"] <= 0:
            return ["RADIOMETRY_METADATA_UNRESOLVED"]
        if not isinstance(record.get("metadata_source"), str) or not record["metadata_source"].strip():
            return ["RADIOMETRY_METADATA_UNRESOLVED"]
        if record.get("cross_check") != "PASS":
            return ["RADIOMETRY_METADATA_UNRESOLVED"]
    return []


def _metadata_admissibility_reasons(item: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    try:
        _canonical_asset_identities(item)
    except AcquisitionPolicyError as exc:
        reasons.append(exc.reason_code)
    sza = item.get("mean_solar_zenith_angle")
    if not _finite_number(sza):
        reasons.append("SOLAR_GEOMETRY_METADATA_UNRESOLVED")
    elif sza > 70.0:
        reasons.append("SOLAR_GEOMETRY_OUT_OF_RANGE")
    reasons.extend(_radiometry_reasons(item))
    return list(dict.fromkeys(reasons))


def _normalise_item(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AcquisitionPolicyError("every STAC item must be an object", "ACQUISITION_IDENTITY_UNRESOLVED")
    item_id = _required_text(item.get("id"), "id", "ACQUISITION_IDENTITY_UNRESOLVED")
    collection = _required_text(item.get("collection"), "collection", "CANONICAL_IDENTIFIER_UNRESOLVED")
    if collection != "sentinel-2-l2a":
        raise AcquisitionPolicyError("collection is not sentinel-2-l2a", "CANONICAL_IDENTIFIER_UNRESOLVED")
    platform = _required_text(item.get("platform"), "platform", "ACQUISITION_IDENTITY_UNRESOLVED")
    datatake_id = _required_text(item.get("datatake_id"), "datatake_id", "ACQUISITION_IDENTITY_UNRESOLVED")
    sensing = _parse_datetime(item.get("datetime"), "datetime", "ACQUISITION_IDENTITY_UNRESOLVED")
    mgrs_tile = _required_text(item.get("mgrs_tile"), "mgrs_tile", "ACQUISITION_IDENTITY_UNRESOLVED")
    baseline_key = _parse_baseline(item.get("processing_baseline"))
    processing = _parse_datetime(
        item.get("processing_datetime"),
        "processing_datetime",
        "ACQUISITION_REPRESENTATION_AMBIGUOUS",
        optional=True,
    )
    return {
        "raw": deepcopy(item),
        "id": item_id,
        "collection": collection,
        "platform": platform,
        "datatake_id": datatake_id,
        "datetime": sensing,
        "mgrs_tile": mgrs_tile,
        "processing_baseline": item["processing_baseline"],
        "baseline_key": baseline_key,
        "processing_datetime": processing,
        "acquisition_key": (platform, datatake_id),
        "component_key": (platform, datatake_id, mgrs_tile),
    }


def _ensure_identity_consistency(items: Sequence[dict[str, Any]]) -> None:
    by_item_id: dict[str, tuple[Any, ...]] = {}
    by_acquisition: dict[tuple[str, str], datetime] = {}
    for item in items:
        identity = (*item["acquisition_key"], item["mgrs_tile"], item["datetime"])
        previous_identity = by_item_id.setdefault(item["id"], identity)
        if previous_identity != identity:
            raise AcquisitionPolicyError(
                f"item {item['id']} has contradictory acquisition identity metadata",
                "ACQUISITION_IDENTITY_UNRESOLVED",
            )
        previous_datetime = by_acquisition.setdefault(item["acquisition_key"], item["datetime"])
        if previous_datetime != item["datetime"]:
            raise AcquisitionPolicyError(
                f"acquisition {item['acquisition_key']} has contradictory sensing datetimes",
                "ACQUISITION_IDENTITY_UNRESOLVED",
            )


def _resolve_component(candidates: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    highest_baseline = max(item["baseline_key"] for item in candidates)
    baseline_candidates = [item for item in candidates if item["baseline_key"] == highest_baseline]
    present_times = [item["processing_datetime"] for item in baseline_candidates if item["processing_datetime"] is not None]
    if present_times:
        latest = max(present_times)
        finalists = [item for item in baseline_candidates if item["processing_datetime"] == latest]
    else:
        finalists = baseline_candidates

    if len(finalists) > 1:
        identities = {_canonical_asset_identities(item["raw"]) for item in finalists}
        if len(identities) != 1:
            key = finalists[0]["component_key"]
            raise AcquisitionPolicyError(
                f"component {key} has equivalent processing representations with conflicting canonical assets",
                "ACQUISITION_REPRESENTATION_AMBIGUOUS",
            )
    selected = min(finalists, key=lambda item: item["id"])
    excluded = [item for item in candidates if item is not selected]
    return selected, excluded


def evaluate_window_metadata(
    raw_items: Sequence[dict[str, Any]],
    *,
    raw_limit: int = RAW_STAC_ITEMS_PER_WINDOW_MAX,
    acquisition_limit: int = INDEPENDENT_ADMISSIBLE_ACQUISITION_GROUPS_PER_WINDOW_MAX,
) -> dict[str, Any]:
    if isinstance(raw_items, (str, bytes)) or not isinstance(raw_items, Sequence):
        raise AcquisitionPolicyError("raw_items must be a finite sequence", "REQUIRED_FIELD_MISSING")
    if len(raw_items) > raw_limit:
        return {
            "status": "ABSTAINED",
            "reason_codes": ["METADATA_INVENTORY_LIMIT_EXCEEDED", "RESOURCE_LIMIT_EXCEEDED"],
            "raw_item_count": len(raw_items),
            "raw_item_limit": raw_limit,
            "inventory": [deepcopy(item) for item in raw_items],
            "acquisition_groups": [],
            "admissible_acquisition_group_count": None,
            "acquisition_group_limit": acquisition_limit,
            "raster_access_permitted": False,
            "truncated": False,
        }

    normalised = [_normalise_item(item) for item in raw_items]
    _ensure_identity_consistency(normalised)
    components: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item in normalised:
        components.setdefault(item["component_key"], []).append(item)

    inventory_by_id: dict[str, dict[str, Any]] = {}
    selected_components: list[dict[str, Any]] = []
    for key in sorted(components):
        selected, excluded = _resolve_component(components[key])
        selected_components.append(selected)
        reasons = _metadata_admissibility_reasons(selected["raw"])
        inventory_by_id[selected["id"]] = {
            **deepcopy(selected["raw"]),
            "representation_status": "SELECTED_CANONICAL_REPRESENTATION",
            "metadata_admissible": not reasons,
            "exclusion_reasons": reasons,
        }
        for item in excluded:
            inventory_by_id[item["id"]] = {
                **deepcopy(item["raw"]),
                "representation_status": "EXCLUDED_PROCESSING_REPRESENTATION",
                "metadata_admissible": False,
                "exclusion_reasons": ["SUPERSEDED_PROCESSING_REPRESENTATION"],
            }

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in selected_components:
        grouped.setdefault(item["acquisition_key"], []).append(item)

    acquisition_groups: list[dict[str, Any]] = []
    for acquisition_key in sorted(grouped):
        component_items = sorted(grouped[acquisition_key], key=lambda item: item["mgrs_tile"])
        component_records = [inventory_by_id[item["id"]] for item in component_items]
        reasons = list(dict.fromkeys(reason for record in component_records for reason in record["exclusion_reasons"]))
        acquisition_groups.append(
            {
                "platform": acquisition_key[0],
                "datatake_id": acquisition_key[1],
                "sensing_datetime": component_items[0]["raw"]["datetime"],
                "component_item_ids": [item["id"] for item in component_items],
                "mgrs_tiles": [item["mgrs_tile"] for item in component_items],
                "metadata_admissible": not reasons,
                "exclusion_reasons": reasons,
            }
        )

    admissible_count = sum(group["metadata_admissible"] for group in acquisition_groups)
    limit_exceeded = admissible_count > acquisition_limit
    return {
        "status": "ABSTAINED" if limit_exceeded else "READY_FOR_RASTER_LIMITED_PROCESSING",
        "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"] if limit_exceeded else [],
        "raw_item_count": len(raw_items),
        "raw_item_limit": raw_limit,
        "inventory": [inventory_by_id[item_id] for item_id in sorted(inventory_by_id)],
        "acquisition_groups": acquisition_groups,
        "admissible_acquisition_group_count": admissible_count,
        "acquisition_group_limit": acquisition_limit,
        "raster_access_permitted": not limit_exceeded,
        "truncated": False,
    }


def canonical_group_identity(group: dict[str, Any]) -> tuple[str, str]:
    return group["platform"], group["datatake_id"]


def selected_item_ids(result: dict[str, Any]) -> list[str]:
    return sorted(
        item["id"]
        for item in result["inventory"]
        if item.get("representation_status") == "SELECTED_CANONICAL_REPRESENTATION"
    )


def forbidden_environmental_selection_fields() -> tuple[str, ...]:
    return ("eo:cloud_cover", "aoi_valid_pixel_fraction", "scl_distribution", "ndvi", "raster_values")
