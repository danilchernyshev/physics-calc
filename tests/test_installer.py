"""Tests for the per-format update applier core (#75).

Headless: format detection takes injected frozen/platform/environ, and the
integrity check runs on tmp files — nothing is actually installed.
"""

import hashlib

import pytest

from study_calc.core.installer import (
    PACKAGE_FORMATS,
    detect_format,
    update_plan,
    verify_sha256,
)


# --- format detection -----------------------------------------------------

def test_detect_flatpak_from_env():
    fmt = detect_format(frozen=True, platform="linux", environ={"FLATPAK_ID": "io.x"})
    assert fmt == "flatpak"


def test_detect_appimage_from_env():
    fmt = detect_format(frozen=True, platform="linux", environ={"APPIMAGE": "/tmp/x.AppImage"})
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
