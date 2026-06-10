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
from pathlib import Path

from . import screens
from .bridge import Bridge

_FRONTEND = Path(__file__).resolve().parent / "frontend"
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
        title=bridge.get_state()["labels"]["appTitle"],
        url=str(INDEX_HTML),
        js_api=bridge,
        width=1200,
        height=800,
        min_size=(960, 640),
    )
    # Pass the icon only when the asset is present; PyWebView silently ignores
    # icon= on platforms where it is not supported (e.g. macOS app bundles).
    if _WINDOW_ICON.exists():
        window_kwargs["icon"] = str(_WINDOW_ICON)
    webview.create_window(**window_kwargs)
    webview.start()
