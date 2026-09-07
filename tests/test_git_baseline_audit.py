import hashlib
import struct
import zlib

import pytest

from scripts import audit_git_baseline


PREVIEW = "docs/assets/repository-social-preview.png"


def _chunk(chunk_type: bytes, payload: bytes, *, corrupt_crc: bool = False) -> bytes:
    crc = zlib.crc32(payload, zlib.crc32(chunk_type)) & 0xFFFFFFFF
    if corrupt_crc:
        crc ^= 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def _png_bytes(
    width: int = 1280,
    height: int = 640,
    *,
    metadata_chunk: bytes | None = None,
    corrupt_idat_crc: bool = False,
    trailing: bytes = b"",
) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    chunks = [_chunk(b"IHDR", ihdr)]
    if metadata_chunk is not None:
        chunks.append(_chunk(metadata_chunk, b"key\x00value"))
    chunks.extend(
        [
            _chunk(b"IDAT", zlib.compress(b"\x00"), corrupt_crc=corrupt_idat_crc),
            _chunk(b"IEND", b""),
        ]
    )
    return audit_git_baseline.PNG_SIGNATURE + b"".join(chunks) + trailing


def _specification(data: bytes, *, max_bytes: int = 1_000_000) -> dict[str, object]:
    return {
        "media_type": "image/png",
        "width": 1280,
        "height": 640,
        "max_bytes": max_bytes,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _audit_files(monkeypatch, tmp_path, relative_files: dict[str, bytes]) -> dict[str, object]:
    paths = []
    for relative, data in relative_files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        paths.append(path)
    monkeypatch.setattr(audit_git_baseline, "ROOT", tmp_path)
    monkeypatch.setattr(audit_git_baseline, "git_files", lambda: paths)
    return audit_git_baseline.audit()


def test_git_candidate_baseline_has_no_secret_path_binary_or_executable_leak():
    result = audit_git_baseline.audit()
    assert result["status"] == "PASS"
    assert result["failures"] == []
    assert result["files_over_10_mb"] == []
    assert result["binary_files"] == [PREVIEW]
    assert result["approved_binary_assets"] == [PREVIEW]
    assert result["rejected_binary_files"] == []
    assert result["symlinks"] == []
    assert result["unexpected_executables"] == []
    assert result["synthetic_signed_url_rejection_fixtures"]
    assert "scientific raster assets and AOI chips" in result["excluded_local_categories"]


def test_non_allowlisted_binary_is_rejected(monkeypatch, tmp_path):
    result = _audit_files(monkeypatch, tmp_path, {"docs/assets/unapproved.bin": b"binary\x00payload"})
    assert result["status"] == "FAIL"
    assert result["binary_files"] == ["docs/assets/unapproved.bin"]
    assert result["approved_binary_assets"] == []
    assert result["rejected_binary_files"] == ["docs/assets/unapproved.bin"]


def test_non_utf8_binary_without_nul_is_rejected_without_crashing(monkeypatch, tmp_path):
    result = _audit_files(monkeypatch, tmp_path, {"docs/assets/non-utf8.bin": b"\xff\xfe\xfd"})
    assert result["status"] == "FAIL"
    assert result["rejected_binary_files"] == ["docs/assets/non-utf8.bin"]


def test_forged_png_at_allowlisted_path_is_rejected(monkeypatch, tmp_path):
    result = _audit_files(monkeypatch, tmp_path, {PREVIEW: b"not a PNG"})
    assert result["status"] == "FAIL"
    assert result["approved_binary_assets"] == []
    assert result["rejected_binary_files"] == [PREVIEW]
    assert any("invalid PNG signature" in failure for failure in result["failures"])


def test_wrong_png_dimensions_are_rejected(tmp_path):
    data = _png_bytes(width=640, height=320)
    path = tmp_path / "wrong-size.png"
    path.write_bytes(data)
    failures = audit_git_baseline.validate_png_asset(path, _specification(data))
    assert any("PNG width 640" in failure for failure in failures)
    assert any("PNG height 320" in failure for failure in failures)


def test_png_digest_mismatch_is_rejected(tmp_path):
    data = _png_bytes()
    path = tmp_path / "digest.png"
    path.write_bytes(data)
    specification = _specification(data)
    specification["sha256"] = "0" * 64
    failures = audit_git_baseline.validate_png_asset(path, specification)
    assert any("does not match approved digest" in failure for failure in failures)


def test_png_over_one_megabyte_is_rejected(tmp_path):
    base = _png_bytes()
    data = base + b"x" * (1_000_001 - len(base))
    path = tmp_path / "oversize.png"
    path.write_bytes(data)
    failures = audit_git_baseline.validate_png_asset(path, _specification(data))
    assert any("exceeds approved 1000000-byte limit" in failure for failure in failures)


def test_png_crc_corruption_is_rejected(tmp_path):
    data = _png_bytes(corrupt_idat_crc=True)
    path = tmp_path / "bad-crc.png"
    path.write_bytes(data)
    failures = audit_git_baseline.validate_png_asset(path, _specification(data))
    assert any("CRC mismatch for PNG chunk IDAT" in failure for failure in failures)


def test_png_trailing_bytes_are_rejected(tmp_path):
    data = _png_bytes(trailing=b"unexpected")
    path = tmp_path / "trailing.png"
    path.write_bytes(data)
    failures = audit_git_baseline.validate_png_asset(path, _specification(data))
    assert "trailing bytes follow IEND" in failures


@pytest.mark.parametrize("chunk_type", [b"tEXt", b"zTXt", b"iTXt", b"eXIf"])
def test_png_text_and_exif_metadata_are_rejected(tmp_path, chunk_type):
    data = _png_bytes(metadata_chunk=chunk_type)
    path = tmp_path / f"metadata-{chunk_type.decode('ascii')}.png"
    path.write_bytes(data)
    failures = audit_git_baseline.validate_png_asset(path, _specification(data))
    assert any("disallowed PNG metadata chunk" in failure for failure in failures)
