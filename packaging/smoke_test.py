#!/usr/bin/env python3
"""Headless smoke test for a study-calc build (#62, epic #60).

A frozen bundle can import fine yet still be broken: a data tree left out of the
PyInstaller ``datas`` shows up only at runtime as an i18n fallback-to-key, a
missing ``elements.json`` or an unstyled, blank window. This script exercises the
real engines and asset paths **without opening a GUI**, so CI (#67) and the
platform installers can gate a release on it.

Three modes:

* **engine mode** (default) — import ``study_calc`` and actually run one of each:
  the bridge state, a physics ``solve``, a CAS ``analyze``, a unit conversion,
  ``molar_mass``, and a vector op; load all five locale catalogs; and confirm the
  bundled assets resolve through :func:`study_calc.resources.resource_path` (which
  points inside the frozen bundle when run by the frozen interpreter). This proves
  the *importable* package — source tree or frozen bundle — is whole.

* **bundle mode** (``--bundle dist/study-calc``) — additionally verify the asset
  files physically exist inside a built one-folder bundle directory, so CI can
  point at ``dist/study-calc/`` and have a deliberately removed asset fail the
  gate, without executing the frozen launcher.

* **gui mode** (``--gui``) — additionally test that PyWebView can initialize a
  GUI backend and create a window. On Linux, this verifies that gi (PyGObject)
  and the GObject-Introspection typelibs are bundled and discoverable. The
  window is created then immediately destroyed; no event loop runs. This mode
  should be run under ``xvfb-run`` on headless CI.

Exit code is ``0`` when every check passes and ``1`` on the first failure.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# The non-code asset paths the frozen app must carry, relative to the package
# root. Used both to probe the importable package and to inspect a built bundle.
_REQUIRED_ASSETS: tuple[tuple[str, ...], ...] = (
    ("data", "elements.json"),
    ("data", "knowledgebase.db"),
    ("web", "frontend", "index.html"),
    ("web", "tokens.json"),
    ("locales", "en.json"),
)

_LANGUAGES = ("en", "es", "fr", "ru", "uk")


def _check_engines() -> None:
    """Run one operation per engine; raise on any wrong or missing result."""
    from study_calc.core import cas, periodic, units, vectors
    from study_calc.domains import SECTIONS
    from study_calc.i18n import I18n
    from study_calc.resources import resource_path
    from study_calc.web.bridge import Bridge

    # 1. The bridge builds the localized shell model.
    state = Bridge().get_state()
    if not state.get("subjects") or not state.get("labels"):
        raise AssertionError("Bridge.get_state() returned an empty shell model")

    # 2. One physics solve (F = m·a -> 2·3 = 6).
    newton = SECTIONS["mechanics"][0]
    force = newton.solve("F", {"m": 2.0, "a": 3.0})
    if abs(force - 6.0) > 1e-9:
        raise AssertionError(f"physics solve returned {force!r}, expected 6.0")

    # 3. One CAS analyze.
    cas_out = cas.run("analyze", "x^2 + 2*x + 1").output_text
    if not cas_out.strip():
        raise AssertionError("cas.analyze produced no output")

    # 4. One unit conversion (1000 m -> 1 km).
    km = units.convert(1000.0, "meter", "kilometer", "length")
    if abs(km - 1.0) > 1e-9:
        raise AssertionError(f"unit conversion returned {km!r}, expected 1.0")

    # 5. molar_mass('H2O') ~ 18.015 g/mol.
    mass = periodic.molar_mass("H2O")
    if abs(mass - 18.015) > 0.05:
        raise AssertionError(f"molar_mass('H2O') returned {mass!r}, expected ~18.015")

    # 6. One vector op (|(3, 4)| = 5).
    vec_out = vectors.run("magnitude", "3,4").output_text
    if "5" not in vec_out:
        raise AssertionError(f"vector magnitude output {vec_out!r} lacks the answer 5")

    # 7. All five locale catalogs load and resolve a known key (no fallback-to-key).
    i18n = I18n()
    for lang in _LANGUAGES:
        i18n.set_language(lang)
        label = i18n.t("subject.physics")
        if not label or label == "subject.physics":
            raise AssertionError(f"locale {lang!r} did not resolve 'subject.physics'")

    # 8. Bundled assets resolve to real files at the paths the frozen app uses.
    for parts in _REQUIRED_ASSETS:
        path = resource_path(*parts)
        if not path.is_file():
            raise AssertionError(f"bundled asset missing: {'/'.join(parts)} ({path})")


def _bundle_package_root(bundle: Path) -> Path:
    """Locate ``study_calc/`` inside a built one-folder bundle directory.

    Recent PyInstaller nests bundled data under ``_internal/``; older layouts put
    it directly in the bundle root. Accept either.
    """
    for candidate in (bundle / "_internal" / "study_calc", bundle / "study_calc"):
        if candidate.is_dir():
            return candidate
    raise AssertionError(
        f"no study_calc/ asset tree found in bundle {bundle} "
        "(looked in _internal/study_calc and study_calc)"
    )


def _check_bundle(bundle: Path) -> None:
    """Verify every required asset physically exists in a built bundle dir."""
    if not bundle.is_dir():
        raise AssertionError(f"bundle directory does not exist: {bundle}")
    root = _bundle_package_root(bundle)
    for parts in _REQUIRED_ASSETS:
        path = root.joinpath(*parts)
        if not path.is_file():
            raise AssertionError(f"bundle is missing asset: {'/'.join(parts)} ({path})")


def _check_gui() -> None:
    """Test that PyWebView can initialize a GUI backend.

    On Linux, this verifies that gi (PyGObject) and GObject-Introspection
    typelibs (WebKit2, Gtk, etc.) are bundled and discoverable. The window is
    created then immediately destroyed; no event loop runs. This test should be
    run under ``xvfb-run`` on headless CI.

    Raises AssertionError if the GUI backend cannot be initialized.
    """
    import webview

    # Create a window but do not run the event loop; just verify the backend
    # initializes without raising. The window.destroy() call below prevents
    # any async event handling.
    try:
        window = webview.create_window(
            title="Study Calc - GUI Smoke Test",
            html="<h1>GUI Test</h1><p>Backend loaded successfully.</p>",
            width=400,
            height=300,
        )
        # Explicitly destroy the window to clean up the backend.
        window.destroy()
    except Exception as exc:
        raise AssertionError(f"PyWebView GUI backend failed to initialize: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        type=Path,
        default=None,
        metavar="DIR",
        help="also check a built one-folder bundle directory (e.g. dist/study-calc)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="also test PyWebView GUI backend initialization (should be run under xvfb-run on headless CI)",
    )
    args = parser.parse_args(argv)

    try:
        _check_engines()
        if args.bundle is not None:
            _check_bundle(args.bundle)
        if args.gui:
            _check_gui()
    except Exception as exc:  # noqa: BLE001 - any failure must fail the build gate
        print(f"SMOKE TEST FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
