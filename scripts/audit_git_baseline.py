from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SIGNED_PARAMETERS = {
    "sig",
    "signature",
    "se",
    "sp",
    "sv",
    "x-amz-credential",
    "x-amz-security-token",
    "x-amz-signature",
}
EXECUTABLE_SUFFIXES = {".exe", ".dll", ".com", ".bat", ".cmd", ".ps1", ".msi", ".jar"}
WINDOWS_PATH = re.compile(r"(?i)(?:[a-z]:[\\/](?:users|documents and settings)[\\/][^\\/\s]+)")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
AUTH_VALUE = re.compile(r"(?i)\bauthorization\s*[:=]\s*(?:bearer|basic)\s+[A-Za-z0-9+/._~-]{8,}")
CONNECTION_SECRET = re.compile(r"(?i)\b(?:accountkey|client_secret|api[_-]?key|password)\s*[:=]\s*['\"]?[^\s'\"]{12,}")
URL = re.compile(r"https?://[^\s<>\"']+")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_METADATA_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"eXIf"}
APPROVED_BINARY_ASSETS = {
    "docs/assets/repository-social-preview.png": {
        "media_type": "image/png",
        "width": 1280,
        "height": 640,
        "max_bytes": 1_000_000,
        "sha256": "460dbd29b0f7342a9724f6e5f59b5bdd74a03534a8672111901d640afc8380a2",
    }
}


def git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def validate_png_asset(path: Path, specification: dict[str, object]) -> list[str]:
    failures: list[str] = []
    data = path.read_bytes()
    max_bytes = int(specification["max_bytes"])
    if len(data) > max_bytes:
        failures.append(f"file exceeds approved {max_bytes}-byte limit")
    if specification.get("media_type") != "image/png":
        failures.append("approved media type is not image/png")
    if not data.startswith(PNG_SIGNATURE):
        return failures + ["invalid PNG signature"]

    offset = len(PNG_SIGNATURE)
    chunk_index = 0
    ihdr_seen = False
    idat_seen = False
    iend_seen = False
    while offset < len(data):
        if len(data) - offset < 12:
            failures.append("truncated PNG chunk header")
            break
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            failures.append(f"PNG chunk {chunk_type!r} exceeds file boundary")
            break
        if not re.fullmatch(rb"[A-Za-z]{4}", chunk_type):
            failures.append(f"invalid PNG chunk type {chunk_type!r}")
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_data, zlib.crc32(chunk_type)) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            failures.append(f"CRC mismatch for PNG chunk {chunk_type.decode('ascii', errors='replace')}")

        if chunk_index == 0 and chunk_type != b"IHDR":
            failures.append("IHDR is not the first PNG chunk")
        if chunk_type == b"IHDR":
            if ihdr_seen:
                failures.append("multiple IHDR chunks")
            ihdr_seen = True
            if length != 13:
                failures.append("IHDR length is not 13 bytes")
            else:
                width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                    ">IIBBBBB", chunk_data
                )
                if width != int(specification["width"]):
                    failures.append(f"PNG width {width} does not match approved width {specification['width']}")
                if height != int(specification["height"]):
                    failures.append(f"PNG height {height} does not match approved height {specification['height']}")
                valid_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
                if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
                    failures.append("IHDR contains an invalid bit-depth/color-type combination")
                if compression != 0 or filter_method != 0 or interlace not in {0, 1}:
                    failures.append("IHDR contains unsupported compression, filter, or interlace values")
        elif chunk_type == b"IDAT":
            idat_seen = True
        elif chunk_type == b"IEND":
            iend_seen = True
            if length != 0:
                failures.append("IEND length is not zero")
            offset = chunk_end
            if offset != len(data):
                failures.append("trailing bytes follow IEND")
            break

        if chunk_type in PNG_METADATA_CHUNKS:
            failures.append(f"disallowed PNG metadata chunk {chunk_type.decode('ascii')}")
        offset = chunk_end
        chunk_index += 1

    if not ihdr_seen:
        failures.append("IHDR chunk is missing")
    if not idat_seen:
        failures.append("IDAT chunk is missing")
    if not iend_seen:
        failures.append("IEND chunk is missing")
    digest = hashlib.sha256(data).hexdigest()
    if digest != specification["sha256"]:
        failures.append(f"SHA-256 {digest} does not match approved digest")
    return failures


def audit() -> dict[str, object]:
    failures: list[str] = []
    fixture_signed_urls: list[str] = []
    binaries: list[str] = []
    approved_binary_assets: list[str] = []
    rejected_binary_files: list[str] = []
    large_files: list[str] = []
    executables: list[str] = []
    symlinks: list[str] = []
    files = git_files()
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            symlinks.append(relative)
        size = path.stat().st_size
        if size > 10 * 1024 * 1024:
            large_files.append(relative)
        if path.suffix.lower() in EXECUTABLE_SUFFIXES:
            executables.append(relative)
        data = path.read_bytes()
        approved_specification = APPROVED_BINARY_ASSETS.get(relative)
        if approved_specification is not None:
            binaries.append(relative)
            asset_failures = validate_png_asset(path, approved_specification)
            if asset_failures:
                rejected_binary_files.append(relative)
                failures.extend(f"invalid approved binary asset: {relative}: {reason}" for reason in asset_failures)
            else:
                approved_binary_assets.append(relative)
            continue
        try:
            text = data.decode("utf-8", errors="strict") if b"\0" not in data else None
        except UnicodeDecodeError:
            text = None
        if text is None:
            binaries.append(relative)
            rejected_binary_files.append(relative)
            failures.append(f"binary proposed for tracking: {relative}")
            continue
        if WINDOWS_PATH.search(text):
            failures.append(f"machine absolute path: {relative}")
        if PRIVATE_KEY.search(text):
            failures.append(f"private key material: {relative}")
        if AUTH_VALUE.search(text):
            failures.append(f"authorization credential value: {relative}")
        if CONNECTION_SECRET.search(text):
            failures.append(f"credential or connection secret: {relative}")
        for match in URL.finditer(text):
            candidate = match.group(0).rstrip(".,);]")
            parsed = urlsplit(candidate)
            query_names = {name.lower() for name, _value in parse_qsl(parsed.query, keep_blank_values=True)}
            if not query_names.intersection(SIGNED_PARAMETERS):
                continue
            if parsed.hostname and (parsed.hostname == "example.test" or parsed.hostname.endswith(".example.test")) and relative.startswith("tests/"):
                fixture_signed_urls.append(f"{relative}:{parsed.hostname}")
            else:
                failures.append(f"unsafe signed URL: {relative}:{parsed.hostname or '<no-host>'}")
    if large_files:
        failures.extend(f"file exceeds 10 MB: {path}" for path in large_files)
    if executables:
        failures.extend(f"unexpected executable: {path}" for path in executables)
    if symlinks:
        failures.extend(f"symlink proposed for tracking: {path}" for path in symlinks)
    return {
        "status": "FAIL" if failures else "PASS",
        "candidate_tracked_file_count": len(files),
        "candidate_tracked_bytes": sum(path.stat().st_size for path in files),
        "files_over_10_mb": large_files,
        "binary_files": binaries,
        "approved_binary_assets": approved_binary_assets,
        "rejected_binary_files": rejected_binary_files,
        "symlinks": symlinks,
        "unexpected_executables": executables,
        "synthetic_signed_url_rejection_fixtures": sorted(set(fixture_signed_urls)),
        "excluded_local_categories": [
            "runs/",
            "Python caches",
            "virtual environments",
            "raw HTTP payload directories",
            "runtime caches",
            "scientific raster assets and AOI chips",
            "credential and signed URL caches",
            "model API response caches",
            "local environment files",
        ],
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the actual Git candidate set before the first commit.")
    parser.add_argument("--json", action="store_true", help="Emit compact JSON.")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
