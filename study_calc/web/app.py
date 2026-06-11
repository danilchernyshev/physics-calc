"""PyWebView host window for the redesign shell (ADR 0001).

``run()`` opens the native window with :class:`~study_calc.web.bridge.Bridge` as
the ``js_api``; the frontend (``frontend/index.html`` + ``shell.css`` +
``shell.js``) renders the nav rail and header from the bridge's state.

PyWebView is an **optional** dependency (the ``web`` extra) and is imported
lazily, so importing this module — and running the test suite — never requires
it or a display. ``render_preview_html()`` produces a self-contained page with
the state pre-injected, for screenshotting the shell in a plain browser without
the bridge.
"""

from __future__ import annotations

import json
import sys

from ..resources import app_version, resource_path
from . import screens
from .bridge import Bridge

_FRONTEND = resource_path("web", "frontend")
INDEX_HTML = _FRONTEND / "index.html"
# 256×256 RGBA PNG used as the window/taskbar icon (PyWebView ``icon=`` arg).
# It ships as package data alongside the other frontend assets.
_WINDOW_ICON = _FRONTEND / "icon.png"

# Marker in index.html where the preview state is injected; empty in production
# (the real window fetches state through the bridge instead).
_STATE_MARKER = "<!-- STATE -->"


def render_preview_html(state: dict | None = None) -> str:
    """Return ``index.html`` with an initial state inlined for browser preview.

    The committed ``index.html`` carries no state; the live window calls
    ``window.pywebview.api.get_state()``. For a static preview (no PyWebView) we
    inject ``window.__STUDY_CALC_STATE__`` (the shell) plus
    ``window.__STUDY_CALC_API__`` (a stand-in for the per-screen bridge calls), so
    the same ``shell.js`` paints the shell *and* the section screens without a
    bridge. ``solve_formula`` is interactive and has no static answer, so the
    preview stub returns ``null`` (the solution card shows its ready hint); solve
    correctness is covered by the headless tests.
    """
    state = state if state is not None else Bridge().get_state()
    html = INDEX_HTML.read_text(encoding="utf-8")
    formula_screens = json.dumps(screens.all_formula_screens())
    problem_screens = json.dumps(screens.all_problem_screens())
    cas = json.dumps(screens.cas_screen())
    vectors = json.dumps(screens.vector_screen())
    converter = json.dumps(screens.converter_screen())
    # periodic_screen() is always available (standard-library only); stub the
    # two run methods so the preview grid renders but tools do nothing.
    periodic = json.dumps(screens.periodic_screen())
    guide = json.dumps(screens.guide_screen())
    inject = (
        f"<script>window.__STUDY_CALC_STATE__ = {json.dumps(state)};\n"
        f"window.__STUDY_CALC_API__ = (function () {{\n"
        f"  var byId = {formula_screens};\n"
        f"  var problemsById = {problem_screens};\n"
        f"  var cas = {cas};\n"
        f"  var vectors = {vectors};\n"
        f"  var converter = {converter};\n"
        f"  var periodic = {periodic};\n"
        f"  var guide = {guide};\n"
        f"  return {{\n"
        f"    formula_screen: function (id) {{ return byId[String(id).split(':').pop()] || null; }},\n"
        f"    solve_formula: function () {{ return null; }},\n"
        f"    problems_screen: function (id) {{ return problemsById[String(id).split(':').pop()] || null; }},\n"
        f"    cas_screen: function () {{ return cas; }},\n"
        f"    cas_run: function () {{ return null; }},\n"
        f"    vector_screen: function () {{ return vectors; }},\n"
        f"    vector_run: function () {{ return null; }},\n"
        f"    converter_screen: function () {{ return converter; }},\n"
        f"    convert_run: function () {{ return null; }},\n"
        f"    periodic_screen: function () {{ return periodic; }},\n"
        f"    molar_mass_run: function () {{ return null; }},\n"
        f"    balance_run: function () {{ return null; }},\n"
        f"    guide_screen: function () {{ return guide; }}\n"
        f"  }};\n"
        f"}})();</script>"
    )
    return html.replace(_STATE_MARKER, inject)


def run() -> None:
    """Open the shell in a PyWebView window (requires the ``web`` extra)."""
    try:
        import webview
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise SystemExit(
            "PyWebView is not installed. Install the 'web' extra, e.g.:\n"
            "  uv run --extra web python -m study_calc.web"
        ) from exc

    bridge = Bridge()
    window_kwargs: dict = dict(
        # Surface the single-sourced version in the title bar / About area.
        title=f"{bridge.get_state()['labels']['appTitle']} {app_version()}",
        url=str(INDEX_HTML),
        js_api=bridge,
        width=1200,
        height=800,
        min_size=(960, 640),
    )
    webview.create_window(**window_kwargs)
    # The window icon belongs on start() in PyWebView 6.x (not create_window).
    # Pass it only when the asset is present; backends that don't support a
    # custom icon (e.g. macOS app bundles) ignore it.
    start_kwargs: dict = {}
    if _WINDOW_ICON.exists():
        start_kwargs["icon"] = str(_WINDOW_ICON)

    # Headless backend self-test (#158/#163). `--smoke-gui` must run through THIS
    # entry point so it exercises the *frozen* interpreter's bundled GObject-
    # Introspection (gi) + typelibs — the thing #158 is about. Running the GUI
    # check via `python smoke_test.py` instead would test the build host's venv,
    # which has no bundled gi, and so could never validate the shipped bundle.
    # Here we start the real backend (forcing GTK on Linux) and tear it down from
    # the func callback, so a bundle missing gi/typelibs exits non-zero under
    # `xvfb-run dist/study-calc/study-calc --smoke-gui`.
    if "--smoke-gui" in sys.argv:
        def _smoke_teardown() -> None:
            for win in list(webview.windows):
                win.destroy()

        start_kwargs["func"] = _smoke_teardown
        if sys.platform.startswith("linux"):
            start_kwargs["gui"] = "gtk"
        webview.start(**start_kwargs)
        print("GUI SMOKE OK")
        return

    webview.start(**start_kwargs)
