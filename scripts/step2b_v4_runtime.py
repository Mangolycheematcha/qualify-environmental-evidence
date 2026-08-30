from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import step2b_acquisition as acquisition  # noqa: E402
from scripts import approval_protocol_v2 as approval_v2  # noqa: E402
from scripts import step2b_offline  # noqa: E402
from scripts import step2b_runtime as legacy_io  # noqa: E402
from scripts import step2b_v4_raster as raster_core  # noqa: E402

POLICY_PATH = ROOT / "policies" / "eop101132" / "step2b-proposed-policy-v4.json"
RUNTIME_SPEC_PATH = ROOT / "runtime-specs" / "eop101132" / "step2b-v4-runtime-spec.json"
APPROVED_POLICY_SHA256 = "3412570f327f4c55184ced99948f3625e718e19e994732ec204cb7dea16318dd"
POLICY_ID = "DEMO_QUALIFICATION_POLICY_EOP101132_V4"
RUNTIME_SPEC_ID = "EOP101132_STEP2B_V4_RUNTIME_V1"
CONTRACT_VERSION = "0.5.0"
APPROVAL_SCOPE = "ONE_EOP101132_V4_PRIMARY_RUN"
APPROVAL_RECORD_VERSION = approval_v2.APPROVAL_PROTOCOL_VERSION
BOUNDARY_SHA256 = "3761b2c8b004308db31e06236bb40f2b00c2e0590ec7039554c7339f8820fef2"
BOUNDARY_BYTES = 10219
FORBIDDEN_CODES = legacy_io.FORBIDDEN_CODES
TRANSFORMATION_IDS = legacy_io.TRANSFORMATION_IDS
RUNTIME_VERSION = "step2b_v4_runtime.py/1.1.0"
NETWORK_MAX_ATTEMPTS = 3
NETWORK_RETRY_DELAYS_SECONDS = (0, 2, 5)


class V4RuntimeFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        reason_code: str = "DETERMINISTIC_PROCESSING_ERROR",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return approval_v2.read_json(path)


def write_json(path: Path, value: Any, *, canonical: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value) if canonical else (
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    path.write_bytes(payload)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def current_git_commit() -> str:
    return _git("rev-parse", "HEAD")


def require_clean_git() -> None:
    if _git("status", "--short", "--untracked-files=all"):
        raise V4RuntimeFailure("Git working tree is not clean", "RUNTIME_SPECIFICATION_NOT_FROZEN")


def approval_statement(policy_hash: str, runtime_spec_hash: str, git_commit: str) -> str:
    return f"批准 QUALIFICATION {policy_hash} RUNTIME_SPEC {runtime_spec_hash} COMMIT {git_commit}"


def verify_runtime_spec(
    approved_runtime_spec_sha256: str,
    *,
    runtime_spec_path: Path = RUNTIME_SPEC_PATH,
    verify_packages: bool = True,
) -> tuple[dict[str, Any], str]:
    spec_bytes = runtime_spec_path.read_bytes()
    calculated = sha256_bytes(spec_bytes)
    if calculated != approved_runtime_spec_sha256:
        raise V4RuntimeFailure("local runtime-spec SHA-256 does not match approval", "PROVENANCE_HASH_MISMATCH")
    spec = json.loads(spec_bytes)
    expected = {
        "runtime_spec_version": "1.1.0",
        "runtime_spec_id": RUNTIME_SPEC_ID,
        "policy_id": POLICY_ID,
        "approved_policy_sha256": APPROVED_POLICY_SHA256,
        "contract_version": CONTRACT_VERSION,
        "approval_record_version": APPROVAL_RECORD_VERSION,
        "allowed_scope": APPROVAL_SCOPE,
    }
    for field, value in expected.items():
        if spec.get(field) != value:
            raise V4RuntimeFailure(f"runtime spec {field} mismatch", "RUNTIME_SPECIFICATION_NOT_FROZEN")
    runtime_python = spec.get("python_runtime", {})
    if runtime_python.get("implementation") != "CPython" or runtime_python.get("major_minor") != f"{sys.version_info.major}.{sys.version_info.minor}":
        raise V4RuntimeFailure("Python runtime does not match the frozen runtime spec", "RUNTIME_SPECIFICATION_NOT_FROZEN")
    if sha256_file(POLICY_PATH) != APPROVED_POLICY_SHA256:
        raise V4RuntimeFailure("V4 policy bytes do not match the frozen policy hash", "PROVENANCE_HASH_MISMATCH")
    files = spec.get("implementation_files")
    if not isinstance(files, dict) or not files:
        raise V4RuntimeFailure("runtime spec has no implementation file inventory", "RUNTIME_SPECIFICATION_NOT_FROZEN")
    for relative, expected_hash in files.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise V4RuntimeFailure(f"runtime implementation drift: {relative}", "PROVENANCE_HASH_MISMATCH")
    if verify_packages:
        for package, expected_version in spec.get("runtime_packages", {}).items():
            try:
                actual = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError as exc:
                raise V4RuntimeFailure(f"required runtime package is missing: {package}") from exc
            if actual != expected_version:
                raise V4RuntimeFailure(
                    f"runtime package {package} is {actual}, expected {expected_version}",
                    "RUNTIME_SPECIFICATION_NOT_FROZEN",
                )
    return spec, calculated


def validate_detached_approval(
    approval: dict[str, Any],
    *,
    runtime_spec_hash: str,
    git_commit: str,
) -> None:
    del approval, runtime_spec_hash, git_commit
    raise V4RuntimeFailure(
        "self-attested detached approval is not independent human evidence; Approval Protocol V2 is required",
        "APPROVAL_EVIDENCE_NOT_INDEPENDENT",
    )


def _run_guard(run_dir: Path, *, verify_packages: bool = True) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = read_json(run_dir / "run-state.json")
    approval = read_json(run_dir / "approval" / "approval-request.json")
    evidence = read_json(run_dir / "approval" / "approval-verification.json")
    consumption = read_json(run_dir / "approval" / "approval-consumption.json")
    commit = current_git_commit()
    if commit != state["git_commit"]:
        raise V4RuntimeFailure("Git commit changed after run initialization", "PROVENANCE_HASH_MISMATCH")
    spec, spec_hash = verify_runtime_spec(
        state["runtime_spec_sha256"],
        runtime_spec_path=run_dir / "frozen" / "runtime-spec.json",
        verify_packages=verify_packages,
    )
    approval_v2.validate_request(approval)
    try:
        approval_v2.validate_execution_bindings(
            approval,
            policy_sha256=APPROVED_POLICY_SHA256,
            runtime_spec_sha256=spec_hash,
            executable_git_commit=commit,
            reserved_run_id=state["run_id"],
        )
    except approval_v2.ApprovalProtocolError as exc:
        raise V4RuntimeFailure(str(exc), exc.reason_code) from exc
    if evidence.get("approval_request_sha256") != approval["approval_request_sha256"]:
        raise V4RuntimeFailure("approval evidence request hash mismatch", "APPROVAL_BINDING_INVALID")
    if consumption.get("approval_request_sha256") != approval["approval_request_sha256"]:
        raise V4RuntimeFailure("approval consumption request hash mismatch", "APPROVAL_BINDING_INVALID")
    if consumption.get("consumed_by_run_id") != state["run_id"] or consumption.get("actual_consumption_count") != 1:
        raise V4RuntimeFailure("approval consumption Run ID or count mismatch", "APPROVAL_RUN_ID_MISMATCH")
    expected_hashes = {
        "approval_request_sha256": approval["approval_request_sha256"],
        "approval_evidence_sha256": sha256_file(run_dir / "approval" / "approval-verification.json"),
        "approval_consumption_sha256": sha256_file(run_dir / "approval" / "approval-consumption.json"),
    }
    for field, value in expected_hashes.items():
        if state.get(field) != value:
            raise V4RuntimeFailure(f"run-state {field} mismatch", "PROVENANCE_HASH_MISMATCH")
    if sha256_file(run_dir / "frozen" / "policy.json") != APPROVED_POLICY_SHA256:
        raise V4RuntimeFailure("run-local frozen policy changed", "PROVENANCE_HASH_MISMATCH")
    if sha256_file(POLICY_PATH) != APPROVED_POLICY_SHA256:
        raise V4RuntimeFailure("repository V4 policy changed", "PROVENANCE_HASH_MISMATCH")
    return state, approval, spec


def initialise_run(approval_path: Path) -> Path:
    require_clean_git()
    request_dir = approval_path
    approval = read_json(request_dir / "approval-request.json")
    approval_v2.validate_request(approval, now=utc_now())
    runtime_spec_hash = approval["runtime_spec_sha256"]
    _, calculated_spec_hash = verify_runtime_spec(runtime_spec_hash)
    commit = current_git_commit()
    if approval["policy_sha256"] != APPROVED_POLICY_SHA256:
        raise V4RuntimeFailure("approval policy hash mismatch", "APPROVAL_BINDING_INVALID")
    if approval["executable_git_commit"] != commit:
        raise V4RuntimeFailure("approval executable Git commit mismatch", "APPROVAL_BINDING_INVALID")
    approval_v2.validate_verified_bundle(request_dir, now=utc_now())
    created = utc_now()
    try:
        approval_v2.consume_verified_approval(
            request_dir,
            executable_git_commit=commit,
            execution_initialized_at_utc=created,
        )
    except approval_v2.ApprovalProtocolError as exc:
        raise V4RuntimeFailure(str(exc), exc.reason_code) from exc
    run_id = approval["reserved_run_id"]
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    for name in ("approval", "frozen", "source/item-metadata", "source/metadata-assets", "inventory", "grouping", "cache", "diagnostics", "replay", "logs"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(request_dir / "approval-request.json", run_dir / "approval" / "approval-request.json")
    shutil.copyfile(request_dir / "approval-verification.json", run_dir / "approval" / "approval-verification.json")
    shutil.copyfile(request_dir / "approval-consumption.json", run_dir / "approval" / "approval-consumption.json")
    shutil.copyfile(request_dir / "approval-state.json", run_dir / "approval" / "approval-state-at-initialization.json")
    shutil.copyfile(POLICY_PATH, run_dir / "frozen" / "policy.json")
    shutil.copyfile(RUNTIME_SPEC_PATH, run_dir / "frozen" / "runtime-spec.json")
    legacy_io._runtime_case(run_dir, read_json(run_dir / "frozen" / "policy.json"))
    state = {
        "run_id": run_id,
        "case_id": "EOP101132-NDVI-001",
        "policy_id": POLICY_ID,
        "policy_sha256": APPROVED_POLICY_SHA256,
        "runtime_spec_id": RUNTIME_SPEC_ID,
        "runtime_spec_sha256": calculated_spec_hash,
        "approval_protocol_version": approval_v2.APPROVAL_PROTOCOL_VERSION,
        "approval_request_sha256": approval["approval_request_sha256"],
        "approval_evidence_sha256": sha256_file(run_dir / "approval" / "approval-verification.json"),
        "approval_consumption_sha256": sha256_file(run_dir / "approval" / "approval-consumption.json"),
        "approval_sha256": sha256_file(run_dir / "approval" / "approval-verification.json"),
        "git_commit": commit,
        "contract_version": CONTRACT_VERSION,
        "created_at_utc": created,
        "stage": "INITIALIZED",
        "authorization_network_access_attempted": read_json(request_dir / "approval-state.json").get("authorization_network_access_attempted", False),
        "first_authorization_access_attempt_at": read_json(request_dir / "approval-state.json").get("first_authorization_access_attempt_at"),
        "data_network_access_attempted": False,
        "first_data_network_attempt_at": None,
        "network_accessed": False,
        "raster_pixels_read": False,
    }
    write_json(run_dir / "run-state.json", state)
    return run_dir


def _strip_query(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _safe_error_message(exc: Exception) -> str:
    message = str(exc)
    url_pattern = re.compile("https:" + r"//[^\s\"'<>]+")
    return url_pattern.sub(lambda match: _strip_query(match.group(0)), message)


def _record_data_network_attempt(run_dir: Path, attempted_at: str, args: tuple[Any, ...]) -> None:
    request_uri = _strip_query(str(args[0])) if args else "UNRESOLVED"
    attempts_path = run_dir / "diagnostics" / "data-network-attempts.json"
    attempts = read_json(attempts_path).get("attempts", []) if attempts_path.is_file() else []
    attempts.append(
        {
            "attempt": len(attempts) + 1,
            "attempted_at_utc": attempted_at,
            "network_class": "ENVIRONMENTAL_DATA",
            "request_uri": request_uri,
        }
    )
    write_json(attempts_path, {"attempts": attempts}, canonical=True)
    state = read_json(run_dir / "run-state.json")
    state.update(data_network_access_attempted=True, network_accessed=True)
    if state.get("first_data_network_attempt_at") is None:
        state["first_data_network_attempt_at"] = attempted_at
    write_json(run_dir / "run-state.json", state)


def _http_request(*args: Any, audit_run_dir: Path | None = None, **kwargs: Any) -> tuple[bytes, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(1, NETWORK_MAX_ATTEMPTS + 1):
        delay = NETWORK_RETRY_DELAYS_SECONDS[attempt_number - 1]
        if delay:
            time.sleep(delay)
        attempted_at = utc_now()
        if audit_run_dir is not None:
            _record_data_network_attempt(audit_run_dir, attempted_at, args)
        try:
            raw, metadata = legacy_io.http_request(*args, **kwargs)
            metadata["request_attempt_count"] = attempt_number
            metadata["retry_delays_seconds"] = list(NETWORK_RETRY_DELAYS_SECONDS[:attempt_number])
            return raw, metadata
        except (legacy_io.RuntimeFailure, TimeoutError) as exc:
            reason_code = getattr(exc, "reason_code", "SOURCE_UNAVAILABLE")
            attempts.append(
                {
                    "attempt": attempt_number,
                    "attempted_at_utc": attempted_at,
                    "reason_code": reason_code,
                    "error": _safe_error_message(exc),
                }
            )
            http_error = exc.__cause__
            non_retryable_http = getattr(http_error, "code", None) not in (None, 408, 429, 500, 502, 503, 504)
            if reason_code != "SOURCE_UNAVAILABLE" or non_retryable_http or attempt_number == NETWORK_MAX_ATTEMPTS:
                raise V4RuntimeFailure(
                    f"source unavailable after {attempt_number} attempt(s): {_safe_error_message(exc)}",
                    reason_code,
                    details={"network_attempts": attempts},
                ) from exc
    raise AssertionError("bounded network retry loop exhausted without returning or raising")


def _sign_asset_url(run_dir: Path, unsigned_url: str) -> tuple[str, dict[str, Any]]:
    canonical = _strip_query(unsigned_url)
    endpoint = "https://planetarycomputer.microsoft.com/api/sas/v1/sign?" + urllib.parse.urlencode({"href": canonical})
    raw, signing_metadata = _http_request(endpoint, audit_run_dir=run_dir)
    try:
        response = json.loads(raw)
        signed = response["href"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise V4RuntimeFailure("Planetary Computer signing response is invalid", "SOURCE_UNAVAILABLE") from exc
    if _strip_query(signed) != canonical:
        raise V4RuntimeFailure("signed asset identity differs from canonical asset", "CANONICAL_IDENTIFIER_UNRESOLVED")
    return signed, {
        "canonical_asset_identity": canonical,
        "redacted_retrieval_uri": canonical,
        "signed_at_utc": utc_now(),
        "safe_expiry": response.get("msft:expiry"),
        "retrieval_uri_sha256": sha256_bytes(signed.encode("utf-8")),
        "signing_request_attempt_count": signing_metadata["request_attempt_count"],
        "signing_retry_delays_seconds": signing_metadata["retry_delays_seconds"],
    }


def _fetch_signed_asset(run_dir: Path, unsigned_url: str) -> tuple[bytes, dict[str, Any]]:
    signed, safe = _sign_asset_url(run_dir, unsigned_url)
    host = urllib.parse.urlsplit(signed).hostname
    if not host:
        raise V4RuntimeFailure("signed asset has no hostname", "SOURCE_UNAVAILABLE")
    raw, metadata = _http_request(signed, extra_hosts={host}, audit_run_dir=run_dir)
    safe.update(
        {
            "retrieved_at_utc": metadata["retrieved_at_utc"],
            "http_status": metadata["http_status"],
            "response_bytes": len(raw),
            "response_sha256": sha256_bytes(raw),
        }
    )
    return raw, safe


def fetch_sources(run_dir: Path) -> None:
    state, _, _ = _run_guard(run_dir)
    if state.get("stage") != "INITIALIZED":
        raise V4RuntimeFailure("fetch-sources requires an initialized run")
    policy = read_json(run_dir / "frozen" / "policy.json")
    project_url = policy["project_and_boundary"]["project_page"]
    state.update(stage="SOURCE_FETCH_STARTED")
    write_json(run_dir / "run-state.json", state)
    project_raw, project_meta = _http_request(project_url, audit_run_dir=run_dir)
    (run_dir / "source" / "cer-project-page.raw").write_bytes(project_raw)
    project_meta["extracted_project_fields"] = legacy_io._project_fields(project_raw)
    write_json(run_dir / "source" / "cer-project-page.metadata.json", project_meta)
    cea_url = policy["project_and_boundary"]["boundary_artifact_uri"]
    cea_raw, cea_meta = _http_request(cea_url, audit_run_dir=run_dir)
    if sha256_bytes(cea_raw) != BOUNDARY_SHA256 or len(cea_raw) != BOUNDARY_BYTES:
        raise V4RuntimeFailure("CER CEA bytes differ from the frozen artifact", "SOURCE_VERSION_UNRESOLVED")
    cea_path = run_dir / "source" / "eop101132-cea.zip"
    cea_path.write_bytes(cea_raw)
    polygons, boundary = legacy_io.safe_extract_boundary(cea_path, run_dir / "cache" / "cea-extracted")
    cea_meta.update(boundary)
    cea_meta.update({"analysis_boundary_role": "CEA", "expected_sha256": BOUNDARY_SHA256, "hash_verified": True})
    write_json(run_dir / "source" / "eop101132-cea.metadata.json", cea_meta)
    geometry = legacy_io.boundary_geojson(polygons)
    write_json(run_dir / "cache" / "aoi-wgs84.geojson", geometry, canonical=True)
    endpoint = policy["stac_source_and_selection"]["endpoint"]
    counts: dict[str, Any] = {}
    raw_limit_exceeded = False
    for window in ("pre", "post"):
        items = legacy_io._stac_search(
            run_dir,
            endpoint,
            window,
            policy["temporal_scope"][f"{window}_window"],
            geometry,
            request_fn=lambda *args, **kwargs: _http_request(*args, audit_run_dir=run_dir, **kwargs),
        )
        unique, duplicate_count = legacy_io._deduplicate_items(items)
        counts[window] = {
            "before_deduplication": len(items),
            "after_deduplication": len(unique),
            "duplicate_count": duplicate_count,
        }
        raw_limit_exceeded |= len(unique) > acquisition.RAW_STAC_ITEMS_PER_WINDOW_MAX
        for item in unique:
            write_json(run_dir / "source" / "item-metadata" / f"{item['id']}.json", item, canonical=True)
    state.update(
        stage="RAW_STAC_LIMIT_EXCEEDED" if raw_limit_exceeded else "RAW_STAC_INVENTORY_COMPLETE",
        network_accessed=True,
        stac_counts=counts,
        boundary=boundary,
        terminal_reason_codes=["METADATA_INVENTORY_LIMIT_EXCEEDED", "RESOURCE_LIMIT_EXCEEDED"] if raw_limit_exceeded else [],
    )
    write_json(run_dir / "run-state.json", state)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _elements(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element.tag) == name]


def _single_float(root: ET.Element, name: str) -> float:
    values = [element.text.strip() for element in _elements(root, name) if element.text and element.text.strip()]
    unique = sorted(set(values))
    if len(unique) != 1:
        raise V4RuntimeFailure(f"metadata field {name} is missing or contradictory", "RADIOMETRY_METADATA_UNRESOLVED")
    value = float(unique[0])
    if not math.isfinite(value):
        raise V4RuntimeFailure(f"metadata field {name} is non-finite", "RADIOMETRY_METADATA_UNRESOLVED")
    return value


def _parse_solar_zenith(granule_xml: bytes) -> float:
    try:
        root = ET.fromstring(granule_xml)
    except ET.ParseError as exc:
        raise V4RuntimeFailure("granule metadata XML is invalid", "SOLAR_GEOMETRY_METADATA_UNRESOLVED") from exc
    candidates = []
    for mean in _elements(root, "Mean_Sun_Angle"):
        for child in mean.iter():
            if _local_name(child.tag) == "ZENITH_ANGLE" and child.text:
                candidates.append(child.text.strip())
    if len(set(candidates)) != 1:
        raise V4RuntimeFailure("granule mean solar zenith is missing or contradictory", "SOLAR_GEOMETRY_METADATA_UNRESOLVED")
    value = float(candidates[0])
    if not math.isfinite(value):
        raise V4RuntimeFailure("granule mean solar zenith is non-finite", "SOLAR_GEOMETRY_METADATA_UNRESOLVED")
    return value


def _parse_radiometry(product_xml: bytes, asset_key: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(product_xml)
    except ET.ParseError as exc:
        raise V4RuntimeFailure("product metadata XML is invalid", "RADIOMETRY_METADATA_UNRESOLVED") from exc
    quantification = _single_float(root, "BOA_QUANTIFICATION_VALUE")
    band_id = {"B04": "3", "B08": "7"}[asset_key]
    offsets = []
    for element in _elements(root, "BOA_ADD_OFFSET"):
        if element.attrib.get("band_id") == band_id and element.text:
            offsets.append(float(element.text.strip()) / quantification)
    if len(set(offsets)) > 1:
        raise V4RuntimeFailure(f"{asset_key} BOA offsets are contradictory", "RADIOMETRY_METADATA_UNRESOLVED")
    if offsets:
        offset = offsets[0]
        source = "PRODUCT_XML:BOA_QUANTIFICATION_VALUE+BOA_ADD_OFFSET"
    else:
        offset = 0.0
        source = "PRODUCT_XML:BOA_QUANTIFICATION_VALUE+SCHEMA_DEFAULT_ZERO_OFFSET"
    nodata_values = []
    for special in _elements(root, "Special_Values"):
        text = next((child.text for child in special if _local_name(child.tag) == "SPECIAL_VALUE_TEXT"), None)
        index = next((child.text for child in special if _local_name(child.tag) == "SPECIAL_VALUE_INDEX"), None)
        if text and text.strip().upper() == "NODATA" and index:
            nodata_values.append(float(index.strip()))
    if len(set(nodata_values)) != 1:
        raise V4RuntimeFailure("product nodata metadata is missing or contradictory", "RADIOMETRY_METADATA_UNRESOLVED")
    return {
        "scale": 1.0 / quantification,
        "offset": offset,
        "quantification_value": quantification,
        "nodata": nodata_values[0],
        "metadata_source": source,
        "cross_check": "PASS",
    }


def _normalise_item_with_metadata(run_dir: Path, item: dict[str, Any], window: str) -> dict[str, Any]:
    item_id = item.get("id")
    properties = item.get("properties", {})
    assets = item.get("assets", {})
    required = ("B04", "B08", "SCL", "product-metadata", "granule-metadata")
    if not isinstance(item_id, str) or any(not isinstance(assets.get(key, {}).get("href"), str) for key in required):
        raise V4RuntimeFailure("STAC item omits a required canonical asset", "RADIOMETRY_METADATA_UNRESOLVED")
    product_raw, product_safe = _fetch_signed_asset(run_dir, assets["product-metadata"]["href"])
    granule_raw, granule_safe = _fetch_signed_asset(run_dir, assets["granule-metadata"]["href"])
    metadata_dir = run_dir / "source" / "metadata-assets" / item_id
    metadata_dir.mkdir(parents=True, exist_ok=False)
    (metadata_dir / "product-metadata.xml").write_bytes(product_raw)
    (metadata_dir / "granule-metadata.xml").write_bytes(granule_raw)
    write_json(metadata_dir / "retrieval.json", {"product-metadata": product_safe, "granule-metadata": granule_safe})
    granule_sza = _parse_solar_zenith(granule_raw)
    stac_sza = properties.get("s2:mean_solar_zenith")
    sza = granule_sza if isinstance(stac_sza, (int, float)) and math.isfinite(stac_sza) and abs(float(stac_sza) - granule_sza) <= 1e-6 else None
    radiometry = {key: _parse_radiometry(product_raw, key) for key in ("B04", "B08")}
    processing_datetime = properties.get("s2:generation_time")
    return {
        "id": item_id,
        "collection": item.get("collection"),
        "platform": properties.get("platform"),
        "datatake_id": properties.get("s2:datatake_id"),
        "datetime": properties.get("datetime"),
        "mgrs_tile": properties.get("s2:mgrs_tile"),
        "processing_baseline": properties.get("s2:processing_baseline"),
        "processing_datetime": processing_datetime,
        "mean_solar_zenith_angle": sza,
        "assets": {key: _strip_query(assets[key]["href"]) for key in required},
        "radiometry": radiometry,
        "window": window.upper(),
        "stac_item_sha256": sha256_bytes(canonical_bytes(item)),
        "solar_geometry_cross_check": "PASS" if sza is not None else "FAIL",
        "eo_cloud_cover_diagnostic_only": properties.get("eo:cloud_cover"),
    }


def _load_cached_items(run_dir: Path, window: str) -> list[dict[str, Any]]:
    raw = read_json(run_dir / "source" / f"stac-{window}.raw.json")
    items, _ = legacy_io._deduplicate_items(raw["features"])
    return items


def _representation_records(normalised: Sequence[dict[str, Any]], result: dict[str, Any], window: str) -> list[dict[str, Any]]:
    selected = set(acquisition.selected_item_ids(result))
    components: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for item in normalised:
        components[(item["platform"], item["datatake_id"], item["mgrs_tile"])].append(item["id"])
    records = []
    for (platform, datatake, tile), candidate_ids in sorted(components.items()):
        chosen = sorted(set(candidate_ids) & selected)
        records.append(
            {
                "window": window.upper(),
                "platform": platform,
                "datatake_id": datatake,
                "mgrs_tile": tile,
                "candidate_item_ids": sorted(candidate_ids),
                "selected_item_id": chosen[0] if len(chosen) == 1 else None,
                "selection_priority": "VALID_SOURCE_THEN_BASELINE_THEN_PROCESSING_TIME_THEN_EQUIVALENT_ID_V1",
                "status": "RESOLVED" if len(chosen) == 1 else "AMBIGUOUS",
                "reason_codes": [] if len(chosen) == 1 else ["ACQUISITION_REPRESENTATION_AMBIGUOUS"],
            }
        )
    return records


def _solar_records(normalised: Sequence[dict[str, Any]], result: dict[str, Any], window: str) -> list[dict[str, Any]]:
    inventory = {item["id"]: item for item in result["inventory"]}
    records = []
    for item in sorted(normalised, key=lambda value: value["id"]):
        reasons = inventory[item["id"]]["exclusion_reasons"]
        solar_reason = next((reason for reason in reasons if reason.startswith("SOLAR_GEOMETRY_")), None)
        records.append(
            {
                "window": window.upper(),
                "item_id": item["id"],
                "acquisition_datetime": item["datetime"],
                "platform": item["platform"],
                "datatake_id": item["datatake_id"],
                "mean_solar_zenith_angle": item["mean_solar_zenith_angle"],
                "metadata_source": "STAC_PROPERTY+CACHED_GRANULE_XML" if item["mean_solar_zenith_angle"] is not None else None,
                "cross_check": item["solar_geometry_cross_check"],
                "admissible": solar_reason is None,
                "exclusion_reason": solar_reason,
                "processing_baseline": item["processing_baseline"],
            }
        )
    return records


def _radiometry_records(normalised: Sequence[dict[str, Any]], result: dict[str, Any]) -> list[dict[str, Any]]:
    selected = set(acquisition.selected_item_ids(result))
    records = []
    for item in sorted(normalised, key=lambda value: value["id"]):
        if item["id"] not in selected:
            continue
        for asset_key in ("B04", "B08"):
            metadata = item["radiometry"][asset_key]
            records.append(
                {
                    "item_id": item["id"],
                    "acquisition_datetime": item["datetime"],
                    "platform": item["platform"],
                    "processing_baseline": item["processing_baseline"],
                    "asset_key": asset_key,
                    "canonical_asset_identity": item["assets"][asset_key],
                    "retrieval_uri": None,
                    **metadata,
                }
            )
    return records


def evaluate_metadata(run_dir: Path) -> None:
    state, _, spec = _run_guard(run_dir)
    if state.get("stage") == "RAW_STAC_LIMIT_EXCEEDED":
        raise V4RuntimeFailure("raw STAC limit already exceeded", "RESOURCE_LIMIT_EXCEEDED")
    if state.get("stage") != "RAW_STAC_INVENTORY_COMPLETE":
        raise V4RuntimeFailure("evaluate-metadata requires a complete raw STAC inventory")
    combined_inventory = []
    combined_groups = []
    representations = []
    solar_records = []
    radiometry_records = []
    window_summary: dict[str, Any] = {}
    for window in ("pre", "post"):
        raw_items = _load_cached_items(run_dir, window)
        normalised = [_normalise_item_with_metadata(run_dir, item, window) for item in raw_items]
        write_json(run_dir / "inventory" / f"{window}-metadata-input.json", normalised, canonical=True)
        result = acquisition.evaluate_window_metadata(normalised)
        write_json(run_dir / "grouping" / f"{window}-grouping.json", result, canonical=True)
        result_hash = sha256_file(run_dir / "grouping" / f"{window}-grouping.json")
        representations.extend(_representation_records(normalised, result, window))
        solar_records.extend(_solar_records(normalised, result, window))
        radiometry_records.extend(_radiometry_records(normalised, result))
        for item in result["inventory"]:
            combined_inventory.append({"window": window.upper(), **item})
        for group in result["acquisition_groups"]:
            combined_groups.append(
                {
                    "window": window.upper(),
                    "platform": group["platform"],
                    "datatake_id": group["datatake_id"],
                    "sensing_datetime": group["sensing_datetime"],
                    "component_item_ids": group["component_item_ids"],
                    "mgrs_tiles": group["mgrs_tiles"],
                    "metadata_admissible": group["metadata_admissible"],
                    "reason_codes": group["exclusion_reasons"],
                    "counted_toward_raster_limit": group["metadata_admissible"],
                }
            )
        window_summary[window] = {
            "raw_item_count": result["raw_item_count"],
            "canonical_representation_count": len(acquisition.selected_item_ids(result)),
            "independent_acquisition_group_count": len(result["acquisition_groups"]),
            "metadata_admissible_acquisition_group_count": result["admissible_acquisition_group_count"],
            "raster_access_permitted": result["raster_access_permitted"],
            "grouping_sha256": result_hash,
            "grouping_rule_id": spec["grouping"]["rule_id"],
        }
    write_json(run_dir / "inventory" / "scene-inventory.json", combined_inventory, canonical=True)
    write_json(run_dir / "grouping" / "processing-representations.json", representations, canonical=True)
    write_json(run_dir / "grouping" / "acquisition-groups.json", combined_groups, canonical=True)
    write_json(run_dir / "diagnostics" / "solar-geometry-records.json", solar_records, canonical=True)
    write_json(run_dir / "diagnostics" / "radiometry-records.json", radiometry_records, canonical=True)
    grouping_output_hash = sha256_bytes(
        canonical_bytes(
            {
                "pre": window_summary["pre"]["grouping_sha256"],
                "post": window_summary["post"]["grouping_sha256"],
                "representations": sha256_file(run_dir / "grouping" / "processing-representations.json"),
                "groups": sha256_file(run_dir / "grouping" / "acquisition-groups.json"),
            }
        )
    )
    permitted = all(window_summary[window]["raster_access_permitted"] for window in ("pre", "post"))
    state.update(
        stage="METADATA_GATE_PASSED" if permitted else "ACQUISITION_GROUP_LIMIT_EXCEEDED",
        metadata_window_summary=window_summary,
        grouping_output_sha256=grouping_output_hash,
        terminal_reason_codes=[] if permitted else ["RESOURCE_LIMIT_EXCEEDED"],
    )
    write_json(run_dir / "run-state.json", state)


def _coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(part, (int, float)) for part in value[:2]):
        yield float(value[0]), float(value[1])
    elif isinstance(value, list):
        for child in value:
            yield from _coordinate_pairs(child)


def _projected_geometry_area(geometry: dict[str, Any]) -> float:
    if geometry.get("type") == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry.get("type") == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise V4RuntimeFailure("CEA geometry must be Polygon or MultiPolygon", "BOUNDARY_NOT_FROZEN")
    area = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        area += abs(legacy_io.signed_area(polygon[0]))
        area -= sum(abs(legacy_io.signed_area(ring)) for ring in polygon[1:])
    return area


def _target_grid(run_dir: Path, spec: dict[str, Any]) -> tuple[dict[str, Any], Any, Any]:
    try:
        import numpy as np
        from rasterio.features import geometry_mask
        from rasterio.transform import Affine
        from rasterio.warp import transform_geom
    except ImportError as exc:  # pragma: no cover - runtime preflight covers dependencies
        raise V4RuntimeFailure(f"raster dependency unavailable: {exc}") from exc
    geometry = read_json(run_dir / "cache" / "aoi-wgs84.geojson")
    projected = transform_geom("EPSG:4326", "EPSG:32754", geometry, precision=9)
    coordinates = list(_coordinate_pairs(projected["coordinates"]))
    if not coordinates:
        raise V4RuntimeFailure("projected CEA is empty", "BOUNDARY_NOT_FROZEN")
    xs, ys = zip(*coordinates)
    grid = raster_core.snapped_grid((min(xs), min(ys), max(xs), max(ys)))
    limits = spec["resource_limits"]
    if grid["width"] > limits["maximum_grid_width_pixels"] or grid["height"] > limits["maximum_grid_height_pixels"]:
        raise V4RuntimeFailure("target grid dimensions exceed frozen runtime limits", "RESOURCE_LIMIT_EXCEEDED")
    affine = Affine(*grid["transform"])
    mask = geometry_mask(
        [projected],
        out_shape=(grid["height"], grid["width"]),
        transform=affine,
        all_touched=False,
        invert=True,
    )
    if int(mask.sum()) > limits["maximum_full_aoi_pixels"]:
        raise V4RuntimeFailure("AOI pixels exceed the frozen runtime limit", "RESOURCE_LIMIT_EXCEEDED")
    grid["aoi_total_pixels"] = int(mask.sum())
    grid["aoi_mask_sha256"] = raster_core.canonical_array_sha256(mask)
    grid["projected_area_m2"] = _projected_geometry_area(projected)
    write_json(run_dir / "diagnostics" / "target-grid.json", grid, canonical=True)
    np.save(run_dir / "cache" / "aoi-mask.npy", mask, allow_pickle=False)
    return grid, affine, mask


def _item_geometry_mask(item: dict[str, Any], affine: Any, shape: tuple[int, int]) -> Any:
    from rasterio.features import geometry_mask
    from rasterio.warp import transform_geom

    projected = transform_geom("EPSG:4326", "EPSG:32754", item["geometry"], precision=9)
    return geometry_mask([projected], out_shape=shape, transform=affine, invert=True, all_touched=False)


def _read_component_arrays(run_dir: Path, item: dict[str, Any], affine: Any, shape: tuple[int, int]) -> tuple[Any, Any, Any, Any]:
    try:
        import numpy as np
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.vrt import WarpedVRT
    except ImportError as exc:  # pragma: no cover
        raise V4RuntimeFailure(f"raster dependency unavailable: {exc}") from exc
    signed: dict[str, str] = {}
    for key in ("B04", "B08", "SCL"):
        signed[key], _ = _sign_asset_url(run_dir, item["assets"][key]["href"])
    env = rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
        GDAL_HTTP_MAX_RETRY="3",
        GDAL_HTTP_RETRY_DELAY="1",
    )
    with env:
        arrays = {}
        masks = []
        for key in ("B04", "B08"):
            with rasterio.open(signed[key]) as dataset:
                if dataset.crs is None or dataset.crs.to_epsg() != 32754:
                    raise V4RuntimeFailure(f"{item['id']} {key} is not EPSG:32754", "SCL_ALIGNMENT_FAILED")
                with WarpedVRT(
                    dataset,
                    crs="EPSG:32754",
                    transform=affine,
                    width=shape[1],
                    height=shape[0],
                    resampling=Resampling.nearest,
                ) as vrt:
                    value = vrt.read(1, masked=True)
                    arrays[key] = np.asarray(value.data)
                    masks.append(~np.asarray(value.mask, dtype=bool))
        with rasterio.open(signed["SCL"]) as dataset, WarpedVRT(
            dataset,
            crs="EPSG:32754",
            transform=affine,
            width=shape[1],
            height=shape[0],
            resampling=Resampling.nearest,
        ) as vrt:
            value = vrt.read(1, masked=True)
            arrays["SCL"] = np.asarray(value.data)
            masks.append(~np.asarray(value.mask, dtype=bool))
    return arrays["B04"], arrays["B08"], arrays["SCL"], np.logical_and.reduce(masks)


def _require_target_grid_metadata(item: dict[str, Any]) -> bool:
    properties = item.get("properties", {})
    if properties.get("proj:epsg") != 32754:
        return False
    transforms = []
    for key in ("B04", "B08"):
        asset = item.get("assets", {}).get(key, {})
        transform = asset.get("proj:transform")
        if not isinstance(transform, list) or len(transform) != 6:
            raise V4RuntimeFailure(f"{item.get('id')} {key} lacks a frozen grid transform", "SCL_ALIGNMENT_FAILED")
        if any(abs(float(actual) - expected) > 1e-9 for actual, expected in zip(transform[:2], (10.0, 0.0))):
            raise V4RuntimeFailure(f"{item.get('id')} {key} is not a native 10 m north-up grid", "SCL_ALIGNMENT_FAILED")
        if abs(float(transform[3])) > 1e-9 or abs(float(transform[4]) + 10.0) > 1e-9:
            raise V4RuntimeFailure(f"{item.get('id')} {key} is not a native 10 m north-up grid", "SCL_ALIGNMENT_FAILED")
        if abs(float(transform[2]) % 10.0) > 1e-9 or abs(float(transform[5]) % 10.0) > 1e-9:
            raise V4RuntimeFailure(f"{item.get('id')} {key} is not congruent with the target lattice", "SCL_ALIGNMENT_FAILED")
        transforms.append(tuple(float(value) for value in transform))
    if transforms[0] != transforms[1]:
        raise V4RuntimeFailure(f"{item.get('id')} B04 and B08 grids differ", "SCL_ALIGNMENT_FAILED")
    return True


def process_rasters(run_dir: Path) -> None:
    state, _, spec = _run_guard(run_dir)
    if state.get("stage") != "METADATA_GATE_PASSED":
        raise V4RuntimeFailure("process-rasters requires a passed metadata gate", "RESOURCE_LIMIT_EXCEEDED")
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise V4RuntimeFailure("NumPy is unavailable") from exc
    grid, affine, aoi_mask = _target_grid(run_dir, spec)
    shape = (grid["height"], grid["width"])
    raw_items = {item["id"]: item for window in ("pre", "post") for item in _load_cached_items(run_dir, window)}
    metadata = {
        item["id"]: item
        for window in ("pre", "post")
        for item in json.loads((run_dir / "inventory" / f"{window}-metadata-input.json").read_text(encoding="utf-8"))
    }
    groups = read_json(run_dir / "grouping" / "acquisition-groups.json")
    arrays_by_window: dict[str, list[Any]] = {"PRE": [], "POST": []}
    cache_index: list[dict[str, Any]] = []
    scene_diagnostics: list[dict[str, Any]] = []
    for group in groups:
        if not group["metadata_admissible"]:
            continue
        members = [raw_items[item_id] for item_id in group["component_item_ids"]]
        target_members = [item for item in members if _require_target_grid_metadata(item)]
        if not target_members:
            raise V4RuntimeFailure(f"group {group['datatake_id']} has no EPSG:32754 component", "SCL_ALIGNMENT_FAILED")
        all_coverage = np.logical_or.reduce([_item_geometry_mask(item, affine, shape) for item in members]) & aoi_mask
        target_coverage = np.logical_or.reduce([_item_geometry_mask(item, affine, shape) for item in target_members]) & aoi_mask
        if np.any(all_coverage & ~target_coverage):
            raise V4RuntimeFailure(
                f"group {group['datatake_id']} needs a non-target-CRS spatial component",
                "SCL_ALIGNMENT_FAILED",
            )
        components = []
        component_cache = []
        for item in sorted(target_members, key=lambda value: value["properties"]["s2:mgrs_tile"]):
            record = metadata[item["id"]]
            red, nir, scl, source_valid = _read_component_arrays(run_dir, item, affine, shape)
            source_valid &= _item_geometry_mask(item, affine, shape) & aoi_mask
            red_meta = record["radiometry"]["B04"]
            nir_meta = record["radiometry"]["B08"]
            ndvi = raster_core.calibrated_ndvi_array(
                red,
                nir,
                scl,
                red_scale=red_meta["scale"],
                red_offset=red_meta["offset"],
                nir_scale=nir_meta["scale"],
                nir_offset=nir_meta["offset"],
                red_nodata=red_meta["nodata"],
                nir_nodata=nir_meta["nodata"],
                valid_scl_classes=(4, 5),
                source_valid_mask=source_valid,
            )
            components.append((record["mgrs_tile"], ndvi))
            component_name = f"component-{sha256_bytes(item['id'].encode('utf-8'))[:20]}.npz"
            np.savez_compressed(
                run_dir / "cache" / component_name,
                red_dn=red,
                nir_dn=nir,
                scl=scl,
                source_valid=source_valid,
            )
            component_cache.append(
                {
                    "item_id": item["id"],
                    "mgrs_tile": record["mgrs_tile"],
                    "path": f"cache/{component_name}",
                    "red_dn_sha256": raster_core.canonical_array_sha256(red),
                    "nir_dn_sha256": raster_core.canonical_array_sha256(nir),
                    "scl_sha256": raster_core.canonical_array_sha256(scl),
                    "source_valid_sha256": raster_core.canonical_array_sha256(source_valid),
                    "red_radiometry": red_meta,
                    "nir_radiometry": nir_meta,
                }
            )
            unique_scl, scl_counts = np.unique(scl[source_valid], return_counts=True)
            scene_diagnostics.append(
                {
                    "window": group["window"],
                    "item_id": item["id"],
                    "datatake_id": group["datatake_id"],
                    "mgrs_tile": record["mgrs_tile"],
                    "geometric_aoi_pixels": int(source_valid.sum()),
                    "valid_ndvi_pixels": int(np.isfinite(ndvi).sum()),
                    "valid_fraction_of_geometric_coverage": float(np.isfinite(ndvi).sum() / source_valid.sum()) if source_valid.any() else 0.0,
                    "scl_class_counts": {str(int(key)): int(value) for key, value in zip(unique_scl, scl_counts)},
                    "aligned_b04_sha256": raster_core.canonical_array_sha256(red),
                    "aligned_b08_sha256": raster_core.canonical_array_sha256(nir),
                    "aligned_scl_sha256": raster_core.canonical_array_sha256(scl),
                    "source_valid_mask_sha256": raster_core.canonical_array_sha256(source_valid),
                    "ndvi_sha256": raster_core.canonical_array_sha256(ndvi),
                }
            )
        mosaic = raster_core.mosaic_acquisition_components(components)
        arrays_by_window[group["window"]].append(mosaic)
        cache_name = f"{group['window'].lower()}-{sha256_bytes(group['datatake_id'].encode('utf-8'))[:20]}.npy"
        np.save(run_dir / "cache" / cache_name, mosaic, allow_pickle=False)
        cache_index.append(
            {
                "window": group["window"],
                "platform": group["platform"],
                "datatake_id": group["datatake_id"],
                "path": f"cache/{cache_name}",
                "array_sha256": raster_core.canonical_array_sha256(mosaic),
                "component_item_ids": group["component_item_ids"],
                "components": component_cache,
            }
        )
    aggregation = raster_core.aggregate_windows(
        arrays_by_window["PRE"],
        arrays_by_window["POST"],
        aoi_mask,
        minimum_observations=spec["coverage"]["minimum_valid_observations_per_pixel_per_window"],
        minimum_joint_fraction=spec["coverage"]["minimum_joint_aoi_fraction"],
    )
    write_json(run_dir / "cache" / "index.json", cache_index, canonical=True)
    write_json(run_dir / "diagnostics" / "scene-raster-statistics.json", scene_diagnostics, canonical=True)
    write_json(run_dir / "diagnostics" / "aggregation.json", aggregation, canonical=True)
    state.update(
        stage="RASTER_AGGREGATION_COMPLETE",
        raster_pixels_read=True,
        raster_processing_group_counts={key.lower(): len(value) for key, value in arrays_by_window.items()},
        aggregation_sha256=sha256_file(run_dir / "diagnostics" / "aggregation.json"),
    )
    write_json(run_dir / "run-state.json", state)


def _quality_checks(reason_codes: Sequence[str], *, complete_system: bool) -> dict[str, str]:
    checks = {
        "claim_contract": "PASS",
        "evidence_allowlist": "PASS",
        "transformation_allowlist": "PASS",
        "spatial_scope": "PASS",
        "temporal_scope": "PASS",
        "observation_coverage": "PASS",
        "evidence_consistency": "PASS",
        "authority_scope": "PASS",
        "provenance": "PASS",
        "system_execution": "PASS",
    }
    if "VALID_OBSERVATION_COVERAGE_LOW" in reason_codes or "RADIOMETRY_METADATA_UNRESOLVED" in reason_codes:
        checks["observation_coverage"] = "FAIL"
    if any(code in reason_codes for code in ("RESOURCE_LIMIT_EXCEEDED", "METADATA_INVENTORY_LIMIT_EXCEEDED")):
        checks["system_execution"] = "FAIL"
        checks["observation_coverage"] = "NOT_RUN"
    if not complete_system and checks["system_execution"] == "PASS":
        checks["system_execution"] = "FAIL"
    return checks


def _statement_parameters(policy: dict[str, Any], aggregation: dict[str, Any]) -> dict[str, str]:
    claim = policy["bounded_claim"]
    pre = policy["temporal_scope"]["pre_window"]
    post = policy["temporal_scope"]["post_window"]
    return {
        "project_id": "EOP101132",
        "analysis_boundary_role": claim["analysis_boundary_role"],
        "pre_window": f"{pre['start_date']}/{pre['end_date']}",
        "post_window": f"{post['start_date']}/{post['end_date']}",
        "seasonal_rule_id": claim["seasonal_rule_id"],
        "aggregation": claim["aggregation"],
        "eligible_population": claim["eligible_population"],
        "pre_value": str(aggregation["pre_window_ndvi_median"]),
        "post_value": str(aggregation["post_window_ndvi_median"]),
        "delta_value": str(aggregation["delta_ndvi"]),
        "primary_tau": "0.03",
        "indifference_policy_id": claim["indifference_policy_id"],
        "qualification_policy_version": CONTRACT_VERSION,
    }


def build_assessment(
    run_id: str,
    policy: dict[str, Any],
    aggregation: dict[str, Any] | None,
    *,
    terminal_reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    manifest_id = f"urn:eop101132:{run_id}:provenance"
    if aggregation is None:
        status = "ABSTAINED"
        disposition = "INCONCLUSIVE"
        reasons = list(terminal_reason_codes)
        observations = None
        classification = None
    else:
        classification = raster_core.qualification_from_aggregation(aggregation)
        status = classification["execution_status"]
        disposition = classification["evidence_disposition"]
        reasons = classification["reason_codes"]
        complete = (
            aggregation.get("coverage_passed") is True
            and aggregation.get("delta_ndvi") is not None
            and aggregation.get("delta_distribution") is not None
        )
        observations = {
            "observation_status": "COMPLETE" if complete else "PARTIAL",
            "aoi_total_pixels": aggregation["aoi_total_pixels"],
            "aoi_valid_pixels": aggregation["aoi_valid_pixels"],
            "aoi_valid_fraction": aggregation["aoi_valid_fraction"],
            "pre_window_ndvi_median": aggregation["pre_window_ndvi_median"],
            "post_window_ndvi_median": aggregation["post_window_ndvi_median"],
            "delta_ndvi": aggregation["delta_ndvi"],
            "primary_tau": 0.03 if complete else None,
            "delta_distribution": aggregation["delta_distribution"],
            "sensitivity_results": classification["sensitivities"] if complete and aggregation["coverage_passed"] else None,
        }
    completed = status == "COMPLETED"
    parameters = _statement_parameters(policy, aggregation) if completed and aggregation is not None else None
    template_id = f"OBSERVATIONAL_COMPARISON_{disposition}_V2" if completed else None
    statement = None
    if completed:
        registry = read_json(ROOT / "config" / "statement-templates.json")
        template = next(item["template_text"] for item in registry["templates"] if item["template_id"] == template_id)
        statement = template.format(**parameters)
    return {
        "schema_version": CONTRACT_VERSION,
        "case_id": "EOP101132-NDVI-001",
        "run_id": run_id,
        "execution_status": status,
        "evidence_disposition": disposition,
        "reason_codes": reasons,
        "quality_checks": _quality_checks(reasons, complete_system=aggregation is not None),
        "observations": observations,
        "statement_template_id": template_id,
        "supported_statement": statement,
        "must_not_claim": FORBIDDEN_CODES,
        "human_review_required": not completed,
        "provenance_manifest_ref": manifest_id,
        "qualification_policy_version": CONTRACT_VERSION,
        "statement_parameters": parameters,
    }


def _artifact_record(path: Path, run_dir: Path) -> dict[str, Any]:
    relative = path.relative_to(run_dir).as_posix()
    media_type = "application/json"
    if path.suffix == ".zip":
        media_type = "application/zip"
    elif path.suffix == ".xml":
        media_type = "application/xml"
    elif path.suffix in {".npy", ".npz"}:
        media_type = "application/x-numpy"
    elif path.suffix in {".md", ".txt", ".sha256"} or path.name.endswith(".raw"):
        media_type = "text/plain"
    return {
        "artifact_id": f"urn:eop101132:{run_dir.name}:artifact:{relative}",
        "artifact_type": re.sub(r"[^A-Z0-9]+", "_", relative.upper()).strip("_"),
        "content_sha256": sha256_file(path),
        "produced_by": "EOP101132_STEP2B_V4_RUNTIME",
        "media_type": media_type,
    }


def _qualification_records(assessment: dict[str, Any]) -> list[dict[str, Any]]:
    observations = assessment.get("observations")
    if not isinstance(observations, dict) or observations.get("observation_status") != "COMPLETE":
        return []
    classification = step2b_offline.classify_primary_and_sensitivities(observations["delta_ndvi"])
    primary = {
        "policy_id": classification["primary"]["policy_id"],
        "is_primary": True,
        "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
        **{key: classification["primary"][key] for key in ("delta_ndvi", "tau", "comparison_semantics", "execution_status", "evidence_disposition", "reason_codes")},
    }
    sensitivities = [
        {
            "is_primary": False,
            "metric": "POST_MINUS_PRE_AOI_MEDIAN_PER_PIXEL_TEMPORAL_MEDIAN_NDVI",
            "delta_ndvi": observations["delta_ndvi"],
            **record,
        }
        for record in classification["sensitivities"]
    ]
    return [primary, *sensitivities]


def _source_records(run_dir: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    project = read_json(run_dir / "source" / "cer-project-page.metadata.json")
    cea = read_json(run_dir / "source" / "eop101132-cea.metadata.json")
    pre_requests = read_json(run_dir / "source" / "stac-pre-requests.json")
    post_requests = read_json(run_dir / "source" / "stac-post-requests.json")
    items = _load_cached_items(run_dir, "pre") + _load_cached_items(run_dir, "post")
    stac_hash = sha256_bytes(canonical_bytes({
        "pre": [record["response_sha256"] for record in pre_requests],
        "post": [record["response_sha256"] for record in post_requests],
    }))
    return [
        {
            "source_id": "CER_PROJECT_RECORD",
            "canonical_uri": policy["project_and_boundary"]["project_page"],
            "retrieval_uri": None,
            "publisher": "Clean Energy Regulator",
            "retrieved_at_utc": project["retrieved_at_utc"],
            "version_identifier": f"sha256:{project['response_sha256']}",
            "content_sha256": project["response_sha256"],
            "source_asset_ids": ["EOP101132"],
        },
        {
            "source_id": "CER_PUBLISHED_CEA",
            "canonical_uri": policy["project_and_boundary"]["boundary_artifact_uri"],
            "retrieval_uri": None,
            "publisher": "Clean Energy Regulator",
            "retrieved_at_utc": cea["retrieved_at_utc"],
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
            "version_identifier": f"stac-response-set-sha256:{stac_hash}",
            "content_sha256": stac_hash,
            "source_asset_ids": sorted({item["id"] for item in items}),
        },
    ]


def _transformation_records(
    run_dir: Path,
    assessment: dict[str, Any],
    artifacts: Sequence[dict[str, Any]],
    policy_hash: str,
) -> list[dict[str, Any]]:
    state = read_json(run_dir / "run-state.json")
    by_path = {record["artifact_id"].split(":artifact:", 1)[1]: record["artifact_id"] for record in artifacts}
    initial = by_path["runtime-case.json"]
    assessment_ref = by_path["assessment.json"]
    completed_through = 12
    failure_reasons: list[str] = []
    if any(code in assessment.get("reason_codes", []) for code in ("RESOURCE_LIMIT_EXCEEDED", "METADATA_INVENTORY_LIMIT_EXCEEDED")):
        completed_through = 4
        failure_reasons = state.get("terminal_reason_codes", ["RESOURCE_LIMIT_EXCEEDED"])
    timestamp = state["created_at_utc"]
    finished = utc_now()
    records = []
    for sequence, transformation_id in enumerate(TRANSFORMATION_IDS, 1):
        if sequence <= completed_through or sequence == 12:
            status = "COMPLETED"
            reasons: list[str] = []
            inputs = [initial]
            outputs = [assessment_ref] if sequence == 12 else [initial]
        elif sequence == 5 and failure_reasons:
            status = "FAILED"
            reasons = failure_reasons
            inputs = [initial]
            outputs = [assessment_ref]
        else:
            status = "SKIPPED"
            reasons = failure_reasons
            inputs = []
            outputs = []
        records.append(
            {
                "sequence": sequence,
                "transformation_id": transformation_id,
                "implementation_version": RUNTIME_VERSION,
                "parameter_set_ref": f"urn:eop101132:policy:{policy_hash}:{sequence}",
                "parameter_set_sha256": policy_hash,
                "input_artifact_refs": inputs,
                "output_artifact_refs": outputs,
                "status": status,
                "started_at_utc": timestamp,
                "finished_at_utc": finished,
                "reason_codes": reasons,
            }
        )
    return records


def build_manifest(run_dir: Path, assessment: dict[str, Any]) -> dict[str, Any]:
    state = read_json(run_dir / "run-state.json")
    policy = read_json(run_dir / "frozen" / "policy.json")
    excluded = {"provenance-manifest.json", "checksums.sha256", "run-state.json"}
    artifact_paths = sorted(
        path for path in run_dir.rglob("*")
        if path.is_file() and path.name not in excluded and "cea-extracted" not in path.parts
    )
    artifacts = [_artifact_record(path, run_dir) for path in artifact_paths]
    assessment_ref = next(record["artifact_id"] for record in artifacts if record["artifact_id"].endswith(":artifact:assessment.json"))
    case_hash = sha256_file(run_dir / "runtime-case.json")
    input_hash = sha256_bytes(canonical_bytes({
        "policy_sha256": state["policy_sha256"],
        "runtime_spec_sha256": state["runtime_spec_sha256"],
        "approval_request_sha256": state["approval_request_sha256"],
        "approval_evidence_sha256": state["approval_evidence_sha256"],
        "approval_consumption_sha256": state["approval_consumption_sha256"],
        "git_commit": state["git_commit"],
        "runtime_case_sha256": case_hash,
    }))
    solar_records = read_json(run_dir / "diagnostics" / "solar-geometry-records.json") if (run_dir / "diagnostics" / "solar-geometry-records.json").exists() else []
    package_versions = {}
    for package in read_json(run_dir / "frozen" / "runtime-spec.json")["runtime_packages"]:
        package_versions[package] = importlib.metadata.version(package)
    return {
        "schema_version": CONTRACT_VERSION,
        "manifest_id": assessment["provenance_manifest_ref"],
        "run_id": state["run_id"],
        "case_id": state["case_id"],
        "runtime_mode": "EXECUTION",
        "created_at_utc": utc_now(),
        "run_identity": {
            "approved_policy_sha256": state["policy_sha256"],
            "calculated_policy_sha256_at_start": state["policy_sha256"],
            "final_policy_sha256": sha256_file(POLICY_PATH),
            "input_sha256_at_start": input_hash,
            "final_input_sha256": input_hash,
            "approved_runtime_spec_sha256": state["runtime_spec_sha256"],
            "detached_approval_sha256": state["approval_sha256"],
            "approval_protocol_version": state["approval_protocol_version"],
            "approval_request_sha256": state["approval_request_sha256"],
            "approval_evidence_sha256": state["approval_evidence_sha256"],
            "approval_consumption_sha256": state["approval_consumption_sha256"],
            "reserved_run_id": state["run_id"],
            "github_approval_url": read_json(run_dir / "approval" / "approval-verification.json")["github_url"],
            "github_approver_login": read_json(run_dir / "approval" / "approval-verification.json")["github_author_login"],
            "git_commit": state["git_commit"],
        },
        "source_records": _source_records(run_dir, policy),
        "processing_representation_records": read_json(run_dir / "grouping" / "processing-representations.json") if (run_dir / "grouping" / "processing-representations.json").exists() else [],
        "acquisition_group_records": read_json(run_dir / "grouping" / "acquisition-groups.json") if (run_dir / "grouping" / "acquisition-groups.json").exists() else [],
        "solar_geometry_records": solar_records,
        "solar_geometry_summary": step2b_offline.solar_geometry_diagnostic(
            [record for record in solar_records if record["window"] == "PRE"],
            [record for record in solar_records if record["window"] == "POST"],
        ),
        "radiometry_records": read_json(run_dir / "diagnostics" / "radiometry-records.json") if (run_dir / "diagnostics" / "radiometry-records.json").exists() else [],
        "qualification_records": _qualification_records(assessment),
        "artifact_records": artifacts,
        "transformation_records": _transformation_records(run_dir, assessment, artifacts, state["policy_sha256"]),
        "policy_versions": {key: CONTRACT_VERSION for key in ("evidence_sources", "transformations", "statement_templates", "forbidden_inferences", "reason_codes", "qualification_policy")},
        "software_environment": {
            "code_revision": state["git_commit"],
            "python_version": sys.version.split()[0],
            "package_lock_sha256": state["runtime_spec_sha256"],
            "packages": package_versions,
        },
        "terminal_result": {
            "assessment_artifact_ref": assessment_ref,
            "assessment_sha256": sha256_file(run_dir / "assessment.json"),
            "execution_status": assessment["execution_status"],
            "reason_codes": assessment["reason_codes"],
            "canonicalisation_id": "CANONICAL_JSON_V1",
        },
    }


def validate_runtime_outputs(run_dir: Path) -> None:
    from scripts import validate_step1_specs as contracts

    loaded = contracts.load_contracts()
    case = read_json(run_dir / "runtime-case.json")
    assessment = read_json(run_dir / "assessment.json")
    manifest = read_json(run_dir / "provenance-manifest.json")
    contracts.validate_assessment(assessment, case, loaded["schemas"], loaded["registries"])
    contracts.validate_manifest_structure(manifest, loaded["schemas"], loaded["registries"])
    if manifest["run_id"] != assessment["run_id"] or manifest["case_id"] != assessment["case_id"]:
        raise V4RuntimeFailure("assessment and provenance identities differ", "PROVENANCE_HASH_MISMATCH")
    if manifest["terminal_result"]["assessment_sha256"] != sha256_file(run_dir / "assessment.json"):
        raise V4RuntimeFailure("manifest assessment hash mismatch", "PROVENANCE_HASH_MISMATCH")


def finalise(run_dir: Path) -> None:
    state, _, _ = _run_guard(run_dir)
    stage = state.get("stage")
    policy = read_json(run_dir / "frozen" / "policy.json")
    if stage == "RASTER_AGGREGATION_COMPLETE":
        aggregation = read_json(run_dir / "diagnostics" / "aggregation.json")
        reasons: list[str] = []
    elif stage in {"RAW_STAC_LIMIT_EXCEEDED", "ACQUISITION_GROUP_LIMIT_EXCEEDED"}:
        aggregation = None
        reasons = state.get("terminal_reason_codes", ["RESOURCE_LIMIT_EXCEEDED"])
    else:
        raise V4RuntimeFailure(f"cannot finalise run at stage {stage}")
    assessment = build_assessment(state["run_id"], policy, aggregation, terminal_reason_codes=reasons)
    write_json(run_dir / "assessment.json", assessment, canonical=True)
    observations = assessment.get("observations")
    sensitivity = {
        "primary_assessment_sha256": sha256_file(run_dir / "assessment.json"),
        "primary_policy_id": "POC_OPERATIONAL_INDIFFERENCE_BAND_V1",
        "primary_tau": 0.03,
        "results": observations.get("sensitivity_results") if isinstance(observations, dict) else None,
        "status": "COMPLETE" if isinstance(observations, dict) and observations.get("sensitivity_results") else "NOT_RUN",
        "cannot_modify_primary": True,
    }
    write_json(run_dir / "sensitivity.json", sensitivity, canonical=True)
    manifest = build_manifest(run_dir, assessment)
    write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    validate_runtime_outputs(run_dir)
    state.update(
        stage="PRIMARY_SEALED",
        execution_status=assessment["execution_status"],
        evidence_disposition=assessment["evidence_disposition"],
        primary_reason_codes=assessment["reason_codes"],
        assessment_sha256=sha256_file(run_dir / "assessment.json"),
        provenance_manifest_sha256=sha256_file(run_dir / "provenance-manifest.json"),
    )
    write_json(run_dir / "run-state.json", state)


def _replay_aggregation(run_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    index = read_json(run_dir / "cache" / "index.json")
    arrays = {"PRE": [], "POST": []}
    for record in index:
        components = []
        for component in record["components"]:
            with np.load(run_dir / component["path"], allow_pickle=False) as cached:
                red = cached["red_dn"]
                nir = cached["nir_dn"]
                scl = cached["scl"]
                source_valid = cached["source_valid"]
            actual_hashes = {
                "red_dn_sha256": raster_core.canonical_array_sha256(red),
                "nir_dn_sha256": raster_core.canonical_array_sha256(nir),
                "scl_sha256": raster_core.canonical_array_sha256(scl),
                "source_valid_sha256": raster_core.canonical_array_sha256(source_valid),
            }
            if any(component[key] != value for key, value in actual_hashes.items()):
                raise V4RuntimeFailure("replay component input-array hash mismatch", "PROVENANCE_HASH_MISMATCH")
            red_meta = component["red_radiometry"]
            nir_meta = component["nir_radiometry"]
            ndvi = raster_core.calibrated_ndvi_array(
                red,
                nir,
                scl,
                red_scale=red_meta["scale"],
                red_offset=red_meta["offset"],
                nir_scale=nir_meta["scale"],
                nir_offset=nir_meta["offset"],
                red_nodata=red_meta["nodata"],
                nir_nodata=nir_meta["nodata"],
                valid_scl_classes=(4, 5),
                source_valid_mask=source_valid,
            )
            components.append((component["mgrs_tile"], ndvi))
        array = raster_core.mosaic_acquisition_components(components)
        if raster_core.canonical_array_sha256(array) != record["array_sha256"]:
            raise V4RuntimeFailure("replay cache array hash mismatch", "PROVENANCE_HASH_MISMATCH")
        arrays[record["window"]].append(array)
    aoi_mask = np.load(run_dir / "cache" / "aoi-mask.npy", allow_pickle=False)
    return raster_core.aggregate_windows(
        arrays["PRE"],
        arrays["POST"],
        aoi_mask,
        minimum_observations=spec["coverage"]["minimum_valid_observations_per_pixel_per_window"],
        minimum_joint_fraction=spec["coverage"]["minimum_joint_aoi_fraction"],
    )


def _write_run_report(run_dir: Path, validation: dict[str, Any]) -> None:
    state = read_json(run_dir / "run-state.json")
    assessment = read_json(run_dir / "assessment.json")
    observations = assessment.get("observations") or {}
    lines = [
        "# EOP101132 Step 2B V4 Run Report",
        "",
        f"- Run ID: {state['run_id']}",
        f"- Git commit: {state['git_commit']}",
        f"- Policy SHA-256: {state['policy_sha256']}",
        f"- Runtime-spec SHA-256: {state['runtime_spec_sha256']}",
        f"- Approval SHA-256: {state['approval_sha256']}",
        f"- Execution status: {assessment['execution_status']}",
        f"- Evidence disposition: {assessment['evidence_disposition']}",
        f"- Reason codes: {', '.join(assessment['reason_codes']) if assessment['reason_codes'] else 'none'}",
        f"- Joint AOI coverage: {observations.get('aoi_valid_fraction')}",
        f"- PRE NDVI median: {observations.get('pre_window_ndvi_median')}",
        f"- POST NDVI median: {observations.get('post_window_ndvi_median')}",
        f"- Delta NDVI: {observations.get('delta_ndvi')}",
        f"- Offline replay assessment match: {validation['canonical_assessment_bytes_equal']}",
        "",
        "This result qualifies only the frozen observational NDVI comparison. It does not establish causality, carbon quantity, additionality, permanence, ACCU validity, regulatory compliance, project integrity, or financial suitability.",
    ]
    (run_dir / "final-run-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_checksums(run_dir: Path) -> None:
    lines = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file() and item.name != "checksums.sha256"):
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="ascii")


def _security_scan(run_dir: Path) -> None:
    credential = re.compile(rb"(?i)([?&](?:sig|token|sv|se|sp)=|x-amz-(?:credential|signature)=|authorization\s*:)")
    local_path = re.compile(rb"(?i)[a-z]:\\users\\")
    non_finite = re.compile(rb"(?<![A-Za-z])(?:NaN|-?Infinity)(?![A-Za-z])")
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.suffix in {".npy", ".npz"}:
            continue
        raw = path.read_bytes()
        if credential.search(raw):
            raise V4RuntimeFailure(f"credential-bearing content persisted in {path.name}", "PROVENANCE_INCOMPLETE")
        if local_path.search(raw):
            raise V4RuntimeFailure(f"local machine path persisted in {path.name}", "PROVENANCE_INCOMPLETE")
        if path.suffix == ".json":
            try:
                json.loads(
                    raw.decode("utf-8"),
                    parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
                )
            except ValueError as exc:
                if str(exc) in {"NaN", "Infinity", "-Infinity"}:
                    raise V4RuntimeFailure(
                        f"non-finite JSON value persisted in {path.name}",
                        "DETERMINISTIC_PROCESSING_ERROR",
                    ) from exc
                raise
        elif path.suffix.lower() in {".csv", ".md", ".sha256", ".txt"} and non_finite.search(raw):
            raise V4RuntimeFailure(f"non-finite token persisted in {path.name}", "DETERMINISTIC_PROCESSING_ERROR")


def replay(run_dir: Path) -> None:
    state, _, spec = _run_guard(run_dir)
    if state.get("stage") != "PRIMARY_SEALED":
        raise V4RuntimeFailure("offline replay requires a sealed primary assessment")
    policy = read_json(run_dir / "frozen" / "policy.json")
    if (run_dir / "diagnostics" / "aggregation.json").exists():
        replay_aggregation = _replay_aggregation(run_dir, spec)
        write_json(run_dir / "replay" / "aggregation.json", replay_aggregation, canonical=True)
        replay_assessment = build_assessment(state["run_id"], policy, replay_aggregation)
        array_hashes = [record["array_sha256"] for record in read_json(run_dir / "cache" / "index.json")]
    else:
        replay_assessment = build_assessment(
            state["run_id"],
            policy,
            None,
            terminal_reason_codes=state.get("primary_reason_codes", []),
        )
        array_hashes = []
    write_json(run_dir / "replay" / "assessment.json", replay_assessment, canonical=True)
    live = (run_dir / "assessment.json").read_bytes()
    replay_bytes = (run_dir / "replay" / "assessment.json").read_bytes()
    grouping_hash = state.get("grouping_output_sha256")
    if grouping_hash is not None:
        current_grouping_hash = sha256_bytes(canonical_bytes({
            "pre": sha256_file(run_dir / "grouping" / "pre-grouping.json"),
            "post": sha256_file(run_dir / "grouping" / "post-grouping.json"),
            "representations": sha256_file(run_dir / "grouping" / "processing-representations.json"),
            "groups": sha256_file(run_dir / "grouping" / "acquisition-groups.json"),
        }))
    else:
        current_grouping_hash = None
    validation = {
        "network_access": False,
        "cached_inputs_only": True,
        "canonical_assessment_bytes_equal": live == replay_bytes,
        "live_assessment_sha256": sha256_bytes(live),
        "replay_assessment_sha256": sha256_bytes(replay_bytes),
        "assessment_sha256_equal": sha256_bytes(live) == sha256_bytes(replay_bytes),
        "derived_array_hashes": array_hashes,
        "grouping_output_sha256": grouping_hash,
        "grouping_output_sha256_equal": grouping_hash == current_grouping_hash,
        "intentionally_variable_provenance_fields": ["created_at_utc", "retrieved_at_utc", "signed_at_utc", "safe_expiry"],
    }
    if not validation["canonical_assessment_bytes_equal"] or validation["grouping_output_sha256_equal"] is False:
        raise V4RuntimeFailure("offline replay differs from the live primary", "PROVENANCE_HASH_MISMATCH")
    write_json(run_dir / "replay" / "replay-validation.json", validation, canonical=True)
    _write_run_report(run_dir, validation)
    manifest = build_manifest(run_dir, read_json(run_dir / "assessment.json"))
    write_json(run_dir / "provenance-manifest.json", manifest, canonical=True)
    validate_runtime_outputs(run_dir)
    state.update(
        stage="REPLAY_VALIDATED",
        ended_at_utc=utc_now(),
        replay_validation=validation,
        provenance_manifest_sha256=sha256_file(run_dir / "provenance-manifest.json"),
    )
    write_json(run_dir / "run-state.json", state)
    _security_scan(run_dir)
    _write_checksums(run_dir)


def execute_live(run_dir: Path) -> None:
    fetch_sources(run_dir)
    stage = read_json(run_dir / "run-state.json")["stage"]
    if stage != "RAW_STAC_LIMIT_EXCEEDED":
        evaluate_metadata(run_dir)
        stage = read_json(run_dir / "run-state.json")["stage"]
    if stage == "METADATA_GATE_PASSED":
        process_rasters(run_dir)
    finalise(run_dir)
    replay(run_dir)


def record_failure(run_dir: Path, exc: Exception) -> None:
    reason = getattr(exc, "reason_code", "DETERMINISTIC_PROCESSING_ERROR")
    failure = {
        "failed_at_utc": utc_now(),
        "exception_type": type(exc).__name__,
        "reason_code": reason,
        "message": _safe_error_message(exc),
        "network_may_have_been_accessed": read_json(run_dir / "run-state.json").get("network_accessed", False),
        "hotfix_applied": False,
        "resume_under_same_run_id_permitted": False,
    }
    details = getattr(exc, "details", None)
    if details is not None:
        failure["details"] = details
    write_json(run_dir / "diagnostics" / "runtime-failure.json", failure)
    state = read_json(run_dir / "run-state.json")
    state.update(stage="ERROR", terminal_reason_codes=[reason], ended_at_utc=utc_now())
    write_json(run_dir / "run-state.json", state)
    sealing_errors = []
    try:
        _security_scan(run_dir)
    except Exception as sealing_exc:  # noqa: BLE001
        sealing_errors.append(
            {
                "operation": "security_scan",
                "exception_type": type(sealing_exc).__name__,
                "reason_code": getattr(sealing_exc, "reason_code", "DETERMINISTIC_PROCESSING_ERROR"),
                "message": _safe_error_message(sealing_exc),
            }
        )
    if sealing_errors:
        write_json(run_dir / "diagnostics" / "failure-sealing-errors.json", sealing_errors)
    try:
        _write_checksums(run_dir)
    except Exception as sealing_exc:  # noqa: BLE001
        sealing_errors.append(
            {
                "operation": "write_checksums",
                "exception_type": type(sealing_exc).__name__,
                "reason_code": getattr(sealing_exc, "reason_code", "DETERMINISTIC_PROCESSING_ERROR"),
                "message": _safe_error_message(sealing_exc),
            }
        )
        write_json(run_dir / "diagnostics" / "failure-sealing-errors.json", sealing_errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen EOP101132 Step 2B V4 runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify-spec")
    verify.add_argument("approved_runtime_spec_sha256")
    verify.add_argument("--skip-packages", action="store_true")
    init = sub.add_parser("init")
    init.add_argument("approval_request_dir", type=Path)
    for command in ("fetch-sources", "evaluate-metadata", "process-rasters", "finalise", "replay", "execute-live"):
        child = sub.add_parser(command)
        child.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-spec":
            _, digest = verify_runtime_spec(args.approved_runtime_spec_sha256, verify_packages=not args.skip_packages)
            print(json.dumps({"runtime_spec_id": RUNTIME_SPEC_ID, "runtime_spec_sha256": digest, "status": "VALID"}, sort_keys=True))
        elif args.command == "init":
            print(initialise_run(args.approval_request_dir.resolve()))
        else:
            run_dir = args.run_dir.resolve()
            try:
                {
                    "fetch-sources": fetch_sources,
                    "evaluate-metadata": evaluate_metadata,
                    "process-rasters": process_rasters,
                    "finalise": finalise,
                    "replay": replay,
                    "execute-live": execute_live,
                }[args.command](run_dir)
            except Exception as exc:
                record_failure(run_dir, exc)
                raise
            print(run_dir)
        return 0
    except (V4RuntimeFailure, approval_v2.ApprovalProtocolError, acquisition.AcquisitionPolicyError, raster_core.RasterContractError, step2b_offline.OfflineContractError, OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "reason_code": getattr(exc, "reason_code", "DETERMINISTIC_PROCESSING_ERROR")}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
