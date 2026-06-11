"""Per-format update application — the sibling of the update check (#75, epic #60).

Where :mod:`study_calc.core.updates` decides *that* a newer release exists, this
decides *how* a user installs it — which differs sharply per packaging format:

* **Windows** (#63) — download and re-run the per-user installer (upgrade in place).
* **macOS** (#64) — download the matching-arch DMG and drag-replace in Applications.
* **Flatpak** (#65) — **never self-update**; defer to the system updater
  (``flatpak update``), which Flathub drives.
* **AppImage** (#66) — replace the image in place (AppImageUpdate where embedded).
* **source** — a dev checkout: pull and reinstall.

This module is the headlessly-testable core of that: it classifies the running
format, verifies a downloaded artifact's integrity before anything executes it,
and describes the per-format strategy as language-neutral keys (the bridge
localizes them). The **automated apply** for Windows & AppImage (#94) is
orchestrated here too — :func:`apply_update` — but kept pure: the download,
checksum and launch steps are injected as callables, so the whole
download → verify → launch flow is unit-tested with no network or subprocess.
The real seams (GitHub download, ``SHA256SUMS`` fetch, installer launch) live in
the bridge and are exercised by per-OS VM acceptance, so nothing in this module
runs an external program.
"""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

#: Every packaging format the updater understands; ``source`` is the dev fallback.
PACKAGE_FORMATS = ("windows", "macos", "flatpak", "appimage", "source")

# Must match the Flatpak manifest's app-id (packaging/flatpak/, #65).
_FLATPAK_APP_ID = "io.github.danilchernyshev.StudyCalc"

_REPO = "danilchernyshev/study-calc"
#: The manual-download fallback shown when an automated apply fails (#94).
RELEASES_PAGE = f"https://github.com/{_REPO}/releases/latest"


def detect_format(
    *,
    frozen: bool | None = None,
    platform: str | None = None,
    environ: "os._Environ[str] | dict[str, str] | None" = None,
) -> str:
    """Classify how this process was packaged (one of :data:`PACKAGE_FORMATS`).

    The runtime signals are checked most-specific first: Flatpak and AppImage
    both export tell-tale environment, so they win over a bare "frozen on Linux".
    All inputs are injectable so the branches are unit-tested without really
    being inside each package.
    """
    env = os.environ if environ is None else environ
    # The Flatpak runtime sets FLATPAK_ID and bind-mounts /.flatpak-info.
    if env.get("FLATPAK_ID") or os.path.exists("/.flatpak-info"):
        return "flatpak"
    # The AppImage runtime exports APPIMAGE (the mounted image's path).
    if env.get("APPIMAGE"):
        return "appimage"
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    plat = sys.platform if platform is None else platform
    if is_frozen:
        if plat.startswith("win"):
            return "windows"
        if plat == "darwin":
            return "macos"
    # A dev checkout, or a frozen Linux folder we don't ship an updater for.
    return "source"


def verify_sha256(path: "str | Path", expected_hex: str) -> bool:
    """True only if ``path`` exists and its SHA-256 matches ``expected_hex``.

    Used to gate execution of a downloaded artifact: a tampered or truncated
    download (or a missing file) returns ``False`` so the caller never runs it.
    Comparison is case-insensitive and whitespace-tolerant; never raises.
    """
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return False
    return digest.hexdigest().lower() == (expected_hex or "").strip().lower()


# Per-format apply strategy. ``self_update`` says whether the app can replace
# itself; ``instructions_key`` is the localized how-to; ``command`` (when set) is
# the exact shell line to run (Flatpak defers to the system updater).
_PLANS: dict[str, dict] = {
    "windows": {"self_update": True, "instructions_key": "updates.apply.windows"},
    "macos": {"self_update": True, "instructions_key": "updates.apply.macos"},
    "appimage": {"self_update": True, "instructions_key": "updates.apply.appimage"},
    "flatpak": {
        "self_update": False,
        "instructions_key": "updates.apply.flatpak",
        "command": f"flatpak update {_FLATPAK_APP_ID}",
    },
    "source": {"self_update": False, "instructions_key": "updates.apply.source"},
}


def update_plan(fmt: str) -> dict:
    """The apply strategy for a packaging format (falls back to the source plan)."""
    return _PLANS.get(fmt, _PLANS["source"])


# --------------------------------------------------------------------------
# Automated self-update apply (#94) — Windows & AppImage.
#
# #75 shipped detect + verify + *guidance*; this is the remaining "do it for me"
# path for the two formats that can replace themselves. The orchestration below
# is **pure and headlessly testable**: it takes the download / checksum / run
# steps as injected callables (seams), so the whole download -> verify -> launch
# flow is unit-tested with good and tampered fixtures and no real network or
# subprocess. The bridge supplies the real seams (GitHub download, SHA256SUMS
# fetch, installer launch / in-place swap), exercised by per-OS VM acceptance.
# Flatpak and source intentionally stay on the defer-to-updater guidance.
# --------------------------------------------------------------------------

#: Formats that can install an update themselves, with their release-asset name.
_AUTO_APPLY_ASSETS: dict[str, str] = {
    "windows": "study-calc-{version}-windows-setup.exe",
    "appimage": "study-calc-{version}-linux.AppImage",
}


def supports_auto_apply(fmt: str) -> bool:
    """True for formats the app can update itself (Windows, AppImage)."""
    return fmt in _AUTO_APPLY_ASSETS


def asset_name(fmt: str, version: str) -> str | None:
    """The release-asset filename to download for ``fmt``/``version`` (or ``None``)."""
    template = _AUTO_APPLY_ASSETS.get(fmt)
    return template.format(version=version) if template else None


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse a ``SHA256SUMS`` manifest (``<hex>  <name>`` lines) to ``{name: hex}``.

    Tolerant of the ``*`` binary-mode marker and extra whitespace; ignores blank
    or malformed lines. This is the manifest the release pipeline publishes (#67).
    """
    sums: dict[str, str] = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        digest, name = parts[0], parts[-1].lstrip("*")
        sums[name] = digest.lower()
    return sums


@dataclass(frozen=True)
class ApplyResult:
    """The outcome of an apply attempt, with a localizable ``code`` (``updates.apply.*``).

    ``status`` is one of ``launched`` / ``unsupported`` / ``download_failed`` /
    ``verify_failed`` / ``launch_failed``. ``path`` is the downloaded artifact
    when one was fetched (for logging / the manual-fallback link).
    """

    status: str
    code: str
    path: str | None = None
    ok: bool = False


def apply_update(
    fmt: str,
    version: str,
    *,
    download: Callable[[str], "str | Path"],
    checksums: Mapping[str, str],
    run: Callable[["Path"], None],
) -> ApplyResult:
    """Download → verify → launch the update for a self-updating format.

    The three side-effecting steps are injected so this stays pure:

    * ``download(asset_name)`` fetches the asset and returns its local path
      (raises on failure);
    * ``checksums`` maps asset name → expected SHA-256 (from the release's
      ``SHA256SUMS``, #67);
    * ``run(path)`` performs the platform action — launch the installer (Windows)
      or replace-in-place and relaunch (AppImage).

    A failed integrity check **never** calls ``run`` — the artifact is not
    executed and the caller falls back to the manual download link. Every failure
    is a structured :class:`ApplyResult` (no exceptions escape).
    """
    name = asset_name(fmt, version)
    if name is None:
        return ApplyResult("unsupported", "updates.apply.error.unsupported")

    try:
        path = Path(download(name))
    except Exception:
        return ApplyResult("download_failed", "updates.apply.error.download")

    expected = checksums.get(name)
    if not expected or not verify_sha256(path, expected):
        # Tampered / truncated / unlisted: do NOT run it.
        return ApplyResult(
            "verify_failed", "updates.apply.error.integrity", path=str(path)
        )

    try:
        run(path)
    except Exception:
        return ApplyResult("launch_failed", "updates.apply.error.launch", path=str(path))

    return ApplyResult("launched", "updates.apply.success", path=str(path), ok=True)
