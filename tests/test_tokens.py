"""Design-token tests (issue #3).

Assert the token set loads, exposes the required semantic keys (so downstream
component work can rely on them), reproduces the Figma color collection exactly,
and that the committed ``tokens.css`` is in sync with ``tokens.json``.
"""

from __future__ import annotations

from study_calc.web import tokens

# The full Figma ``study-calc/color`` collection (22 variables), names verbatim.
# This is the spot-check that the palette matches the design frame.
FIGMA_COLORS = {
    "bg/app": "#eef1f8",
    "bg/surface": "#ffffff",
    "bg/subtle": "#f7f9fc",
    "bg/nav": "#0f1b2d",
    "bg/nav-active": "#1e3a6b",
    "brand/primary": "#3b5bdb",
    "brand/hover": "#2f49b2",
    "brand/soft": "#e7ecfb",
    "accent/link": "#1a5fb4",
    "success": "#0ca678",
    "success/soft": "#e3f8f1",
    "danger": "#e03131",
    "danger/soft": "#fdecec",
    "warn/soft": "#fff4e2",
    "text/strong": "#16213a",
    "text/body": "#475569",
    "text/muted": "#94a3b8",
    "text/on-dark": "#e8edf6",
    "text/on-brand": "#ffffff",
    "border": "#e2e8f0",
    "border/strong": "#cbd5e1",
    "formula": "#1b3a6b",
}

# Minimum semantic keys each non-color group must expose.
REQUIRED_KEYS = {
    "font-family": {"sans", "mono"},
    "font-weight": {"regular", "medium", "semibold", "bold"},
    "font-size": {"eyebrow", "xs", "sm", "base", "md", "lg", "xl", "2xl"},
    "line-height": {"tight", "normal", "relaxed"},
    "space": {"3xs", "2xs", "xs", "sm", "md", "lg", "xl", "2xl", "3xl"},
    "radius": {"xs", "sm", "md", "lg", "pill"},
    # All four levels are defined and in use: --elevation-raised backs .modal__card
    # in web/frontend/screens.css, so dropping it would degrade that CSS to an
    # undefined variable (issue #25).
    "elevation": {"none", "sm", "card", "raised"},
}


def test_tokens_load():
    data = tokens.load_tokens()
    assert isinstance(data, dict)
    for group in tokens.GROUPS:
        assert group in data, f"missing token group: {group}"
        assert data[group], f"empty token group: {group}"


def test_color_palette_matches_figma():
    colors = tokens.load_tokens()["color"]
    assert colors == FIGMA_COLORS, "color tokens drifted from the Figma collection"


def test_required_semantic_keys_present():
    data = tokens.load_tokens()
    for group, keys in REQUIRED_KEYS.items():
        missing = keys - set(data[group])
        assert not missing, f"{group} missing semantic keys: {sorted(missing)}"


def test_css_variables_render_each_token():
    css = tokens.css_variables()
    assert css.startswith("/*")
    assert ":root {" in css and css.rstrip().endswith("}")
    # A few representative variables, with their unit conventions.
    assert "--color-bg-app: #eef1f8;" in css
    assert "--color-text-on-brand: #ffffff;" in css
    assert "--font-size-base: 14px;" in css
    assert "--font-weight-semibold: 600;" in css
    assert "--line-height-normal: 1.4;" in css
    assert "--space-md: 12px;" in css
    assert "--radius-pill: 999px;" in css
    assert "--elevation-card: 0 8px 24px rgba(26, 41, 77, 0.08);" in css


def test_committed_css_is_in_sync():
    on_disk = tokens.CSS_PATH.read_text(encoding="utf-8")
    assert on_disk == tokens.css_variables(), (
        "tokens.css is stale — regenerate with `python -m study_calc.web.tokens`"
    )
