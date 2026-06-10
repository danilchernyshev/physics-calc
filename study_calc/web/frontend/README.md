# Frontend (redesign)

The PyWebView frontend for the study-calc redesign (ADR 0001). Plain
HTML/CSS/vanilla-JS — **no build step** — so it ships as static files in the
Python package and loads over `file://` in the PyWebView window.

## Why vanilla JS

The framework choice deferred from ADR 0001 was settled here (issue #5):
**vanilla JS** with a tiny `h()` hyperscript helper. The app is small, and a
bundler/npm toolchain would complicate the Python packaging for no real gain.
Components are plain factory functions returning DOM nodes.

## Files

| File | Role |
| --- | --- |
| `dom.js` | `h(tag, attrs, children)` hyperscript helper → `window.h`. Loaded first. |
| `components.js` | The shared component factories → `window.UI`. |
| `components.css` | Component styles, **entirely on the design tokens** (`../tokens.css`). |
| `screens.js` / `screens.css` | Per-screen renderers → `window.Screens` (the physics formula screen, issue #6). |
| `shell.js` / `shell.css` | The app shell (nav rail + header, issue #4) and the screen dispatcher. |
| `index.html` | The window: loads tokens → components → screens → shell, in order. |
| `gallery.html` | Living component reference / visual-check page (open in a browser). |

## Components (`window.UI`)

Each consumes the design tokens — no hardcoded colors or sizes
(`tests/test_web_components.py` enforces this).

| Factory | Renders |
| --- | --- |
| `UI.card({title, badge, body, class})` | Rounded surface card with optional header (title + badge). |
| `UI.textInput({label, value, placeholder, mono, oninput, width})` | Labeled text field (`mono` for expressions). |
| `UI.select({label, options, value, onchange})` | Labeled dropdown. |
| `UI.button({label, variant, onclick, disabled})` | `primary` / `secondary` / `ghost` button. |
| `UI.chips({items, active, onselect})` / `UI.chip(...)` | Selectable chip row / segmented control. |
| `UI.result({label, value})` | Green answer chip. |
| `UI.errorStrip(text)` | Red error strip (renders a localized message). |
| `UI.steps([{text, formula}])` | Numbered step-by-step list. |
| `UI.rich([{kind, text, href, onclick}])` | Rich-text block (`heading`/`body`/`formula`/`label`/`link`) — folds the Tk `_RichText` vocabulary. |
| `UI.badge` / `UI.eyebrow` / `UI.hint` | Small text primitives. |

Per-screen surfaces (#6–#11) compose these — no per-screen re-implementation.

## Screens (`window.Screens`)

`screens.js` turns a per-screen model from the bridge into a self-contained
interactive node: typing and solving update the node in place, so only a nav or
language change triggers the shell's full re-render. `shell.js` dispatches on the
active item's `kind` (a `section` item → `Screens.formula`).

| Screen | Renders |
| --- | --- |
| `Screens.formula(model, ctx)` | Physics formula screen (#6): an **input card** (formula picker + per-variable fields + Compute/Clear), a **solution card** (green result or red error), and the **learning card** (theory, useful formulas, how-to-solve, key terms with a pop-up, worked example, study links). `ctx.solve(key, values)` calls the bridge. |

The screen models are built server-side in `web/screens.py` (pure Python, so the
solve flow and the learning blocks are unit-tested headlessly) and reach the
frontend via `bridge.formula_screen()` / `bridge.solve_formula()`.

## Running

```bash
uv run --extra web python -m study_calc.web   # the app
# or open gallery.html / index.html in a browser for a quick visual check
```
