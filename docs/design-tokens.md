# Design tokens

The redesign's visual style — colors, typography, spacing, radii, elevation — is
captured once as **named, semantic tokens** so every surface stays consistent and
a theme change is a one-place edit. This is the design-system foundation for
issue #3 and the constraint set by [ADR 0001](adr/0001-ui-framework.md): the
tokens are the single source of truth that the PyWebView frontend (and its shared
components, issue #5) consume as CSS custom properties.

## Files

| File | Role |
| --- | --- |
| [`study_calc/web/tokens.json`](../study_calc/web/tokens.json) | **Canonical** source of truth. Framework-agnostic JSON; edit this. |
| [`study_calc/web/tokens.py`](../study_calc/web/tokens.py) | Loader (`load_tokens()`) + CSS generator (`css_variables()`, `write_css()`). |
| [`study_calc/web/frontend/tokens.css`](../study_calc/web/frontend/tokens.css) | **Generated** `:root` custom properties, beside the other stylesheets the frontend serves. Do not hand-edit. |

Regenerate the CSS after changing the JSON:

```bash
python -m study_calc.web.tokens
```

`tests/test_tokens.py` fails if the committed CSS drifts from the JSON, if the
color palette no longer matches Figma, or if a required semantic key is missing.

## Origin

- **Colors** are taken **verbatim** from the Figma `study-calc/color` variable
  collection (22 variables) in file
  [`1RKI6SYs0PJ5EEA0JQzLf7`](https://www.figma.com/design/1RKI6SYs0PJ5EEA0JQzLf7),
  names and all (`bg/app`, `text/on-brand`, `success/soft`, …).
- **Typography, spacing, radii, elevation** are **rationalized scales** read off
  the design frames (the CAS screen, node `2:2`, as reference). The screens were
  not built on a strict grid, so these are clean scales that the organic values
  snap onto — not a byte-for-byte copy. The one shadow in the design is captured
  exactly as `elevation.card`.

## Naming → CSS

Each token becomes a CSS custom property named `--<group>-<key>`, with `/` and
`.` in the key replaced by `-`:

| JSON | CSS variable |
| --- | --- |
| `color["bg/app"]` | `--color-bg-app` |
| `color["text/on-brand"]` | `--color-text-on-brand` |
| `font-size.base` | `--font-size-base` (`14px`) |
| `font-weight.semibold` | `--font-weight-semibold` (`600`) |
| `space.md` | `--space-md` (`12px`) |
| `radius.pill` | `--radius-pill` (`999px`) |
| `elevation.card` | `--elevation-card` |

Unit conventions: `font-size`, `space`, `radius` emit `px`; `font-weight` and
`line-height` are unitless; `color`, `font-family`, `elevation` are verbatim
strings.

## The tokens

### Color (semantic)

| Group | Token | Value | Use |
| --- | --- | --- | --- |
| Background | `bg/app` | `#eef1f8` | App canvas behind cards |
| | `bg/surface` | `#ffffff` | Card / panel surface |
| | `bg/subtle` | `#f7f9fc` | Inset areas, table rows, inputs |
| | `bg/nav` | `#0f1b2d` | Dark left nav rail |
| | `bg/nav-active` | `#1e3a6b` | Active nav item |
| Brand | `brand/primary` | `#3b5bdb` | Primary buttons, active tab, accents |
| | `brand/hover` | `#2f49b2` | Primary hover/pressed |
| | `brand/soft` | `#e7ecfb` | Soft brand fills, selected chips |
| Accent | `accent/link` | `#1a5fb4` | Hyperlinks |
| Status | `success` | `#0ca678` | Result / correct |
| | `success/soft` | `#e3f8f1` | Result box, success strip |
| | `danger` | `#e03131` | Error border / wrong answer |
| | `danger/soft` | `#fdecec` | Error strip background |
| | `warn/soft` | `#fff4e2` | Warning strip background |
| Text | `text/strong` | `#16213a` | Headings |
| | `text/body` | `#475569` | Body copy |
| | `text/muted` | `#94a3b8` | Captions, uppercase eyebrow labels |
| | `text/on-dark` | `#e8edf6` | Text on the nav rail |
| | `text/on-brand` | `#ffffff` | Text on primary fills |
| Line | `border` | `#e2e8f0` | Default 1px borders, dividers |
| | `border/strong` | `#cbd5e1` | Emphasised borders |
| Misc | `formula` | `#1b3a6b` | Rendered formula / expression text |

### Typography

- **Family:** `font-family.sans` is the Inter stack used throughout the design;
  `font-family.mono` is a *derived* monospace stack for rendering expressions/code
  (no exact Figma counterpart).
- **Weight:** `regular` 400, `medium` 500, `semibold` 600, `bold` 700.
- **Size:** `eyebrow` 11, `xs` 12, `sm` 13, `base` 14, `md` 15, `lg` 17, `xl` 18,
  `2xl` 24 (px). `base` is body text; `lg`/`xl` are card and header titles; `2xl`
  is the screen title / large result; `eyebrow` is the uppercase section labels.
- **Line height:** `tight` 1.2, `normal` 1.4, `relaxed` 1.5 (unitless).

### Spacing

A ~4px scale with a 6px half-step: `3xs` 2, `2xs` 4, `xs` 6, `sm` 8, `md` 12,
`lg` 16, `xl` 20, `2xl` 24, `3xl` 32 (px). Use for gaps and padding.

### Radius

`xs` 2, `sm` 8 (chips, inputs), `md` 10 (cards, buttons), `lg` 16 (large cards),
`pill` 999 (fully-rounded chips/pills).

### Elevation

`none`; `card` = `0 8px 24px rgba(26, 41, 77, 0.08)` (exact from Figma — the card
shadow). `sm` and `raised` are *derived* steps for inputs and hover states that
the component work (issue #5) will need.

### Series (element families — periodic-table screen, issue #10)

| Token | Value | Element family |
| --- | --- | --- |
| `alkali-metal` | `#ff8a80` | Alkali metals (Li, Na, K …) |
| `alkaline-earth-metal` | `#ffd180` | Alkaline-earth metals (Be, Mg, Ca …) |
| `transition-metal` | `#ffe0b2` | Transition metals (Fe, Cu, Zn …) |
| `post-transition-metal` | `#c5e1a5` | Post-transition metals (Al, Ga, In …) |
| `metalloid` | `#80cbc4` | Metalloids (B, Si, Ge …) |
| `diatomic-nonmetal` | `#a5d6a7` | Diatomic nonmetals (H, C, N, O, F …) |
| `polyatomic-nonmetal` | `#a5d6a7` | Polyatomic nonmetals (S, Se, Te …) |
| `noble-gas` | `#b39ddb` | Noble gases (He, Ne, Ar …) |
| `lanthanide` | `#f48fb1` | Lanthanides (La–Lu) |
| `actinide` | `#ce93d8` | Actinides (Ac–Lr) |
| `default` | `#e0e0e0` | Unknown / synthetic (Z ≥ 113 where category is unconfirmed) |

These values mirror the Tk `PeriodicTablePanel._COLORS` palette exactly so the
web UI matches the desktop app. CSS variables are `--series-<slug>` (group name
is `series`, not nested under `color`); referenced as `var(--series-alkali-metal)`
etc. in `screens.css`. The slug for each element is pre-computed in
`screens.periodic_screen()` via `_CATEGORY_SERIES` and shipped in the model, so
the renderer never needs to repeat the mapping.

## Using them

In CSS, link `tokens.css` and reference the variables:

```css
.card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--elevation-card);
  padding: var(--space-lg);
  color: var(--color-text-body);
  font-family: var(--font-family-sans);
  font-size: var(--font-size-base);
}
```

In Python (e.g. to inline the variables into the host HTML):

```python
from study_calc.web import tokens

css_block = tokens.css_variables()   # ":root { --color-...; ... }"
palette = tokens.load_tokens()["color"]
```
