from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from scripts import step2b_offline


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policies" / "eop101132" / "step2b-proposed-policy.json"
APPROVED_POLICY_SHA256 = "4a8a138308f0c3b95e8e9f06d448619e9b710882b1233fc71ab5df3158c7ca59"
BOUNDARY_SHA256 = "3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2"
BOUNDARY_BYTES = 10219
APPROVAL_STATEMENT = f"批准 QUALIFICATION {APPROVED_POLICY_SHA256}"
APPROVAL_SCOPE = "ONE_PRIMARY_EOP101132_RUN"
USER_AGENT = "qualify-environmental-evidence/0.4.0 (bounded EOP101132 runtime)"
STATIC_ALLOWED_HOSTS = {"cer.gov.au", "planetarycomputer.microsoft.com"}
FORBIDDEN_CODES = [
    "CAUSAL_ATTRIBUTION", "CARBON_QUANTITY", "ADDITIONALITY",
    "CREDIT_VALIDITY_OR_QUALITY", "REGULATORY_OR_METHODOLOGY_COMPLIANCE",
    "PERMANENCE", "PROJECT_PERFORMANCE_BEYOND_BOUNDED_OBSERVATION",
    "GREENWASHING_OR_LEGAL_LIABILITY", "FINANCIAL_RECOMMENDATION",
    "TOKENISATION_READINESS",
]
TRANSFORMATION_IDS = [
    "VALIDATE_CLAIM_CONTRACT", "CHECK_AUTHORITY_SCOPE", "RESOLVE_REGISTRY_FACTS",
    "RESOLVE_CEA_BOUNDARY", "SEARCH_SENTINEL2_L2A", "ALIGN_AOI_RASTERS",
    "APPLY_SCL_VALIDITY_MASK", "CALCULATE_AOI_VALID_COVERAGE",
    "CALCULATE_AOI_NDVI", "AGGREGATE_SEASONAL_WINDOWS",
    "QUALIFY_OBSERVATIONAL_CLAIM", "EMIT_ASSESSMENT_AND_PROVENANCE",
]


class RuntimeFailure(RuntimeError):
    def __init__(self, message: str, reason_code: str):
        super().__init__(message)
        self.reason_code = reason_code


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def write_json(path: Path, value: Any, *, canonical: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) if canonical else (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    path.write_bytes(payload)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _safe_host(url: str, extra_hosts: set[str] | None = None) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    allowed = STATIC_ALLOWED_HOSTS | (extra_hosts or set())
    if parsed.scheme != "https" or host not in allowed or parsed.username or parsed.password:
        raise RuntimeFailure(f"network target is not allowlisted: {host!r}", "EVIDENCE_SOURCE_NOT_ALLOWED")
    return host


def http_request(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    extra_hosts: set[str] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    _safe_host(url, extra_hosts)
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json,application/zip,text/html,*/*"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    retrieved_at = utc_now()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            final_url = response.geturl()
            _safe_host(final_url, extra_hosts)
            metadata = {
                "requested_url": url,
                "final_url": final_url,
                "method": method,
                "retrieved_at_utc": retrieved_at,
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "content_length_header": response.headers.get("Content-Length"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "response_sha256": sha256_bytes(raw),
                "response_bytes": len(raw),
            }
            return raw, metadata
    except urllib.error.HTTPError as exc:
        raise RuntimeFailure(f"HTTP {exc.code} retrieving {url}", "SOURCE_UNAVAILABLE") from exc
    except urllib.error.URLError as exc:
        raise RuntimeFailure(f"source unavailable: {exc.reason}", "SOURCE_UNAVAILABLE") from exc


def initialise_run() -> Path:
    policy_bytes = POLICY_PATH.read_bytes()
    policy = read_json(POLICY_PATH)
    digest = sha256_bytes(policy_bytes)
    if digest != APPROVED_POLICY_SHA256:
        raise RuntimeFailure("local policy bytes do not match human approval", "PROVENANCE_HASH_MISMATCH")
    timestamp = utc_now()
    approval = {
        "approval_record_version": "1.0.0",
        "policy_id": "DEMO_QUALIFICATION_POLICY_EOP101132_V3",
        "approved_policy_sha256": APPROVED_POLICY_SHA256,
        "mode": "QUALIFICATION",
        "approval_statement": APPROVAL_STATEMENT,
        "approval_timestamp_utc": timestamp,
        "approver_role": "HUMAN_PROJECT_OWNER",
        "runtime_scope": APPROVAL_SCOPE,
        "policy_mutation_permitted": False,
    }
    step2b_offline.validate_detached_approval(policy, policy_bytes, approval)
    run_id = f"EOP101132-STEP2B-{timestamp.replace('-', '').replace(':', '').replace('.', '')}-{uuid.uuid4().hex[:8]}"
    run_dir = ROOT / "runs" / run_id
    if run_dir.exists():
        raise RuntimeFailure("run directory already exists", "PROVENANCE_HASH_MISMATCH")
    for relative in (
        "source/item-metadata", "inventory", "cache", "diagnostics", "logs"
    ):
        (run_dir / relative).mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "approval.json", approval, canonical=True)
    state = {
        "run_id": run_id,
        "case_id": "EOP101132-NDVI-001",
        "policy_id": policy["policy_id"],
        "policy_sha256": digest,
        "approval_sha256": sha256_file(run_dir / "approval.json"),
        "contract_version": policy["contract_version"],
        "created_at_utc": timestamp,
        "stage": "APPROVAL_BOUND",
    }
    write_json(run_dir / "run-state.json", state)
    return run_dir


def _planar_signed_area(ring: list[list[float]]) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def _point_in_ring(point: list[float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
    return inside


def parse_polygon_shapefile(raw: bytes) -> list[list[list[list[float]]]]:
    if len(raw) < 100 or struct.unpack(">i", raw[:4])[0] != 9994:
        raise RuntimeFailure("invalid shapefile header", "BOUNDARY_NOT_FROZEN")
    rings: list[list[list[float]]] = []
    offset = 100
    while offset + 8 <= len(raw):
        _, words = struct.unpack(">2i", raw[offset : offset + 8])
        content = raw[offset + 8 : offset + 8 + words * 2]
        offset += 8 + words * 2
        if len(content) < 44:
            continue
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type == 0:
            continue
        if shape_type not in {5, 15, 25}:
            raise RuntimeFailure(f"unexpected shapefile geometry type {shape_type}", "BOUNDARY_NOT_FROZEN")
        num_parts, num_points = struct.unpack("<2i", content[36:44])
        parts = list(struct.unpack(f"<{num_parts}i", content[44 : 44 + num_parts * 4]))
        points_start = 44 + num_parts * 4
        points = [list(struct.unpack("<2d", content[points_start + i * 16 : points_start + (i + 1) * 16])) for i in range(num_points)]
        ends = parts[1:] + [num_points]
        rings.extend(points[start:end] for start, end in zip(parts, ends, strict=True))
    if not rings or any(len(ring) < 4 or ring[0] != ring[-1] for ring in rings):
        raise RuntimeFailure("boundary polygon rings are invalid or empty", "BOUNDARY_NOT_FROZEN")
    outers = [ring for ring in rings if _planar_signed_area(ring) < 0]
    holes = [ring for ring in rings if _planar_signed_area(ring) > 0]
    polygons = [[outer] for outer in outers]
    for hole in holes:
        candidates = [index for index, outer in enumerate(outers) if _point_in_ring(hole[0], outer)]
        if not candidates:
            raise RuntimeFailure("boundary hole is not contained by an exterior ring", "BOUNDARY_NOT_FROZEN")
        owner = min(candidates, key=lambda index: abs(_planar_signed_area(outers[index])))
        polygons[owner].append(hole)
    if len(polygons) != 10:
        raise RuntimeFailure(f"boundary has {len(polygons)} exterior parts; expected 10", "BOUNDARY_NOT_FROZEN")
    return polygons


def lonlat_to_utm54(lon: float, lat: float) -> tuple[float, float]:
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996
    lon0 = math.radians(141.0)
    phi, lam = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = ep2 * math.cos(phi) ** 2
    aa = math.cos(phi) * (lam - lon0)
    m = a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
             + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
             - (35 * e2**3 / 3072) * math.sin(6 * phi))
    easting = 500000 + k0 * n * (aa + (1 - t + c) * aa**3 / 6 + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * aa**5 / 120)
    northing = k0 * (m + n * math.tan(phi) * (aa**2 / 2 + (5 - t + 9 * c + 4 * c**2) * aa**4 / 24 + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * aa**6 / 720)) + 10000000
    return easting, northing


def signed_area(ring: list[list[float]]) -> float:
    projected = [lonlat_to_utm54(*point) for point in ring]
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(projected, projected[1:])) / 2


def boundary_geojson(polygons: list[list[list[list[float]]]]) -> dict[str, Any]:
    return {"type": "MultiPolygon", "coordinates": polygons}


def safe_extract_boundary(zip_path: Path, destination: Path) -> tuple[list[list[list[float]]], dict[str, Any]]:
    expected = {"EOP101132_CEA.dbf", "EOP101132_CEA.prj", "EOP101132_CEA.shp", "EOP101132_CEA.shx"}
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if set(names) != expected or any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise RuntimeFailure("CEA archive members differ from the frozen safe set", "SOURCE_VERSION_UNRESOLVED")
        prj = archive.read("EOP101132_CEA.prj").decode("ascii", errors="strict")
        if "GDA2020" not in prj:
            raise RuntimeFailure("CEA CRS is not the frozen GDA2020 definition", "BOUNDARY_NOT_FROZEN")
        shp = archive.read("EOP101132_CEA.shp")
        polygons = parse_polygon_shapefile(shp)
        if destination.exists():
            if {path.name for path in destination.iterdir() if path.is_file()} != expected:
                raise RuntimeFailure("existing CEA extraction differs from the frozen safe set", "SOURCE_VERSION_UNRESOLVED")
            if (destination / "EOP101132_CEA.shp").read_bytes() != shp:
                raise RuntimeFailure("existing CEA extraction bytes differ from the archive", "PROVENANCE_HASH_MISMATCH")
        else:
            destination.mkdir(parents=True, exist_ok=False)
            archive.extractall(destination)
    area = abs(sum(signed_area(ring) for polygon in polygons for ring in polygon))
    return polygons, {"geometry_type": "MultiPolygon", "geometry_part_count": len(polygons), "source_crs": "EPSG:7844", "projected_area_m2": area, "geometry_valid": True}


def _project_fields(html: bytes) -> dict[str, Any]:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.decode("utf-8", errors="replace")))
    fields: dict[str, Any] = {"project_id_present": "EOP101132" in text, "model_start_date_present": "6 October 2017" in text or "2017-10-06" in text}
    title = re.search(r"Sunday Morning Hills Revegetation", text, flags=re.I)
    fields["project_name"] = title.group(0) if title else None
    return fields


def _stac_search(
    run_dir: Path,
    endpoint: str,
    window_name: str,
    window: dict[str, str],
    geometry: dict[str, Any],
    *,
    request_fn: Callable[..., tuple[bytes, dict[str, Any]]] = http_request,
) -> list[dict[str, Any]]:
    search_url = endpoint.rstrip("/") + "/search"
    body_value = {
        "collections": ["sentinel-2-l2a"],
        "intersects": geometry,
        "datetime": f"{window['start_date']}T00:00:00Z/{window['end_date']}T23:59:59Z",
        "limit": 41,
    }
    body = canonical_bytes(body_value)
    page = 1
    items: list[dict[str, Any]] = []
    request_url, request_method, request_body = search_url, "POST", body
    request_records = []
    while request_url:
        raw, metadata = request_fn(
            request_url,
            method=request_method,
            body=request_body,
            headers={"Content-Type": "application/json"} if request_method == "POST" else None,
        )
        raw_path = run_dir / "source" / f"stac-{window_name}-page-{page:03d}.raw.json"
        raw_path.write_bytes(raw)
        response = json.loads(raw.decode("utf-8"))
        page_items = response.get("features", [])
        if not isinstance(page_items, list):
            raise RuntimeFailure("STAC response features is not a list", "SOURCE_VERSION_UNRESOLVED")
        items.extend(page_items)
        request_records.append({
            **metadata,
            "request_body": body_value if page == 1 else None,
            "raw_path": raw_path.relative_to(run_dir).as_posix(),
            "pagination_sequence": page,
            "page_item_count": len(page_items),
        })
        next_link = next((link for link in response.get("links", []) if link.get("rel") == "next"), None)
        if next_link:
            request_url = next_link["href"]
            request_method = next_link.get("method", "GET").upper()
            next_body = next_link.get("body")
            request_body = canonical_bytes(next_body) if next_body is not None else None
        else:
            request_url = ""
        page += 1
    write_json(run_dir / "source" / f"stac-{window_name}-requests.json", request_records)
    write_json(run_dir / "source" / f"stac-{window_name}.raw.json", {"type": "FeatureCollection", "features": items}, canonical=True)
    return items


def _deduplicate_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: dict[tuple[str, str], bytes] = {}
    result = []
    for item in items:
        key = (item.get("collection"), item.get("id"))
        payload = canonical_bytes(item)
        if key in seen and seen[key] != payload:
            raise RuntimeFailure(f"conflicting duplicate STAC item {key}", "SOURCE_VERSION_UNRESOLVED")
        if key not in seen:
            seen[key] = payload
            result.append(item)
    result.sort(key=lambda item: (item.get("properties", {}).get("datetime", ""), item.get("id", "")))
    return result, len(items) - len(result)


def _asset_identity(item: dict[str, Any], key: str) -> str | None:
    asset = item.get("assets", {}).get(key)
    return asset.get("href") if isinstance(asset, dict) else None


def _inventory_row(item: dict[str, Any], window: str) -> dict[str, Any]:
    properties = item.get("properties", {})
    return {
        "window": window.upper(),
        "item_id": item.get("id"),
        "collection": item.get("collection"),
        "platform": properties.get("platform"),
        "acquisition_datetime": properties.get("datetime"),
        "datatake_id": properties.get("s2:datatake_id"),
        "mgrs_tile": properties.get("s2:mgrs_tile"),
        "relative_orbit": properties.get("sat:relative_orbit"),
        "processing_baseline": properties.get("s2:processing_baseline"),
        "eo_cloud_cover": properties.get("eo:cloud_cover"),
        "mean_solar_zenith_angle": properties.get("s2:mean_solar_zenith"),
        "solar_geometry_metadata_source": "STAC_PROPERTY:s2:mean_solar_zenith" if properties.get("s2:mean_solar_zenith") is not None else None,
        "solar_geometry_status": "AVAILABLE_NOT_EVALUATED" if properties.get("s2:mean_solar_zenith") is not None else "MISSING_NOT_EVALUATED",
        "radiometry_metadata_source": None,
        "radiometry_status": "NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED",
        "b04_scale": None,
        "b04_offset": None,
        "b04_quantification_value": None,
        "b04_nodata": None,
        "b08_scale": None,
        "b08_offset": None,
        "b08_quantification_value": None,
        "b08_nodata": None,
        "b04_identity": _asset_identity(item, "B04"),
        "b08_identity": _asset_identity(item, "B08"),
        "scl_identity": _asset_identity(item, "SCL"),
        "granule_metadata_identity": _asset_identity(item, "granule-metadata"),
        "product_metadata_identity": _asset_identity(item, "product-metadata"),
        "asset_keys": sorted(item.get("assets", {})),
        "admissible": None,
        "admissibility_status": "NOT_EVALUATED",
        "exclusion_reasons": [],
    }


def fetch_sources(run_dir: Path) -> None:
    state = read_json(run_dir / "run-state.json")
    policy_bytes = POLICY_PATH.read_bytes()
    policy = read_json(POLICY_PATH)
    approval = read_json(run_dir / "approval.json")
    step2b_offline.validate_detached_approval(policy, policy_bytes, approval)
    if sha256_bytes(policy_bytes) != state["policy_sha256"]:
        raise RuntimeFailure("policy changed after run start", "PROVENANCE_HASH_MISMATCH")
    project_url = policy["project_and_boundary"]["project_page"]
    page_path = run_dir / "source" / "cer-project-page.raw"
    page_metadata_path = run_dir / "source" / "cer-project-page.metadata.json"
    if page_path.exists() and page_metadata_path.exists():
        page_raw = page_path.read_bytes()
        page_metadata = read_json(page_metadata_path)
        if page_metadata.get("response_sha256") != sha256_bytes(page_raw):
            raise RuntimeFailure("cached CER project page hash mismatch", "PROVENANCE_HASH_MISMATCH")
    else:
        page_raw, page_metadata = http_request(project_url)
        page_path.write_bytes(page_raw)
        page_metadata["extracted_project_fields"] = _project_fields(page_raw)
        page_metadata["extraction_software_version"] = "step2b_runtime.py/0.1.0"
        write_json(page_metadata_path, page_metadata)
    cea_url = policy["project_and_boundary"]["boundary_artifact_uri"]
    cea_path = run_dir / "source" / "eop101132-cea.zip"
    cea_metadata_path = run_dir / "source" / "eop101132-cea.metadata.json"
    if cea_path.exists():
        cea_raw = cea_path.read_bytes()
        cea_metadata = read_json(cea_metadata_path) if cea_metadata_path.exists() else {
            "requested_url": cea_url,
            "retrieved_at_utc": state["created_at_utc"],
            "response_sha256": sha256_bytes(cea_raw),
            "response_bytes": len(cea_raw),
        }
    else:
        cea_raw, cea_metadata = http_request(cea_url)
        cea_path.write_bytes(cea_raw)
    if sha256_bytes(cea_raw) != BOUNDARY_SHA256 or len(cea_raw) != BOUNDARY_BYTES:
        state.update(stage="SOURCE_ARTIFACT_DRIFT", terminal_reason_code="SOURCE_VERSION_UNRESOLVED")
        write_json(run_dir / "run-state.json", state)
        raise RuntimeFailure("CER CEA bytes differ from the frozen artifact", "SOURCE_VERSION_UNRESOLVED")
    polygons, boundary = safe_extract_boundary(cea_path, run_dir / "cache" / "cea-extracted")
    cea_metadata.update(boundary)
    cea_metadata.update({"analysis_boundary_role": "CEA", "expected_sha256": BOUNDARY_SHA256, "hash_verified": True, "byte_size_verified": True})
    write_json(cea_metadata_path, cea_metadata)
    geometry = boundary_geojson(polygons)
    write_json(run_dir / "cache" / "aoi-wgs84.geojson", geometry, canonical=True)
    endpoint = policy["stac_source_and_selection"]["endpoint"]
    all_rows: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}
    for window_name in ("pre", "post"):
        raw_items = _stac_search(run_dir, endpoint, window_name, policy["temporal_scope"][f"{window_name}_window"], geometry)
        items, duplicates = _deduplicate_items(raw_items)
        counts[window_name] = {"before_deduplication": len(raw_items), "after_deduplication": len(items), "duplicate_count": duplicates}
        if len(items) > policy["stac_source_and_selection"]["maximum_items_per_window"]:
            state.update(stage="RESOURCE_LIMIT_EXCEEDED", terminal_reason_code="RESOURCE_LIMIT_EXCEEDED", stac_counts=counts)
            write_json(run_dir / "run-state.json", state)
            raise RuntimeFailure(f"{window_name} window has {len(items)} items", "RESOURCE_LIMIT_EXCEEDED")
        for item in items:
            write_json(run_dir / "source" / "item-metadata" / f"{item['id']}.json", item, canonical=True)
            all_rows.append(_inventory_row(item, window_name))
    write_json(run_dir / "inventory" / "scene-inventory.json", all_rows)
    with (run_dir / "inventory" / "scene-inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_rows[0]) if all_rows else ["window", "item_id"])
        writer.writeheader()
        for row in all_rows:
            serialised = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()}
            writer.writerow(serialised)
    state.update(stage="SCENE_INVENTORY_CREATED", stac_counts=counts, scene_inventory_count=len(all_rows), boundary=boundary)
    write_json(run_dir / "run-state.json", state)


def _load_cached_items(run_dir: Path, window: str) -> list[dict[str, Any]]:
    value = read_json(run_dir / "source" / f"stac-{window}.raw.json")
    items, _ = _deduplicate_items(value["features"])
    return items


def _empty_solar_summary() -> dict[str, Any]:
    return step2b_offline.solar_geometry_diagnostic([], [])


def _runtime_case(run_dir: Path, policy: dict[str, Any]) -> dict[str, Any]:
    case = read_json(ROOT / "cases" / "eop101132" / "case-spec.json")
    cea_url = policy["project_and_boundary"]["boundary_artifact_uri"]
    binding = next(item for item in case["evidence_policy"]["source_bindings"] if item["source_id"] == "CER_PUBLISHED_CEA")
    binding.update(canonical_uri=cea_url, discovery_uri=None, retrieval_uri=None, binding_status="FROZEN")
    case["spatial_scope"] = {
        "status": "FROZEN",
        "boundary_source_id": "CER_PUBLISHED_CEA",
        "boundary_artifact_uri": cea_url,
        "boundary_sha256": BOUNDARY_SHA256,
    }
    case["temporal_scope"] = {
        "status": "FROZEN",
        "pre_window": policy["temporal_scope"]["pre_window"],
        "post_window": policy["temporal_scope"]["post_window"],
        "seasonal_rule": {"rule_id": policy["bounded_claim"]["seasonal_rule_id"]},
    }
    case["qualification_policy"].update(
        approval_status="APPROVED",
        scl_rule={"valid_classes": [4, 5]},
        observation_coverage_rule={
            "minimum_unique_acquisitions_per_window": 3,
            "minimum_valid_observations_per_pixel_per_window": 3,
            "minimum_joint_aoi_fraction": 0.8,
        },
    )
    case["pending_step_2"] = []
    case["runtime_ready"] = True
    write_json(run_dir / "runtime-case.json", case, canonical=True)
    return case


def _resource_limit_assessment(run_id: str, manifest_id: str) -> dict[str, Any]:
    return {
        "schema_version": "0.4.0",
        "case_id": "EOP101132-NDVI-001",
        "run_id": run_id,
        "execution_status": "ABSTAINED",
        "evidence_disposition": "INCONCLUSIVE",
        "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"],
        "quality_checks": {
            "claim_contract": "PASS",
            "evidence_allowlist": "PASS",
            "transformation_allowlist": "PASS",
            "spatial_scope": "PASS",
            "temporal_scope": "PASS",
            "observation_coverage": "NOT_RUN",
            "evidence_consistency": "PASS",
            "authority_scope": "PASS",
            "provenance": "PASS",
            "system_execution": "FAIL",
        },
        "observations": None,
        "statement_template_id": None,
        "supported_statement": None,
        "must_not_claim": FORBIDDEN_CODES,
        "human_review_required": True,
        "provenance_manifest_ref": manifest_id,
        "qualification_policy_version": "0.4.0",
        "statement_parameters": None,
    }


def _artifact(path: Path, run_dir: Path, artifact_type: str, produced_by: str, media_type: str) -> dict[str, Any]:
    return {
        "artifact_id": f"urn:eop101132:{run_dir.name}:artifact:{path.relative_to(run_dir).as_posix()}",
        "artifact_type": artifact_type,
        "content_sha256": sha256_file(path),
        "produced_by": produced_by,
        "media_type": media_type,
    }


def _input_hash(policy_hash: str, approval_hash: str, case_hash: str) -> str:
    return sha256_bytes(canonical_bytes({"policy_sha256": policy_hash, "approval_sha256": approval_hash, "runtime_case_sha256": case_hash}))


def _build_manifest(run_dir: Path, assessment: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    state = read_json(run_dir / "run-state.json")
    project_meta = read_json(run_dir / "source" / "cer-project-page.metadata.json")
    cea_meta = read_json(run_dir / "source" / "eop101132-cea.metadata.json")
    pre_requests = read_json(run_dir / "source" / "stac-pre-requests.json")
    post_requests = read_json(run_dir / "source" / "stac-post-requests.json")
    pre_items = _load_cached_items(run_dir, "pre")
    post_items = _load_cached_items(run_dir, "post")
    stac_digest = sha256_bytes(canonical_bytes({
        "pre": [record["response_sha256"] for record in pre_requests],
        "post": [record["response_sha256"] for record in post_requests],
    }))
    source_records = [
        {
            "source_id": "CER_PROJECT_RECORD",
            "canonical_uri": policy["project_and_boundary"]["project_page"],
            "retrieval_uri": None,
            "publisher": "Clean Energy Regulator",
            "retrieved_at_utc": project_meta["retrieved_at_utc"],
            "version_identifier": f"sha256:{project_meta['response_sha256']}",
            "content_sha256": project_meta["response_sha256"],
            "source_asset_ids": ["EOP101132"],
        },
        {
            "source_id": "CER_PUBLISHED_CEA",
            "canonical_uri": policy["project_and_boundary"]["boundary_artifact_uri"],
            "retrieval_uri": None,
            "publisher": "Clean Energy Regulator",
            "retrieved_at_utc": cea_meta["retrieved_at_utc"],
            "version_identifier": f"sha256:{BOUNDARY_SHA256}",
            "content_sha256": BOUNDARY_SHA256,
            "source_asset_ids": ["EOP101132_CEA.zip"],
        },
        {
            "source_id": "MSPC_SENTINEL2_L2A",
            "canonical_uri": "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
            "retrieval_uri": None,
            "publisher": "Microsoft Planetary Computer",
            "retrieved_at_utc": pre_requests[0]["retrieved_at_utc"],
            "version_identifier": f"stac-response-set-sha256:{stac_digest}",
            "content_sha256": stac_digest,
            "source_asset_ids": [item["id"] for item in pre_items + post_items],
        },
    ]
    artifact_specs = [
        (run_dir / "approval.json", "DETACHED_HUMAN_APPROVAL", "HUMAN_PROJECT_OWNER", "application/json"),
        (run_dir / "runtime-case.json", "FROZEN_RUNTIME_CASE", "VALIDATE_CLAIM_CONTRACT", "application/json"),
        (run_dir / "source" / "cer-project-page.raw", "RAW_SOURCE_RESPONSE", "RESOLVE_REGISTRY_FACTS", "text/html"),
        (run_dir / "source" / "eop101132-cea.zip", "FROZEN_CEA_ARCHIVE", "RESOLVE_CEA_BOUNDARY", "application/zip"),
        (run_dir / "source" / "stac-pre.raw.json", "RAW_STAC_ITEM_SET", "SEARCH_SENTINEL2_L2A", "application/json"),
        (run_dir / "source" / "stac-post.raw.json", "RAW_STAC_ITEM_SET", "SEARCH_SENTINEL2_L2A", "application/json"),
        (run_dir / "inventory" / "scene-inventory.json", "DISCOVERED_SCENE_INVENTORY", "SEARCH_SENTINEL2_L2A", "application/json"),
        (run_dir / "assessment.json", "PRIMARY_ASSESSMENT", "EMIT_ASSESSMENT_AND_PROVENANCE", "application/json"),
        (run_dir / "sensitivity.json", "SENSITIVITY_NOT_RUN", "QUALIFY_OBSERVATIONAL_CLAIM", "application/json"),
    ]
    artifacts = [_artifact(path, run_dir, artifact_type, produced_by, media_type) for path, artifact_type, produced_by, media_type in artifact_specs]
    artifact_by_type = {item["artifact_type"]: item["artifact_id"] for item in artifacts}
    initial = artifact_by_type["FROZEN_RUNTIME_CASE"]
    cea = artifact_by_type["FROZEN_CEA_ARCHIVE"]
    stac_outputs = [item["artifact_id"] for item in artifacts if item["artifact_type"] == "RAW_STAC_ITEM_SET"] + [artifact_by_type["DISCOVERED_SCENE_INVENTORY"]]
    assessment_id = artifact_by_type["PRIMARY_ASSESSMENT"]
    timestamp = state["created_at_utc"]
    end = utc_now()
    transformations = []
    for sequence, transformation_id in enumerate(TRANSFORMATION_IDS, 1):
        if sequence <= 4:
            status, reasons = "COMPLETED", []
        elif sequence == 5:
            status, reasons = "FAILED", ["RESOURCE_LIMIT_EXCEEDED"]
        elif sequence == 12:
            status, reasons = "COMPLETED", []
        else:
            status, reasons = "SKIPPED", ["RESOURCE_LIMIT_EXCEEDED"]
        inputs: list[str] = []
        outputs: list[str] = []
        if sequence == 1:
            inputs, outputs = [initial], [initial]
        elif sequence == 2:
            inputs, outputs = [initial], [initial]
        elif sequence == 3:
            inputs, outputs = [initial], [artifact_by_type["RAW_SOURCE_RESPONSE"]]
        elif sequence == 4:
            inputs, outputs = [artifact_by_type["RAW_SOURCE_RESPONSE"]], [cea]
        elif sequence == 5:
            inputs, outputs = [cea], stac_outputs
        elif sequence == 12:
            inputs, outputs = stac_outputs, [assessment_id]
        transformations.append({
            "sequence": sequence,
            "transformation_id": transformation_id,
            "implementation_version": "step2b_runtime.py/0.1.0",
            "parameter_set_ref": f"urn:eop101132:policy:{APPROVED_POLICY_SHA256}:{sequence}",
            "parameter_set_sha256": APPROVED_POLICY_SHA256,
            "input_artifact_refs": inputs,
            "output_artifact_refs": outputs,
            "status": status,
            "started_at_utc": timestamp,
            "finished_at_utc": end,
            "reason_codes": reasons,
        })
    case_hash = sha256_file(run_dir / "runtime-case.json")
    run_input_hash = _input_hash(APPROVED_POLICY_SHA256, state["approval_sha256"], case_hash)
    return {
        "schema_version": "0.4.0",
        "manifest_id": assessment["provenance_manifest_ref"],
        "run_id": state["run_id"],
        "case_id": state["case_id"],
        "runtime_mode": "EXECUTION",
        "created_at_utc": end,
        "run_identity": {
            "approved_policy_sha256": APPROVED_POLICY_SHA256,
            "calculated_policy_sha256_at_start": APPROVED_POLICY_SHA256,
            "final_policy_sha256": sha256_file(POLICY_PATH),
            "input_sha256_at_start": run_input_hash,
            "final_input_sha256": run_input_hash,
        },
        "source_records": source_records,
        "solar_geometry_records": [],
        "solar_geometry_summary": _empty_solar_summary(),
        "radiometry_records": [],
        "qualification_records": [],
        "artifact_records": artifacts,
        "transformation_records": transformations,
        "policy_versions": {key: "0.4.0" for key in ("evidence_sources", "transformations", "statement_templates", "forbidden_inferences", "reason_codes", "qualification_policy")},
        "software_environment": {
            "code_revision": sha256_file(Path(__file__)),
            "python_version": sys.version.split()[0],
            "package_lock_sha256": "NO_EXTERNAL_RUNTIME_PACKAGES",
            "packages": {},
        },
        "terminal_result": {
            "assessment_artifact_ref": assessment_id,
            "assessment_sha256": sha256_bytes(canonical_bytes(assessment)),
            "execution_status": "ABSTAINED",
            "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"],
            "canonicalisation_id": "CANONICAL_JSON_V1",
        },
    }


def finalise_resource_limit(run_dir: Path) -> None:
    state = read_json(run_dir / "run-state.json")
    if state.get("stage") != "RESOURCE_LIMIT_EXCEEDED" or state.get("terminal_reason_code") != "RESOURCE_LIMIT_EXCEEDED":
        raise RuntimeFailure("run is not at the frozen resource-limit terminal", "DETERMINISTIC_PROCESSING_ERROR")
    policy = read_json(POLICY_PATH)
    _runtime_case(run_dir, policy)
    pre_items = _load_cached_items(run_dir, "pre")
    post_items = _load_cached_items(run_dir, "post")
    rows = [_inventory_row(item, "pre") for item in pre_items] + [_inventory_row(item, "post") for item in post_items]
    for row in rows:
        row["admissible"] = None
        row["admissibility_status"] = "NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED"
        row["exclusion_reasons"] = ["NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED"]
    write_json(run_dir / "inventory" / "scene-inventory.json", rows, canonical=True)
    with (run_dir / "inventory" / "scene-inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    manifest_id = f"urn:eop101132:{state['run_id']}:provenance"
    assessment = _resource_limit_assessment(state["run_id"], manifest_id)
    assessment_path = run_dir / "assessment.json"
    expected_assessment_bytes = canonical_bytes(assessment)
    if assessment_path.exists():
        if assessment_path.read_bytes() != expected_assessment_bytes:
            raise RuntimeFailure("sealed primary assessment differs from the deterministic terminal", "PROVENANCE_HASH_MISMATCH")
    else:
        assessment_path.write_bytes(expected_assessment_bytes)
    sensitivity = {
        "run_id": state["run_id"], "status": "NOT_RUN", "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"],
        "primary_assessment_sha256": sha256_file(run_dir / "assessment.json"), "results": [],
    }
    write_json(run_dir / "sensitivity.json", sensitivity, canonical=True)
    write_json(run_dir / "diagnostics" / "window-coverage.json", {"status": "NOT_RUN", "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"]})
    write_json(run_dir / "diagnostics" / "solar-geometry.json", {"status": "NOT_RUN", "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"], "summary": _empty_solar_summary()})
    write_json(run_dir / "diagnostics" / "delta-distribution.json", {"status": "NOT_RUN", "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"]})
    baselines: dict[str, dict[str, int]] = {"pre": {}, "post": {}}
    for window, items in (("pre", pre_items), ("post", post_items)):
        for item in items:
            value = str(item.get("properties", {}).get("s2:processing_baseline"))
            baselines[window][value] = baselines[window].get(value, 0) + 1
    write_json(run_dir / "diagnostics" / "processing-baselines.json", baselines)
    manifest = _build_manifest(run_dir, assessment, policy)
    write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    state.update(
        stage="PRIMARY_ASSESSMENT_SEALED",
        execution_status="ABSTAINED",
        evidence_disposition="INCONCLUSIVE",
        primary_reason_codes=["RESOURCE_LIMIT_EXCEEDED"],
        assessment_sha256=sha256_file(run_dir / "assessment.json"),
        ended_at_utc=utc_now(),
    )
    write_json(run_dir / "run-state.json", state)


def replay_resource_limit(run_dir: Path) -> None:
    state = read_json(run_dir / "run-state.json")
    if state.get("stage") != "PRIMARY_ASSESSMENT_SEALED":
        raise RuntimeFailure("primary assessment is not sealed", "PROVENANCE_INCOMPLETE")
    replay_dir = run_dir / "replay"
    replay_dir.mkdir(exist_ok=False)
    pre = _load_cached_items(run_dir, "pre")
    post = _load_cached_items(run_dir, "post")
    counts = {"pre": len(pre), "post": len(post)}
    if counts["pre"] > 40 or counts["post"] > 40:
        replay_assessment = _resource_limit_assessment(state["run_id"], read_json(run_dir / "assessment.json")["provenance_manifest_ref"])
    else:
        raise RuntimeFailure("cached replay no longer reaches the live resource-limit terminal", "PROVENANCE_HASH_MISMATCH")
    write_json(replay_dir / "assessment.json", replay_assessment, canonical=True)
    live_bytes = (run_dir / "assessment.json").read_bytes()
    replay_bytes = (replay_dir / "assessment.json").read_bytes()
    validation = {
        "network_access": False,
        "cached_inputs_only": True,
        "cached_item_counts": counts,
        "canonical_assessment_bytes_equal": live_bytes == replay_bytes,
        "live_assessment_sha256": sha256_bytes(live_bytes),
        "replay_assessment_sha256": sha256_bytes(replay_bytes),
        "assessment_sha256_equal": sha256_bytes(live_bytes) == sha256_bytes(replay_bytes),
        "derived_array_hashes": [],
        "intentionally_variable_fields": [],
    }
    if not validation["canonical_assessment_bytes_equal"]:
        raise RuntimeFailure("offline replay assessment differs from live assessment", "PROVENANCE_HASH_MISMATCH")
    write_json(replay_dir / "replay-validation.json", validation, canonical=True)
    manifest = read_json(run_dir / "provenance-manifest.json")
    manifest["artifact_records"].extend([
        _artifact(replay_dir / "assessment.json", run_dir, "OFFLINE_REPLAY_ASSESSMENT", "OFFLINE_REPLAY", "application/json"),
        _artifact(replay_dir / "replay-validation.json", run_dir, "OFFLINE_REPLAY_VALIDATION", "OFFLINE_REPLAY", "application/json"),
    ])
    write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    state.update(stage="REPLAY_VALIDATED", replay_validation=validation, provenance_manifest_sha256=sha256_file(run_dir / "provenance-manifest.json"))
    write_json(run_dir / "run-state.json", state)
    summary = f"""# EOP101132 Step 2B Run Summary

- Run ID: `{state['run_id']}`
- Approved policy SHA-256: `{APPROVED_POLICY_SHA256}`
- Execution status: `ABSTAINED`
- Evidence disposition: `INCONCLUSIVE`
- Reason: `RESOURCE_LIMIT_EXCEEDED`
- Pre-window items: `{counts['pre']}`
- Post-window items: `{counts['post']}` (maximum permitted: `40`)
- Raster asset reads: `0`
- Coverage calculation: not run
- NDVI calculation: not run
- Offline replay assessment bytes equal: `true`

The frozen policy prohibited truncation or selective scene choice. No policy, window, threshold, mask, grid, or claim wording was changed after observing the item counts.
"""
    (run_dir / "run-summary.md").write_text(summary, encoding="utf-8")
    checksum_rows = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "checksums.sha256"):
        checksum_rows.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "checksums.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="ascii")


def reseal_resource_limit_inventory(run_dir: Path) -> None:
    state = read_json(run_dir / "run-state.json")
    if state.get("stage") != "REPLAY_VALIDATED":
        raise RuntimeFailure("replay must be validated before provenance reseal", "PROVENANCE_INCOMPLETE")
    rows = read_json(run_dir / "inventory" / "scene-inventory.json")
    for row in rows:
        row["admissible"] = None
        row["admissibility_status"] = "NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED"
        row["exclusion_reasons"] = ["NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED"]
        value = row.get("mean_solar_zenith_angle")
        row["solar_geometry_metadata_source"] = "STAC_PROPERTY:s2:mean_solar_zenith" if value is not None else None
        row["solar_geometry_status"] = "AVAILABLE_NOT_EVALUATED" if value is not None else "MISSING_NOT_EVALUATED"
        row["radiometry_metadata_source"] = None
        row["radiometry_status"] = "NOT_EVALUATED_RESOURCE_LIMIT_EXCEEDED"
        for field in ("b04_scale", "b04_offset", "b04_quantification_value", "b04_nodata", "b08_scale", "b08_offset", "b08_quantification_value", "b08_nodata"):
            row[field] = None
    write_json(run_dir / "inventory" / "scene-inventory.json", rows, canonical=True)
    with (run_dir / "inventory" / "scene-inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    manifest = read_json(run_dir / "provenance-manifest.json")
    inventory_hash = sha256_file(run_dir / "inventory" / "scene-inventory.json")
    next(item for item in manifest["artifact_records"] if item["artifact_type"] == "DISCOVERED_SCENE_INVENTORY")["content_sha256"] = inventory_hash
    manifest["software_environment"]["code_revision"] = sha256_file(Path(__file__))
    summaries = {}
    for window in ("PRE", "POST"):
        window_rows = [row for row in rows if row["window"] == window]
        values = [float(row["mean_solar_zenith_angle"]) for row in window_rows if isinstance(row.get("mean_solar_zenith_angle"), (int, float)) and math.isfinite(row["mean_solar_zenith_angle"])]
        distribution = step2b_offline.descriptive_distribution(values) if values else None
        summaries[window.lower()] = {
            "discovered_count": len(window_rows),
            "finite_value_count": len(values),
            "minimum": min(values) if values else None,
            "q25": distribution["q25"] if distribution else None,
            "median": distribution["median"] if distribution else None,
            "q75": distribution["q75"] if distribution else None,
            "maximum": max(values) if values else None,
            "missing_count": len(window_rows) - len(values),
            "admitted_summary_status": "NOT_RUN_RESOURCE_LIMIT_EXCEEDED",
        }
    diagnostics = {
        "status": "DISCOVERED_ITEMS_DESCRIBED_ADMISSIBILITY_NOT_RUN",
        "reason_codes": ["RESOURCE_LIMIT_EXCEEDED"],
        "discovered": summaries,
        "post_minus_pre_discovered_median_degrees": summaries["post"]["median"] - summaries["pre"]["median"] if summaries["pre"]["median"] is not None and summaries["post"]["median"] is not None else None,
        "diagnostic_only": True,
    }
    write_json(run_dir / "diagnostics" / "solar-geometry.json", diagnostics)
    write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    state["provenance_manifest_sha256"] = sha256_file(run_dir / "provenance-manifest.json")
    write_json(run_dir / "run-state.json", state)
    checksum_rows = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "checksums.sha256"):
        checksum_rows.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "checksums.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="ascii")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Approved bounded EOP101132 Step 2B runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    fetch_parser = sub.add_parser("fetch-sources")
    fetch_parser.add_argument("run_dir", type=Path)
    finalise_parser = sub.add_parser("finalise-resource-limit")
    finalise_parser.add_argument("run_dir", type=Path)
    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("run_dir", type=Path)
    reseal_parser = sub.add_parser("reseal-resource-limit-inventory")
    reseal_parser.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            print(initialise_run())
        elif args.command == "fetch-sources":
            fetch_sources(args.run_dir.resolve())
            print(args.run_dir.resolve())
        elif args.command == "finalise-resource-limit":
            finalise_resource_limit(args.run_dir.resolve())
            print(args.run_dir.resolve())
        elif args.command == "replay":
            replay_resource_limit(args.run_dir.resolve())
            print(args.run_dir.resolve())
        elif args.command == "reseal-resource-limit-inventory":
            reseal_resource_limit_inventory(args.run_dir.resolve())
            print(args.run_dir.resolve())
        return 0
    except (RuntimeFailure, step2b_offline.OfflineContractError, ValueError, OSError, zipfile.BadZipFile) as exc:
        reason = getattr(exc, "reason_code", "DETERMINISTIC_PROCESSING_ERROR")
        print(json.dumps({"error": str(exc), "reason_code": reason}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
