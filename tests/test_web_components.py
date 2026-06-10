"""Shared-component tests (issue #5).

The components are vanilla JS/CSS, so they can't be instantiated under pytest.
Instead we lint the contract that matters: the frontend CSS uses **only** design
tokens (no hardcoded palette colors), the component factory surface is present
and wired into the shell, and the gallery references the modules.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "study_calc" / "web" / "frontend"

# Hex color literals. Pure-white/black semi-transparent overlays (rgba) have no
# token and are allowed; any hex (#abc / #aabbcc) means a hardcoded palette color.
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def test_frontend_css_has_no_hardcoded_hex_colors():
    offenders = {}
    for css in FRONTEND.glob("*.css"):
        hits = _HEX.findall(css.read_text(encoding="utf-8"))
        if hits:
            offenders[css.name] = hits
    assert not offenders, f"hardcoded hex colors (use tokens.css vars): {offenders}"


def test_frontend_css_references_tokens():
    css = (FRONTEND / "components.css").read_text(encoding="utf-8")
    assert "var(--color-" in css and "var(--space-" in css and "var(--radius-" in css


def test_components_expose_the_factory_surface():
    js = (FRONTEND / "components.js").read_text(encoding="utf-8")
    assert "window.UI = UI" in js
    for factory in ("card", "textInput", "select", "button", "chips", "chip",
                    "result", "errorStrip", "steps", "rich", "badge"):
        assert re.search(rf"\b{factory}\s*\(", js), f"missing component factory: {factory}"


def test_dom_helper_is_shared():
    dom = (FRONTEND / "dom.js").read_text(encoding="utf-8")
    assert "window.h = h" in dom
    # shell.js must no longer define its own h() — it relies on the shared one.
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "function h(" not in shell


def test_index_loads_component_assets_in_order():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    for asset in ("components.css", "dom.js", "components.js", "shell.js"):
        assert asset in html, f"index.html does not load {asset}"
    # dom.js (defines h) must load before components.js and shell.js use it.
    assert html.index("dom.js") < html.index("components.js") < html.index("shell.js")


def test_gallery_exists_and_uses_components():
    gallery = (FRONTEND / "gallery.html").read_text(encoding="utf-8")
    assert "components.js" in gallery and "UI.card" in gallery
