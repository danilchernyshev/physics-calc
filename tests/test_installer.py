"""Tests for the per-format update applier core (#75) + automated apply (#94).

Headless: format detection takes injected frozen/platform/environ, the integrity
check runs on tmp files, and apply_update's download/checksum/run steps are
injected — nothing is actually downloaded or installed.
"""

import hashlib
from pathlib import Path

import pytest

from study_calc.core.installer import (
    PACKAGE_FORMATS,
    ApplyResult,
    apply_update,
    asset_name,
    detect_format,
    parse_sha256sums,
    supports_auto_apply,
    update_plan,
    verify_sha256,
)


# --- format detection -----------------------------------------------------

def test_detect_flatpak_from_env():
    fmt = detect_format(frozen=True, platform="linux", environ={"FLATPAK_ID": "io.x"})
    assert fmt == "flatpak"


def test_detect_appimage_from_env(tmp_path):
    appimage = tmp_path / "x.AppImage"
    fmt = detect_format(frozen=True, platform="linux", environ={"APPIMAGE": str(appimage)})
    assert fmt == "appimage"


def test_detect_windows_when_frozen():
    assert detect_format(frozen=True, platform="win32", environ={}) == "windows"


def test_detect_macos_when_frozen():
    assert detect_format(frozen=True, platform="darwin", environ={}) == "macos"


def test_detect_source_when_not_frozen():
    assert detect_format(frozen=False, platform="linux", environ={}) == "source"
    assert detect_format(frozen=False, platform="win32", environ={}) == "source"


def test_flatpak_and_appimage_win_over_bare_frozen():
    # Even a frozen Linux build defers to the packaging-format env signals.
    assert detect_format(frozen=True, platform="linux", environ={"FLATPAK_ID": "x"}) == "flatpak"


def test_detect_returns_a_known_format():
    assert detect_format(frozen=False, platform="linux", environ={}) in PACKAGE_FORMATS


# --- integrity verification ----------------------------------------------

def test_verify_sha256_matches(tmp_path):
    artifact = tmp_path / "study-calc.AppImage"
    payload = b"pretend installer bytes"
    artifact.write_bytes(payload)
    good = hashlib.sha256(payload).hexdigest()
    assert verify_sha256(artifact, good) is True
    # Case- and whitespace-tolerant.
    assert verify_sha256(artifact, f"  {good.upper()}  ") is True


def test_verify_sha256_rejects_tampered(tmp_path):
    artifact = tmp_path / "setup.exe"
    artifact.write_bytes(b"original")
    digest_of_original = hashlib.sha256(b"original").hexdigest()
    artifact.write_bytes(b"tampered!")  # bytes changed after the digest was taken
    assert verify_sha256(artifact, digest_of_original) is False


def test_verify_sha256_missing_file_is_false(tmp_path):
    assert verify_sha256(tmp_path / "nope.dmg", "deadbeef") is False


def test_verify_sha256_empty_expected_is_false(tmp_path):
    artifact = tmp_path / "a.bin"
    artifact.write_bytes(b"x")
    assert verify_sha256(artifact, "") is False


# --- per-format apply plan ------------------------------------------------

def test_flatpak_plan_defers_and_carries_a_command():
    plan = update_plan("flatpak")
    assert plan["self_update"] is False
    assert plan["command"].startswith("flatpak update ")
    assert plan["instructions_key"] == "updates.apply.flatpak"


@pytest.mark.parametrize("fmt", ["windows", "macos", "appimage"])
def test_installable_formats_self_update_without_a_command(fmt):
    plan = update_plan(fmt)
    assert plan["self_update"] is True
    assert "command" not in plan
    assert plan["instructions_key"] == f"updates.apply.{fmt}"


def test_unknown_format_falls_back_to_source_plan():
    assert update_plan("haiku-os") == update_plan("source")


# --- automated apply (#94): asset names, SHA256SUMS, orchestration ---------

def test_supports_auto_apply_only_windows_and_appimage():
    assert supports_auto_apply("windows") is True
    assert supports_auto_apply("appimage") is True
    for fmt in ("macos", "flatpak", "source", "unknown"):
        assert supports_auto_apply(fmt) is False


def test_asset_name_per_format():
    assert asset_name("windows", "0.8.0") == "study-calc-0.8.0-windows-setup.exe"
    assert asset_name("appimage", "0.8.0") == "study-calc-0.8.0-linux.AppImage"
    assert asset_name("flatpak", "0.8.0") is None


def test_parse_sha256sums():
    text = (
        "abc123  study-calc-0.8.0-linux.AppImage\n"
        "def456 *study-calc-0.8.0-windows-setup.exe\n"
        "\n"
        "garbage-line\n"
    )
    sums = parse_sha256sums(text)
    assert sums["study-calc-0.8.0-linux.AppImage"] == "abc123"
    # The '*' binary marker is stripped from the filename.
    assert sums["study-calc-0.8.0-windows-setup.exe"] == "def456"
    assert len(sums) == 2


def _artifact(tmp_path, name, payload=b"installer-bytes"):
    p = tmp_path / name
    p.write_bytes(payload)
    return p


def test_apply_update_happy_path_runs_after_verify(tmp_path):
    payload = b"the real installer"
    name = "study-calc-0.8.0-windows-setup.exe"
    artifact = _artifact(tmp_path, name, payload)
    ran = []
    result = apply_update(
        "windows", "0.8.0",
        download=lambda n: artifact,
        checksums={name: hashlib.sha256(payload).hexdigest()},
        run=lambda path: ran.append(path),
    )
    assert result.ok is True
    assert result.status == "launched"
    assert result.code == "updates.apply.success"
    assert ran == [artifact]  # run() was called with the verified artifact


def test_apply_update_tampered_artifact_is_not_run(tmp_path):
    name = "study-calc-0.8.0-linux.AppImage"
    artifact = _artifact(tmp_path, name, b"tampered")
    ran = []
    result = apply_update(
        "appimage", "0.8.0",
        download=lambda n: artifact,
        checksums={name: hashlib.sha256(b"original").hexdigest()},  # mismatch
        run=lambda path: ran.append(path),
    )
    assert result.ok is False
    assert result.status == "verify_failed"
    assert result.code == "updates.apply.error.integrity"
    assert ran == []  # never executed


def test_apply_update_missing_checksum_is_not_run(tmp_path):
    name = "study-calc-0.8.0-linux.AppImage"
    artifact = _artifact(tmp_path, name)
    ran = []
    result = apply_update(
        "appimage", "0.8.0",
        download=lambda n: artifact,
        checksums={},  # no entry for the asset
        run=lambda path: ran.append(path),
    )
    assert result.status == "verify_failed"
    assert ran == []


def test_apply_update_download_failure_is_structured(tmp_path):
    def boom(name):
        raise OSError("network down")

    result = apply_update(
        "windows", "0.8.0",
        download=boom,
        checksums={},
        run=lambda path: None,
    )
    assert result.ok is False
    assert result.status == "download_failed"
    assert result.code == "updates.apply.error.download"


def test_apply_update_launch_failure_is_structured(tmp_path):
    name = "study-calc-0.8.0-windows-setup.exe"
    payload = b"x"
    artifact = _artifact(tmp_path, name, payload)

    def boom(path):
        raise RuntimeError("exec failed")

    result = apply_update(
        "windows", "0.8.0",
        download=lambda n: artifact,
        checksums={name: hashlib.sha256(payload).hexdigest()},
        run=boom,
    )
    assert result.status == "launch_failed"
    assert result.code == "updates.apply.error.launch"


def test_apply_update_unsupported_format_does_nothing(tmp_path):
    ran = []
    result = apply_update(
        "flatpak", "0.8.0",
        download=lambda n: tmp_path / n,
        checksums={},
        run=lambda path: ran.append(path),
    )
    assert result.status == "unsupported"
    assert result.code == "updates.apply.error.unsupported"
    assert ran == []
