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


# --- Debian .deb packaging inputs (#146) -------------------------------------
#
# The .deb is assembled and built by packaging/linux/build_deb.sh in the
# release CI (it needs dpkg-deb, so the archive itself is only produced there).
# These tests lint the *static inputs* the script wraps so a broken control
# field, a missing maintainer script, or a desktop entry whose Exec drifts from
# the launcher name fails fast at unit-test time rather than only on a tag.

_LINUX = _ROOT / "packaging" / "linux"
_DEB = _LINUX / "deb"


def test_deb_build_script_is_present_and_single_sources_the_version() -> None:
    """build_deb.sh exists and derives the version from app_version (not a
    hand-typed literal), so the .deb version can never drift from pyproject."""
    script = _LINUX / "build_deb.sh"
    assert script.is_file(), "packaging/linux/build_deb.sh is missing"
    text = script.read_text(encoding="utf-8")
    assert "app_version()" in text, "build_deb.sh must read the version via app_version()"
    # The canonical Debian artifact name (underscores, amd64) is what the README
    # and the release job reference.
    assert "study-calc_${VERSION}_${ARCH}" in text
    assert "dpkg-deb" in text and "--root-owner-group" in text


def test_deb_desktop_entry_matches_the_launcher() -> None:
    """The packaged .desktop must be a valid entry whose Exec/Icon line up with
    the /usr/bin/study-calc launcher and the hicolor icon name."""
    desktop = (_LINUX / "study-calc.desktop").read_text(encoding="utf-8")
    assert "[Desktop Entry]" in desktop
    assert "Type=Application" in desktop
    assert "Exec=study-calc" in desktop, "Exec must match the /usr/bin launcher symlink"
    assert "Icon=study-calc" in desktop, "Icon must match the hicolor icon stem"


def test_deb_maintainer_scripts_refresh_caches() -> None:
    """postinst/postrm exist, are POSIX sh, and refresh the desktop + icon caches
    so the menu entry appears/disappears without a re-login."""
    for name in ("postinst", "postrm"):
        script = _DEB / name
        assert script.is_file(), f"packaging/linux/deb/{name} is missing"
        text = script.read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh"), f"{name} must be POSIX sh"
        assert "update-desktop-database" in text and "gtk-update-icon-cache" in text, (
            f"{name} must refresh the desktop-entry and icon caches"
        )


def test_deb_copyright_is_machine_readable() -> None:
    """A DEP-5 copyright file ships (lintian errors without one)."""
    text = (_DEB / "copyright").read_text(encoding="utf-8")
    assert text.startswith("Format: https://www.debian.org/doc/packaging-manuals/")
    assert "License: MIT" in text


def test_deb_ships_a_lintian_override_for_opt_placement() -> None:
    """The by-design /opt bundle raises dir-or-file-in-opt; a shipped lintian
    override silences it so `lintian` reports no errors (#146). The override is
    installed as /usr/share/lintian/overrides/study-calc by the build script."""
    override = _DEB / "lintian-overrides"
    assert override.is_file(), "packaging/linux/deb/lintian-overrides is missing"
    text = override.read_text(encoding="utf-8")
    assert "dir-or-file-in-opt" in text, "override must cover dir-or-file-in-opt"
    assert "study-calc:" in text, "override line must name the package"
    assert "opt/study-calc" in text, "override must scope to the /opt bundle path"
    script = (_LINUX / "build_deb.sh").read_text(encoding="utf-8")
    assert "usr/share/lintian/overrides/study-calc" in script, (
        "build_deb.sh must install the override at the path lintian reads"
    )


def test_release_workflow_builds_and_gates_on_the_deb() -> None:
    """The release pipeline has a linux-deb job, gates the publish on it, and
    uploads the .deb artifact so it lands on the GitHub Release."""
    workflow = (_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "linux-deb:" in workflow, "release.yml must define a linux-deb job"
    assert "bash packaging/linux/build_deb.sh" in workflow
    assert "study-calc_${{ env.VERSION }}_amd64.deb" in workflow
    # The release job must depend on linux-deb, or download-artifact could run
    # before the .deb exists and miss it.
    needs_line = next(
        line for line in workflow.splitlines()
        if line.strip().startswith("needs: [linux-appimage")
    )
    assert "linux-deb" in needs_line, "release.needs must include linux-deb"
