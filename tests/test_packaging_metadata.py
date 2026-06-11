"""Guard that hand-written packaging metadata stays in sync with the version.

The single source of truth for the version is ``pyproject.toml``'s
``project.version`` (surfaced by :func:`study_calc.resources.app_version`).
Most build inputs derive the version from it at build time (the PyInstaller spec,
the Inno Setup ``/DMyAppVersion``, the DMG/AppImage/Flatpak build scripts, and the
CI ``resolve-version`` job, which even asserts the pushed tag matches pyproject).

One field does **not**: the Flatpak AppStream ``metainfo.xml`` ``<release>`` entry,
which GNOME Software / KDE Discover show as the app's latest version. A version
bump that forgets to add a ``<release>`` line drifts silently — the app ships as
0.8.0 while its store page still advertises 0.7.0 (issue #100). These tests fail
loudly on that drift so a bump can never leave the packaging metadata behind.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from study_calc.resources import app_version

_ROOT = Path(__file__).resolve().parent.parent
_METAINFO = (
    _ROOT
    / "packaging"
    / "flatpak"
    / "io.github.danilchernyshev.StudyCalc.metainfo.xml"
)


def _release_versions() -> list[str]:
    root = ET.parse(_METAINFO).getroot()
    return [r.get("version", "") for r in root.findall("./releases/release")]


def test_flatpak_metainfo_lists_the_current_version() -> None:
    """The newest ``<release>`` must be the current project version."""
    versions = _release_versions()
    assert versions, f"no <release> entries in {_METAINFO.name}"
    # AppStream lists newest first; the top entry is what software centres show.
    assert versions[0] == app_version(), (
        f"{_METAINFO.name} advertises {versions[0]} as the latest release, but "
        f"the project is on {app_version()} — add a <release> entry for the bump "
        f"(issue #100)."
    )


def test_flatpak_metainfo_releases_are_unique_and_descending() -> None:
    """Release history is well-formed: no duplicate versions, newest first."""
    versions = _release_versions()
    assert len(versions) == len(set(versions)), f"duplicate <release> in {versions}"
    parsed = [tuple(int(p) for p in v.split(".")) for v in versions]
    assert parsed == sorted(parsed, reverse=True), (
        f"<release> entries must be newest-first; got {versions}"
    )
