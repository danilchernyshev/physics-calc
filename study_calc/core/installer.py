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
localizes them). Actually launching an installer / swapping a file is the
platform step exercised by per-OS acceptance, not here — so nothing in this
module runs an external program.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

#: Every packaging format the updater understands; ``source`` is the dev fallback.
PACKAGE_FORMATS = ("windows", "macos", "flatpak", "appimage", "source")

# Must match the Flatpak manifest's app-id (packaging/flatpak/, #65).
_FLATPAK_APP_ID = "io.github.danilchernyshev.StudyCalc"


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
