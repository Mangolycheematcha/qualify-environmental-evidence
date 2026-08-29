from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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


def git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def audit() -> dict[str, object]:
    failures: list[str] = []
    fixture_signed_urls: list[str] = []
    binaries: list[str] = []
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
        if b"\0" in data:
            binaries.append(relative)
            continue
        text = data.decode("utf-8", errors="strict")
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
    if binaries:
        failures.extend(f"binary proposed for tracking: {path}" for path in binaries)
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
        "symlinks": symlinks,
        "unexpected_executables": executables,
        "synthetic_signed_url_rejection_fixtures": sorted(set(fixture_signed_urls)),
        "excluded_local_categories": [
            "runs/",
            "Python caches",
            "virtual environments",
            "raw HTTP payload directories",
            "runtime caches",
            "raster assets and AOI chips",
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
