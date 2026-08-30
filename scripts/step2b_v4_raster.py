from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from scripts import step2b_offline

CANONICAL_ARRAY_HASH_ID = "NUMPY_LITTLE_ENDIAN_C_ORDER_V1"


class RasterContractError(ValueError):
    def __init__(self, message: str, reason_code: str = "DETERMINISTIC_PROCESSING_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def _numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - exercised by runtime preflight
        raise RasterContractError("NumPy is required by the frozen V4 runtime") from exc
    return np


def snapped_grid(
    bounds: Sequence[float],
    *,
    resolution: float = 10.0,
    origin_x: float = 0.0,
    origin_y: float = 10_000_000.0,
) -> dict[str, Any]:
    if len(bounds) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bounds):
        raise RasterContractError("target-grid bounds must contain four finite numbers")
    if resolution <= 0 or not math.isfinite(resolution):
        raise RasterContractError("target-grid resolution must be positive and finite")
    min_x, min_y, max_x, max_y = (float(value) for value in bounds)
    if min_x >= max_x or min_y >= max_y:
        raise RasterContractError("target-grid bounds must have positive area")
    left = origin_x + math.floor((min_x - origin_x) / resolution) * resolution
    right = origin_x + math.ceil((max_x - origin_x) / resolution) * resolution
    bottom = origin_y + math.floor((min_y - origin_y) / resolution) * resolution
    top = origin_y + math.ceil((max_y - origin_y) / resolution) * resolution
    width = round((right - left) / resolution)
    height = round((top - bottom) / resolution)
    return {
        "crs": "EPSG:32754",
        "resolution_m": resolution,
        "bounds": [left, bottom, right, top],
        "width": width,
        "height": height,
        "transform": [resolution, 0.0, left, 0.0, -resolution, top],
        "pixel_count": width * height,
    }


def canonical_array_sha256(value: Any, *, dtype: str | None = None) -> str:
    np = _numpy()
    array = np.asarray(value, dtype=dtype)
    if array.dtype.kind == "f":
        canonical = np.asarray(array, dtype="<f8", order="C").copy()
        canonical[np.isnan(canonical)] = np.nan
    elif array.dtype.kind == "b":
        canonical = np.asarray(array, dtype=np.uint8, order="C")
    elif array.dtype.kind in "iu":
        canonical = np.asarray(array, dtype="<i8", order="C")
    else:
        raise RasterContractError(f"unsupported canonical array dtype {array.dtype}")
    header = json.dumps(
        {
            "array_hash_id": CANONICAL_ARRAY_HASH_ID,
            "dtype": canonical.dtype.str,
            "shape": list(canonical.shape),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(header + b"\n" + canonical.tobytes(order="C")).hexdigest()


def calibrated_ndvi_array(
    red_dn: Any,
    nir_dn: Any,
    scl: Any,
    *,
    red_scale: float,
    red_offset: float,
    nir_scale: float,
    nir_offset: float,
    red_nodata: float,
    nir_nodata: float,
    valid_scl_classes: Sequence[int] = (4, 5),
    denominator_epsilon: float = 1e-6,
    source_valid_mask: Any | None = None,
) -> Any:
    np = _numpy()
    red_raw = np.asarray(red_dn)
    nir_raw = np.asarray(nir_dn)
    scl_raw = np.asarray(scl)
    if red_raw.shape != nir_raw.shape or red_raw.shape != scl_raw.shape:
        raise RasterContractError("B04, B08 and SCL arrays must have identical target-grid shapes", "SCL_ALIGNMENT_FAILED")
    valid = np.isfinite(red_raw) & np.isfinite(nir_raw) & np.isfinite(scl_raw)
    valid &= (red_raw != 0) & (nir_raw != 0)
    valid &= (red_raw != red_nodata) & (nir_raw != nir_nodata)
    valid &= np.isin(scl_raw, tuple(valid_scl_classes))
    if source_valid_mask is not None:
        mask = np.asarray(source_valid_mask, dtype=bool)
        if mask.shape != red_raw.shape:
            raise RasterContractError("source-valid mask shape does not match target grid")
        valid &= mask
    red = red_raw.astype(np.float64) * float(red_scale) + float(red_offset)
    nir = nir_raw.astype(np.float64) * float(nir_scale) + float(nir_offset)
    denominator = nir + red
    valid &= np.isfinite(red) & np.isfinite(nir) & np.isfinite(denominator)
    valid &= np.abs(denominator) > denominator_epsilon
    result = np.full(red.shape, np.nan, dtype=np.float64)
    result[valid] = (nir[valid] - red[valid]) / denominator[valid]
    if np.any(np.isfinite(result) & ((result < -1.0 - 1e-12) | (result > 1.0 + 1e-12))):
        raise RasterContractError("calibrated NDVI is outside [-1, 1]")
    result[np.isfinite(result)] = np.clip(result[np.isfinite(result)], -1.0, 1.0)
    return result


def mosaic_acquisition_components(components: Sequence[tuple[str, Any]], *, tolerance: float = 1e-12) -> Any:
    np = _numpy()
    if not components:
        raise RasterContractError("an acquisition group has no raster components", "AOI_NO_OVERLAP")
    ordered = sorted(components, key=lambda record: record[0])
    shape = np.asarray(ordered[0][1]).shape
    output = np.full(shape, np.nan, dtype=np.float64)
    for component_id, values in ordered:
        array = np.asarray(values, dtype=np.float64)
        if array.shape != shape:
            raise RasterContractError(f"component {component_id} has a non-congruent shape", "SCL_ALIGNMENT_FAILED")
        incoming = np.isfinite(array)
        overlap = incoming & np.isfinite(output)
        if np.any(np.abs(output[overlap] - array[overlap]) > tolerance):
            raise RasterContractError(
                f"component {component_id} conflicts with an earlier component on the target grid",
                "EVIDENCE_CONFLICT_UNRESOLVED",
            )
        output[incoming & ~np.isfinite(output)] = array[incoming & ~np.isfinite(output)]
    return output


def _finite_quantiles(values: Any) -> dict[str, float | int]:
    np = _numpy()
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise RasterContractError("delta distribution has no finite joint-eligible pixels", "VALID_OBSERVATION_COVERAGE_LOW")
    quantiles = np.quantile(finite, [0.05, 0.25, 0.5, 0.75, 0.95], method="linear")
    median = float(quantiles[2])
    return {
        "count": int(finite.size),
        "q05": float(quantiles[0]),
        "q25": float(quantiles[1]),
        "median": median,
        "q75": float(quantiles[3]),
        "q95": float(quantiles[4]),
        "iqr": float(quantiles[3] - quantiles[1]),
        "mad": float(np.median(np.abs(finite - median))),
    }


def aggregate_windows(
    pre_acquisitions: Sequence[Any],
    post_acquisitions: Sequence[Any],
    aoi_mask: Any,
    *,
    minimum_observations: int = 3,
    minimum_joint_fraction: float = 0.8,
) -> dict[str, Any]:
    np = _numpy()
    aoi = np.asarray(aoi_mask, dtype=bool)
    if aoi.ndim != 2 or not np.any(aoi):
        raise RasterContractError("the target-grid AOI mask is empty", "AOI_NO_OVERLAP")
    if len(pre_acquisitions) < minimum_observations or len(post_acquisitions) < minimum_observations:
        return {
            "coverage_passed": False,
            "reason_codes": ["VALID_OBSERVATION_COVERAGE_LOW"],
            "aoi_total_pixels": int(aoi.sum()),
            "pre_unique_acquisitions": len(pre_acquisitions),
            "post_unique_acquisitions": len(post_acquisitions),
            "aoi_valid_pixels": 0,
            "aoi_valid_fraction": 0.0,
            "pre_window_ndvi_median": None,
            "post_window_ndvi_median": None,
            "delta_ndvi": None,
            "delta_distribution": None,
            "pre_valid_count_distribution": None,
            "post_valid_count_distribution": None,
        }
    expected_shape = aoi.shape
    stacks = []
    for label, acquisitions in (("PRE", pre_acquisitions), ("POST", post_acquisitions)):
        stack = np.asarray(acquisitions, dtype=np.float64)
        if stack.ndim != 3 or stack.shape[1:] != expected_shape:
            raise RasterContractError(f"{label} acquisition arrays do not match the AOI target grid")
        stacks.append(stack)
    pre_stack, post_stack = stacks
    pre_count = np.sum(np.isfinite(pre_stack), axis=0)
    post_count = np.sum(np.isfinite(post_stack), axis=0)
    pre_eligible = aoi & (pre_count >= minimum_observations)
    post_eligible = aoi & (post_count >= minimum_observations)
    joint = pre_eligible & post_eligible
    total = int(aoi.sum())
    joint_count = int(joint.sum())
    joint_fraction = joint_count / total
    pre_composite = np.full(expected_shape, np.nan, dtype=np.float64)
    post_composite = np.full(expected_shape, np.nan, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        pre_composite[pre_eligible] = np.nanmedian(pre_stack[:, pre_eligible], axis=0)
        post_composite[post_eligible] = np.nanmedian(post_stack[:, post_eligible], axis=0)
    pre_median = float(np.median(pre_composite[joint])) if joint_count else None
    post_median = float(np.median(post_composite[joint])) if joint_count else None
    delta = float(Decimal(str(post_median)) - Decimal(str(pre_median))) if joint_count else None
    distribution = _finite_quantiles(post_composite[joint] - pre_composite[joint]) if joint_count else None
    return {
        "coverage_passed": joint_fraction >= minimum_joint_fraction,
        "reason_codes": [] if joint_fraction >= minimum_joint_fraction else ["VALID_OBSERVATION_COVERAGE_LOW"],
        "aoi_total_pixels": total,
        "pre_unique_acquisitions": len(pre_acquisitions),
        "post_unique_acquisitions": len(post_acquisitions),
        "pre_eligible_pixels": int(pre_eligible.sum()),
        "post_eligible_pixels": int(post_eligible.sum()),
        "aoi_valid_pixels": joint_count,
        "aoi_valid_fraction": joint_fraction,
        "pre_window_ndvi_median": pre_median,
        "post_window_ndvi_median": post_median,
        "delta_ndvi": delta,
        "delta_distribution": distribution,
        "pre_valid_count_distribution": step2b_offline.descriptive_distribution(pre_count[aoi].astype(float).tolist()),
        "post_valid_count_distribution": step2b_offline.descriptive_distribution(post_count[aoi].astype(float).tolist()),
        "pre_composite_sha256": canonical_array_sha256(pre_composite),
        "post_composite_sha256": canonical_array_sha256(post_composite),
        "joint_mask_sha256": canonical_array_sha256(joint),
    }


def qualification_from_aggregation(aggregation: dict[str, Any]) -> dict[str, Any]:
    if not aggregation["coverage_passed"]:
        return {
            "execution_status": "ABSTAINED",
            "evidence_disposition": "INCONCLUSIVE",
            "reason_codes": list(aggregation["reason_codes"]),
            "primary": None,
            "sensitivities": None,
        }
    delta = aggregation.get("delta_ndvi")
    if delta is None or not math.isfinite(delta):
        raise RasterContractError("coverage passed without a finite NDVI delta")
    classification = step2b_offline.classify_primary_and_sensitivities(delta)
    return {
        "execution_status": classification["primary"]["execution_status"],
        "evidence_disposition": classification["primary"]["evidence_disposition"],
        "reason_codes": classification["primary"]["reason_codes"],
        "primary": classification["primary"],
        "sensitivities": classification["sensitivities"],
    }
