"""Design tokens: the single source of truth for the redesign's visual style.

``tokens.json`` (next to this module) is the canonical, framework-agnostic
definition — colors, typography, spacing, radii and elevation, with semantic
names lifted from the Figma ``study-calc/color`` collection and the design
frames (see ``docs/design-tokens.md``). This module loads that JSON and emits it
as **CSS custom properties** (``study_calc/web/frontend/tokens.css``) for the
PyWebView frontend chosen in ADR 0001. The CSS lives *inside* ``frontend/`` so it
is a sibling of the other stylesheets: PyWebView serves that directory as the web
root, and a stylesheet above it would 404 and leave the UI unstyled.

The CSS file is committed and kept in sync with the JSON; regenerate it with::

    python -m study_calc.web.tokens

``tests/test_tokens.py`` asserts the token set loads, exposes the required
semantic keys, and that the committed CSS matches what this module generates.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..resources import resource_path

TOKENS_PATH = resource_path("web", "tokens.json")
CSS_PATH = resource_path("web", "frontend", "tokens.css")

# Token groups, in the order they appear in the generated CSS. Every group is a
# flat ``{name: value}`` map; ``$meta`` is documentation only and never emitted.
GROUPS: tuple[str, ...] = (
    "color",
    "font-family",
    "font-weight",
    "font-size",
    "line-height",
    "space",
    "radius",
    "elevation",
    # Element-series backgrounds for the periodic-table screen (issue #10).
    # Each slug maps to var(--series-<slug>) and is baked into the element
    # model by screens.periodic_screen(); values mirror gui.app._COLORS exactly.
    "series",
)

# How each group's values become CSS: numeric groups that carry a pixel unit,
# numeric groups that are unitless, and groups whose values are emitted verbatim.
_PX_GROUPS = frozenset({"font-size", "space", "radius"})
_UNITLESS_GROUPS = frozenset({"font-weight", "line-height"})


@lru_cache(maxsize=1)
def load_tokens() -> dict:
    """Return the parsed ``tokens.json`` (cached)."""
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def _css_var_name(group: str, key: str) -> str:
    """``("color", "bg/app")`` -> ``"--color-bg-app"``."""
    slug = key.replace("/", "-").replace(".", "-")
    return f"--{group}-{slug}"


def _css_value(group: str, value) -> str:
    """Format a token value for CSS, applying the group's unit convention."""
    if group in _PX_GROUPS:
        return f"{value}px"
    if group in _UNITLESS_GROUPS:
        return str(value)
    return str(value)


def css_variables(tokens: dict | None = None) -> str:
    """Render the tokens as a ``:root { ... }`` CSS custom-property block."""
    tokens = tokens if tokens is not None else load_tokens()
    lines = [
        "/* GENERATED from study_calc/web/tokens.json by"
        " study_calc/web/tokens.py — do not edit by hand. */",
        "/* Regenerate with: python -m study_calc.web.tokens */",
        ":root {",
    ]
    for group in GROUPS:
        values = tokens.get(group, {})
        if not values:
            continue
        lines.append(f"  /* {group} */")
        for key, value in values.items():
            lines.append(f"  {_css_var_name(group, key)}: {_css_value(group, value)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_css(path: Path | None = None) -> Path:
    """Regenerate the committed ``tokens.css`` from ``tokens.json``."""
    path = path if path is not None else CSS_PATH
    path.write_text(css_variables(), encoding="utf-8")
    return path


if __name__ == "__main__":
    out = write_css()
    # resource_path() (no args) is the package root; its parent is the repo root,
    # so this prints the committed CSS path relative to the checkout.
    print(f"Wrote {out.relative_to(resource_path().parent)}")
