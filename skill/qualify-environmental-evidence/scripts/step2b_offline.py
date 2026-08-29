from __future__ import annotations

import math
import hashlib
import statistics
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Sequence


PRIMARY_POLICY_ID = "POC_OPERATIONAL_INDIFFERENCE_BAND_V1"
PRIMARY_TAU = Decimal("0.03")
SENSITIVITY_TAUS = (Decimal("0.01"), Decimal("0.02"), Decimal("0.05"))
COMPARISON_SEMANTICS = "CANONICAL_DECIMAL_FROM_JSON_NUMBER_V1"
RADIOMETRY_REASON = "RADIOMETRY_METADATA_UNRESOLVED"
RESOURCE_LIMIT_REASON = "RESOURCE_LIMIT_EXCEEDED"
SOLAR_GEOMETRY_MAX_DEGREES = 70.0
SOLAR_GEOMETRY_OUT_OF_RANGE = "SOLAR_GEOMETRY_OUT_OF_RANGE"
SOLAR_GEOMETRY_METADATA_UNRESOLVED = "SOLAR_GEOMETRY_METADATA_UNRESOLVED"


class OfflineContractError(ValueError):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class Radiometry:
    item_id: str
    acquisition_datetime: str
    platform: str
    processing_baseline: str
    asset_key: str
    canonical_asset_identity: str
    retrieval_uri: str | None
    scale: float
    offset: float
    quantification_value: float
    nodata: float
    metadata_source: str
    cross_check: str


@dataclass(frozen=True)
class SolarGeometryRecord:
    window: str
    item_id: str
    acquisition_datetime: str
    platform: str
    datatake_id: str
    mean_solar_zenith_angle: float | None
    metadata_source: str | None
    cross_check: str
    admissible: bool
    exclusion_reason: str | None
    processing_baseline: str


@dataclass(frozen=True)
class RunIdentity:
    approved_policy_sha256: str
    calculated_policy_sha256_at_start: str
    input_sha256_at_start: str


def canonical_decimal(value: int | float | str | Decimal, field: str) -> Decimal:
    if isinstance(value, bool):
        raise OfflineContractError(f"{field} must be a finite JSON number", "DETERMINISTIC_PROCESSING_ERROR")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OfflineContractError(f"{field} must be a finite JSON number", "DETERMINISTIC_PROCESSING_ERROR") from exc
    if not result.is_finite():
        raise OfflineContractError(f"{field} must be finite", "DETERMINISTIC_PROCESSING_ERROR")
    return result


def _required_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise OfflineContractError(f"{context}: missing {key}", RADIOMETRY_REASON)
    return value


def _required_number(mapping: dict[str, Any], key: str, context: str) -> float:
    if key not in mapping:
        raise OfflineContractError(f"{context}: missing {key}", RADIOMETRY_REASON)
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise OfflineContractError(f"{context}: {key} must be finite", RADIOMETRY_REASON)
    return float(value)


def _required_solar_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise OfflineContractError(f"{context}: missing {key}", SOLAR_GEOMETRY_METADATA_UNRESOLVED)
    return value


def resolve_solar_geometry(item: dict[str, Any], window: str) -> SolarGeometryRecord:
    """Resolve one item's SZA from explicit metadata only; no geographic or date fallback exists."""
    if window not in {"PRE", "POST"}:
        raise OfflineContractError("window must be PRE or POST", "DETERMINISTIC_PROCESSING_ERROR")
    item_id = _required_solar_text(item, "id", "item")
    context = f"item {item_id}"
    acquisition = _required_solar_text(item, "datetime", context)
    platform = _required_solar_text(item, "platform", context)
    datatake_id = _required_solar_text(item, "datatake_id", context)
    baseline = _required_solar_text(item, "processing_baseline", context)
    metadata_source = item.get("solar_geometry_metadata_source")
    cross_check = item.get("solar_geometry_cross_check")
    raw_value = item.get("mean_solar_zenith_angle")
    if raw_value is None:
        return SolarGeometryRecord(
            window, item_id, acquisition, platform, datatake_id, None,
            metadata_source if isinstance(metadata_source, str) and metadata_source else None,
            "MISSING", False, SOLAR_GEOMETRY_METADATA_UNRESOLVED, baseline,
        )
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)) or not math.isfinite(raw_value):
        return SolarGeometryRecord(
            window, item_id, acquisition, platform, datatake_id, None,
            metadata_source if isinstance(metadata_source, str) and metadata_source else None,
            "UNPARSEABLE", False, SOLAR_GEOMETRY_METADATA_UNRESOLVED, baseline,
        )
    value = float(raw_value)
    if not isinstance(metadata_source, str) or not metadata_source or cross_check != "PASS":
        return SolarGeometryRecord(
            window, item_id, acquisition, platform, datatake_id, value,
            metadata_source if isinstance(metadata_source, str) and metadata_source else None,
            "FAIL", False, SOLAR_GEOMETRY_METADATA_UNRESOLVED, baseline,
        )
    if value > SOLAR_GEOMETRY_MAX_DEGREES:
        return SolarGeometryRecord(
            window, item_id, acquisition, platform, datatake_id, value,
            metadata_source, "PASS", False, SOLAR_GEOMETRY_OUT_OF_RANGE, baseline,
        )
    return SolarGeometryRecord(
        window, item_id, acquisition, platform, datatake_id, value,
        metadata_source, "PASS", True, None, baseline,
    )


def partition_items_by_solar_geometry(items: Sequence[dict[str, Any]], window: str) -> dict[str, Any]:
    records = [resolve_solar_geometry(item, window) for item in items]
    admitted = [item for item, record in zip(items, records, strict=True) if record.admissible]
    return {"records": [asdict(record) for record in records], "admitted_items": admitted}


def _solar_population_summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    values = [record["mean_solar_zenith_angle"] for record in records if record["mean_solar_zenith_angle"] is not None]
    if values:
        distribution = descriptive_distribution(values)
        statistics_fields = {
            "minimum": min(values),
            "q25": distribution["q25"],
            "median": distribution["median"],
            "q75": distribution["q75"],
            "maximum": max(values),
        }
    else:
        statistics_fields = {key: None for key in ("minimum", "q25", "median", "q75", "maximum")}
    return {
        "count": len(records),
        **statistics_fields,
        "missing_count": sum(record["mean_solar_zenith_angle"] is None for record in records),
        "excluded_above_threshold_count": sum(record["exclusion_reason"] == SOLAR_GEOMETRY_OUT_OF_RANGE for record in records),
        "excluded_unresolved_count": sum(record["exclusion_reason"] == SOLAR_GEOMETRY_METADATA_UNRESOLVED for record in records),
    }


def solar_geometry_window_summary(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    admitted = [record for record in records if record["admissible"]]
    return {"discovered": _solar_population_summary(records), "admitted": _solar_population_summary(admitted)}


def solar_geometry_diagnostic(pre_records: Sequence[dict[str, Any]], post_records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    pre = solar_geometry_window_summary(pre_records)
    post = solar_geometry_window_summary(post_records)
    pre_median = pre["admitted"]["median"]
    post_median = post["admitted"]["median"]
    difference = None if pre_median is None or post_median is None else post_median - pre_median
    return {
        "pre_window": pre,
        "post_window": post,
        "post_minus_pre_median_degrees": difference,
        "diagnostic_only": True,
    }


def admissible_measurement_values(items: Sequence[dict[str, Any]], window: str, field: str) -> list[Any]:
    partition = partition_items_by_solar_geometry(items, window)
    return [item[field] for item in partition["admitted_items"] if field in item]


def evaluate_window_gate(
    items: Sequence[dict[str, Any]],
    window: str,
    admissible_valid_pixel_fraction: float,
    minimum_unique_acquisitions: int = 3,
    minimum_valid_fraction: float = 0.8,
) -> dict[str, Any]:
    partition = partition_items_by_solar_geometry(items, window)
    admitted = partition["admitted_items"]
    identities = sorted({item["datatake_id"] for item in admitted})
    passes = len(identities) >= minimum_unique_acquisitions and admissible_valid_pixel_fraction >= minimum_valid_fraction
    return {
        "execution_status": "COMPLETED" if passes else "ABSTAINED",
        "evidence_disposition": None if passes else "INCONCLUSIVE",
        "reason_codes": [] if passes else ["VALID_OBSERVATION_COVERAGE_LOW"],
        "independent_acquisition_count": len(identities),
        "admitted_item_ids": [item["id"] for item in admitted],
        "scene_records": partition["records"],
    }


def canonical_policy_sha256(policy_bytes: bytes) -> str:
    if not isinstance(policy_bytes, bytes) or not policy_bytes:
        raise OfflineContractError("canonical policy bytes are required", "PROVENANCE_HASH_MISMATCH")
    return hashlib.sha256(policy_bytes).hexdigest()


def require_approved_policy_for_runtime(
    policy: dict[str, Any], approved_policy_sha256: str | None, policy_bytes: bytes
) -> str:
    if (
        policy.get("approval_status") != "APPROVED"
        or policy.get("runtime_ready") is not True
        or policy.get("approval", {}).get("sentinel_2_access_permitted") is not True
    ):
        raise OfflineContractError("policy is not approved and runtime-ready; network access is prohibited", "RUNTIME_SPECIFICATION_NOT_FROZEN")
    if not isinstance(approved_policy_sha256, str) or len(approved_policy_sha256) != 64:
        raise OfflineContractError("an explicit approved policy SHA-256 is required", "PROVENANCE_HASH_MISMATCH")
    calculated = canonical_policy_sha256(policy_bytes)
    if calculated != approved_policy_sha256:
        raise OfflineContractError("local policy SHA-256 does not match the approved hash", "PROVENANCE_HASH_MISMATCH")
    return calculated


def validate_detached_approval(
    policy: dict[str, Any], policy_bytes: bytes, approval: dict[str, Any]
) -> str:
    calculated = canonical_policy_sha256(policy_bytes)
    expected_statement = f"批准 QUALIFICATION {calculated}"
    expected = {
        "approval_record_version": "1.0.0",
        "policy_id": policy.get("policy_id"),
        "approved_policy_sha256": calculated,
        "mode": "QUALIFICATION",
        "approval_statement": expected_statement,
        "approver_role": "HUMAN_PROJECT_OWNER",
        "runtime_scope": "ONE_PRIMARY_EOP101132_RUN",
        "policy_mutation_permitted": False,
    }
    for field, value in expected.items():
        if approval.get(field) != value:
            raise OfflineContractError(
                f"detached approval {field} does not match the approved policy",
                "PROVENANCE_HASH_MISMATCH",
            )
    timestamp = approval.get("approval_timestamp_utc")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise OfflineContractError(
            "detached approval requires a UTC approval timestamp",
            "PROVENANCE_HASH_MISMATCH",
        )
    if policy.get("contract_version") not in {"0.4.0", "0.5.0"}:
        raise OfflineContractError("detached approval contract version mismatch", "PROVENANCE_HASH_MISMATCH")
    return calculated


def freeze_run_identity(
    policy: dict[str, Any], approved_policy_sha256: str, policy_bytes: bytes, input_sha256: str
) -> RunIdentity:
    calculated = require_approved_policy_for_runtime(policy, approved_policy_sha256, policy_bytes)
    if not isinstance(input_sha256, str) or len(input_sha256) != 64:
        raise OfflineContractError("a canonical input SHA-256 is required", "PROVENANCE_HASH_MISMATCH")
    return RunIdentity(approved_policy_sha256, calculated, input_sha256)


def verify_run_identity(identity: RunIdentity, policy_bytes: bytes, input_sha256: str) -> None:
    if canonical_policy_sha256(policy_bytes) != identity.calculated_policy_sha256_at_start:
        raise OfflineContractError("policy mutated after run start", "PROVENANCE_HASH_MISMATCH")
    if input_sha256 != identity.input_sha256_at_start:
        raise OfflineContractError("input mutated after run start", "PROVENANCE_HASH_MISMATCH")


def require_new_run_for_policy(
    existing_run_id: str,
    existing_policy_sha256: str,
    proposed_run_id: str,
    proposed_policy_sha256: str,
) -> None:
    if existing_policy_sha256 != proposed_policy_sha256 and existing_run_id == proposed_run_id:
        raise OfflineContractError(
            "a future policy requires a new run ID and cannot overwrite the original run",
            "PROVENANCE_HASH_MISMATCH",
        )


def resolve_item_asset_radiometry(item: dict[str, Any], asset_key: str) -> Radiometry:
    """Resolve calibration from this item and this band only; no date-based fallback exists."""
    if asset_key not in {"B04", "B08"}:
        raise OfflineContractError(f"unsupported reflectance asset {asset_key!r}", RADIOMETRY_REASON)
    item_id = _required_text(item, "id", "item")
    acquisition = _required_text(item, "datetime", f"item {item_id}")
    platform = _required_text(item, "platform", f"item {item_id}")
    baseline = _required_text(item, "processing_baseline", f"item {item_id}")
    assets = item.get("assets")
    if not isinstance(assets, dict) or not isinstance(assets.get(asset_key), dict):
        raise OfflineContractError(f"item {item_id}: missing asset {asset_key}", RADIOMETRY_REASON)
    asset = assets[asset_key]
    identity = _required_text(asset, "canonical_identity", f"item {item_id} asset {asset_key}")
    retrieval_uri = asset.get("retrieval_uri")
    if retrieval_uri is not None and (not isinstance(retrieval_uri, str) or not retrieval_uri):
        raise OfflineContractError(f"item {item_id} asset {asset_key}: invalid retrieval_uri", RADIOMETRY_REASON)
    raster = asset.get("raster")
    if not isinstance(raster, dict):
        raise OfflineContractError(f"item {item_id} asset {asset_key}: missing raster metadata", RADIOMETRY_REASON)
    scale = _required_number(raster, "scale", f"item {item_id} asset {asset_key} raster")
    offset = _required_number(raster, "offset", f"item {item_id} asset {asset_key} raster")
    raster_nodata = _required_number(raster, "nodata", f"item {item_id} asset {asset_key} raster")

    product = item.get("product_metadata")
    if not isinstance(product, dict):
        raise OfflineContractError(f"item {item_id}: missing product_metadata", RADIOMETRY_REASON)
    quantification = _required_number(product, "quantification_value", f"item {item_id} product metadata")
    product_nodata = _required_number(product, "nodata", f"item {item_id} product metadata")
    offsets = product.get("boa_add_offset")
    if not isinstance(offsets, dict):
        raise OfflineContractError(f"item {item_id}: missing BOA_ADD_OFFSET mapping", RADIOMETRY_REASON)
    band_offset_dn = _required_number(offsets, asset_key, f"item {item_id} BOA_ADD_OFFSET")
    if quantification <= 0:
        raise OfflineContractError(f"item {item_id}: quantification_value must be positive", RADIOMETRY_REASON)
    expected_scale = 1.0 / quantification
    expected_offset = band_offset_dn / quantification
    if not math.isclose(scale, expected_scale, rel_tol=0.0, abs_tol=1e-12):
        raise OfflineContractError(
            f"item {item_id} asset {asset_key}: asset/product scale metadata contradicts quantification value",
            RADIOMETRY_REASON,
        )
    if not math.isclose(offset, expected_offset, rel_tol=0.0, abs_tol=1e-12):
        raise OfflineContractError(
            f"item {item_id} asset {asset_key}: asset/product offset metadata contradicts BOA_ADD_OFFSET",
            RADIOMETRY_REASON,
        )
    if raster_nodata != product_nodata:
        raise OfflineContractError(
            f"item {item_id} asset {asset_key}: asset/product nodata metadata contradicts",
            RADIOMETRY_REASON,
        )
    return Radiometry(
        item_id=item_id,
        acquisition_datetime=acquisition,
        platform=platform,
        processing_baseline=baseline,
        asset_key=asset_key,
        canonical_asset_identity=identity,
        retrieval_uri=retrieval_uri,
        scale=scale,
        offset=offset,
        quantification_value=quantification,
        nodata=raster_nodata,
        metadata_source="ASSET_RASTER_AND_PRODUCT_METADATA_CROSS_CHECKED",
        cross_check="PASS",
    )


def reflectance_from_dn(dn: int | float, radiometry: Radiometry) -> float | None:
    if isinstance(dn, bool) or not isinstance(dn, (int, float)) or not math.isfinite(dn):
        return None
    if dn == 0 or dn == radiometry.nodata:
        return None
    reflectance = float(dn) * radiometry.scale + radiometry.offset
    return reflectance if math.isfinite(reflectance) else None


def ndvi_from_reflectance(red: float | None, nir: float | None, denominator_epsilon: float = 1e-6) -> float | None:
    if red is None or nir is None or not math.isfinite(red) or not math.isfinite(nir):
        return None
    denominator = nir + red
    if not math.isfinite(denominator) or abs(denominator) <= denominator_epsilon:
        return None
    value = (nir - red) / denominator
    if not math.isfinite(value) or value < -1.0 - 1e-12 or value > 1.0 + 1e-12:
        raise OfflineContractError("calibrated NDVI is outside [-1, 1]", "DETERMINISTIC_PROCESSING_ERROR")
    return min(1.0, max(-1.0, value))


def calibrated_ndvi(item: dict[str, Any], red_dn: int | float, nir_dn: int | float) -> tuple[float | None, tuple[Radiometry, Radiometry]]:
    red_metadata = resolve_item_asset_radiometry(item, "B04")
    nir_metadata = resolve_item_asset_radiometry(item, "B08")
    red = reflectance_from_dn(red_dn, red_metadata)
    nir = reflectance_from_dn(nir_dn, nir_metadata)
    return ndvi_from_reflectance(red, nir), (red_metadata, nir_metadata)


def classify_delta(delta_ndvi: int | float | str | Decimal, tau: int | float | str | Decimal = PRIMARY_TAU) -> dict[str, Any]:
    delta = canonical_decimal(delta_ndvi, "delta_ndvi")
    threshold = canonical_decimal(tau, "tau")
    if threshold < 0:
        raise OfflineContractError("tau must be non-negative", "DETERMINISTIC_PROCESSING_ERROR")
    if delta > threshold:
        status, disposition, reasons = "COMPLETED", "CORROBORATING", []
    elif delta < -threshold:
        status, disposition, reasons = "COMPLETED", "CONTRADICTORY", []
    else:
        status = "ABSTAINED"
        disposition = "INCONCLUSIVE"
        reasons = ["EFFECT_WITHIN_OPERATIONAL_INDIFFERENCE_BAND"]
    return {
        "delta_ndvi": float(delta),
        "tau": float(threshold),
        "execution_status": status,
        "evidence_disposition": disposition,
        "reason_codes": reasons,
        "comparison_semantics": COMPARISON_SEMANTICS,
    }


def classify_primary_and_sensitivities(delta_ndvi: int | float | str | Decimal) -> dict[str, Any]:
    return {
        "primary": {"policy_id": PRIMARY_POLICY_ID, **classify_delta(delta_ndvi, PRIMARY_TAU)},
        "sensitivities": [
            {"policy_id": f"{PRIMARY_POLICY_ID}:SENSITIVITY:{tau}", **classify_delta(delta_ndvi, tau)}
            for tau in SENSITIVITY_TAUS
        ],
    }


def enforce_item_limit(items: Sequence[Any], maximum: int) -> Sequence[Any]:
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
        raise OfflineContractError("maximum item count must be a positive integer", "DETERMINISTIC_PROCESSING_ERROR")
    if len(items) > maximum:
        raise OfflineContractError(
            f"qualifying item count {len(items)} exceeds configured maximum {maximum}; truncation is prohibited",
            RESOURCE_LIMIT_REASON,
        )
    return items


def independent_acquisition_ids(items: Iterable[dict[str, Any]]) -> list[str]:
    identities: set[str] = set()
    for item in items:
        value = item.get("datatake_id")
        if not isinstance(value, str) or not value:
            raise OfflineContractError("item is missing deterministic datatake_id", "SOURCE_VERSION_UNRESOLVED")
        identities.add(value)
    return sorted(identities)


def require_cea_boundary(role: str, actual_sha256: str, approved_sha256: str) -> None:
    if role != "CEA":
        raise OfflineContractError("analysis boundary role must be CEA", "BOUNDARY_NOT_FROZEN")
    if actual_sha256 != approved_sha256:
        raise OfflineContractError("analysis boundary SHA-256 does not match the approved CEA", "PROVENANCE_HASH_MISMATCH")


def require_congruent_utm_grid(grids: Iterable[dict[str, Any]], resolution: float = 10.0) -> None:
    for grid in grids:
        values = [grid.get(key) for key in ("x_resolution", "y_resolution", "x_origin", "y_origin")]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
            raise OfflineContractError("grid metadata is missing or non-finite", "SCL_ALIGNMENT_FAILED")
        xres, yres, xorigin, yorigin = map(float, values)
        if not math.isclose(abs(xres), resolution) or not math.isclose(abs(yres), resolution):
            raise OfflineContractError("item grid resolution is not the frozen 10 m lattice", "SCL_ALIGNMENT_FAILED")
        if not math.isclose(xorigin % resolution, 0.0, abs_tol=1e-9) or not math.isclose(yorigin % resolution, 0.0, abs_tol=1e-9):
            raise OfflineContractError("item grid origin is not congruent with the frozen UTM lattice", "SCL_ALIGNMENT_FAILED")


def descriptive_distribution(values: Sequence[float]) -> dict[str, float | int]:
    if not values or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
        raise OfflineContractError("distribution values must be a non-empty finite sequence", "DETERMINISTIC_PROCESSING_ERROR")
    ordered = sorted(float(value) for value in values)

    def quantile(probability: float) -> float:
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    median = quantile(0.5)
    q25 = quantile(0.25)
    q75 = quantile(0.75)
    return {
        "count": len(ordered),
        "q05": quantile(0.05),
        "q25": q25,
        "median": median,
        "q75": q75,
        "q95": quantile(0.95),
        "iqr": q75 - q25,
        "mad": statistics.median(abs(value - median) for value in ordered),
    }
