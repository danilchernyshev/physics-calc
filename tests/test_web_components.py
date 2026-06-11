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
    # tokens.css is the generated palette — the single home of hex literals; the
    # hand-written stylesheets must reference its variables instead.
    offenders = {}
    for css in FRONTEND.glob("*.css"):
        if css.name == "tokens.css":
            continue
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


# --- issue #26: keyboard navigation and ARIA accessibility -------------------
#
# The components/CSS/shell are vanilla JS, so we lint the structural a11y
# contract from source the same way the token checks above do.


def test_button_and_chip_factories_render_native_buttons():
    """Interactive controls must be real <button>s (focusable + Space/Enter
    activatable for free) rather than clickable <div>s (issue #26)."""
    js = (FRONTEND / "components.js").read_text(encoding="utf-8")
    # The button() and chip() factories build a native <button> element.
    button_body = js[js.index("button({"):js.index("chips({")]
    assert "h('button'" in button_body, "UI.button must render a <button> element"
    chip_body = js[js.index("chip({"):js.index("result({")]
    assert "h('button'" in chip_body, "UI.chip must render a <button> element"


def test_focus_indicators_are_token_based_and_visible():
    """A visible :focus-visible ring exists and is built on a design token; no
    interactive element drops the outline without a replacement (issue #26)."""
    css = (FRONTEND / "components.css").read_text(encoding="utf-8")
    assert ":focus-visible" in css, "components.css must define a :focus-visible ring"
    # The ring colour is a token, not a hardcoded value: the first :focus-visible
    # rule block declares an outline built on a --color-* variable. (Plain string
    # scanning, not a regex — avoids any backtracking/ReDoS surface.)
    fv = css.index(":focus-visible")
    block = css[fv:css.index("}", fv)]
    assert "outline:" in block and "var(--color-" in block, (
        "the :focus-visible outline must use a --color-* token"
    )
    # Any `outline: none` must sit on a :focus-visible-guarded selector so
    # keyboard focus still shows a ring. Scan the whitespace-stripped text so the
    # match is independent of formatting.
    packed = "".join(css.split())
    start = 0
    while True:
        i = packed.find("outline:none", start)
        if i == -1:
            break
        brace = packed.rfind("{", 0, i)
        selector = packed[packed.rfind("}", 0, brace) + 1:brace]
        assert ":focus-visible" in selector, (
            f"`outline: none` on selector {selector!r} has no :focus-visible replacement"
        )
        start = i + len("outline:none")


def test_modal_overlays_carry_dialog_semantics_and_keyboard_trap():
    """Every body-level overlay is a focus-trapping dialog dismissable by
    Escape, wired through the shared helper (issue #26)."""
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # The shared keyboard helper handles Escape + the Tab focus-trap once.
    assert "function _wireModalKeys(" in js
    assert "e.key === 'Escape'" in js and "if (e.key !== 'Tab') return;" in js
    # All three overlays opt into dialog semantics and the shared key handler.
    assert js.count("role: 'dialog'") >= 3, "openGuide/openUpdates/openConcept dialogs"
    assert js.count("'aria-modal': 'true'") >= 3
    assert js.count("_wireModalKeys(overlay, close)") >= 3


def test_nav_rail_region_is_labeled():
    """The nav rail is a labeled landmark and the language toggle exposes its
    expanded state (issue #26)."""
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    nav_call = shell[shell.index("h('nav'"):shell.index("h('div', { class: 'nav__logo'")]
    assert "'aria-label'" in nav_call, "the nav rail must carry an aria-label"
    assert "'aria-expanded'" in shell, "the language toggle must expose aria-expanded"
