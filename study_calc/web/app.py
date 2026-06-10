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

from .bridge import Bridge

_FRONTEND = Path(__file__).resolve().parent / "frontend"
INDEX_HTML = _FRONTEND / "index.html"

# Marker in index.html where the preview state is injected; empty in production
# (the real window fetches state through the bridge instead).
_STATE_MARKER = "<!-- STATE -->"


def render_preview_html(state: dict | None = None) -> str:
    """Return ``index.html`` with an initial state inlined for browser preview.

    The committed ``index.html`` carries no state; the live window calls
    ``window.pywebview.api.get_state()``. For a static preview (no PyWebView) we
    inject ``window.__STUDY_CALC_STATE__`` so the same ``shell.js`` paints
    without a bridge.
    """
    state = state if state is not None else Bridge().get_state()
    html = INDEX_HTML.read_text(encoding="utf-8")
    inject = f"<script>window.__STUDY_CALC_STATE__ = {json.dumps(state)};</script>"
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
    webview.create_window(
        title=bridge.get_state()["labels"]["appTitle"],
        url=str(INDEX_HTML),
        js_api=bridge,
        width=1200,
        height=800,
        min_size=(960, 640),
    )
    webview.start()
