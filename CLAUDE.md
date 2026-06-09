# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the GUI
python -m physics_calc          # or: uv run python -m physics_calc

# Tests (no graphical environment needed — they cover core + i18n, not the GUI)
uv run --extra dev pytest       # or: pytest
uv run --extra dev pytest tests/test_formulas.py::test_name   # a single test
```

Requires Python ≥ 3.10 and Tkinter (a separate system package on some Linux
distros: `sudo apt-get install -y python3-tk`). Runtime dependencies are zero —
only the standard library; `pytest` is the sole dev dependency.

## Architecture

Three layers, deliberately decoupled so the domain logic stays UI- and
language-agnostic:

- **`core/`** — the engine. `formula.py` defines `Formula`/`Variable` and the
  "solve for any variable" model: each `Formula` carries a `solvers` dict
  mapping a variable symbol to a function computing it from the others. `solve()`
  translates every failure (missing value, division by zero, complex/`NaN`
  result) into a `SolveError` with a stable `code`. `units.py` is the converter:
  linear categories convert through an SI base unit via a factor table;
  temperature is special-cased with to/from-kelvin function pairs.

- **`domains/`** — declarative formula sets, one module per physics section
  (mechanics, thermodynamics, electromagnetism, waves). `domains/__init__.py`
  exposes the ordered `SECTIONS` dict (section id → formula list); its order is
  the GUI tab order.

- **`gui/app.py`** — Tkinter window. One tab per section plus a converter tab.
  `App` rebuilds *all* its widgets on language change (it destroys children and
  re-runs `_build()`), preserving the selected tab.

### The i18n contract (most important to preserve)

The domain layer **never stores display strings** — only message *keys*
(`Variable.name_key` like `"var.force"`, `unit_key` like `"unit.newton"`,
`Formula.name_key`). Likewise `units.py` uses language-neutral ids
(`"length"`, `"celsius"`) resolved via `category.<id>` / `unit.<id>` keys.
Errors carry a machine `code` + params, not prose. All resolution happens in
`i18n.py` (the `i18n` singleton and `t()` shortcut) and the GUI.

Each language is a flat `{key: text}` JSON file in `physics_calc/locales/`
(`en`, `es`, `fr`, `ru`, `uk`). `en` is the default and fallback — a missing
key in another catalog falls back to English, then to the key itself, so a
partial translation never crashes the UI.

When you **add or change a formula, unit, or error code**, update *every*
locale JSON. `tests/test_i18n.py` enforces this: `_all_required_keys()` walks
`SECTIONS` and the converter and asserts each catalog (and the error-key list)
is complete — these tests fail loudly on a missing translation.

### Adding a formula

Add a `Formula` to the relevant `domains/*.py` module with one solver per
variable you want to be computable, then add its `formula.*`, `var.*`, and
`unit.*` keys to all five locale files. The GUI picks it up automatically — no
GUI edits needed.
