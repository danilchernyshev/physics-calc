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
distros: `sudo apt-get install -y python3-tk`). The only runtime dependency is
`sympy` (powers the symbolic-math / CAS tab); the physics-formula and converter
tabs use nothing but the standard library, and the GUI degrades to a notice tab
if `sympy` is somehow absent. `pytest` is the sole dev dependency.

## Architecture

Three layers, deliberately decoupled so the domain logic stays UI- and
language-agnostic:

- **`core/`** — the engine. `formula.py` defines `Formula`/`Variable` and the
  "solve for any variable" model: each `Formula` carries a `solvers` dict
  mapping a variable symbol to a function computing it from the others. `solve()`
  translates every failure (missing value, division by zero, complex/`NaN`
  result) into a `SolveError` with a stable `code`. `units.py` is the converter:
  linear categories convert through an SI base unit via a factor table;
  temperature is special-cased with to/from-kelvin function pairs. `cas.py` is
  the symbolic engine: a thin SymPy wrapper (`analyze`/`simplify`/`expand`/
  `factor`/`derivative`/`integral`/`series`/`solve`/`evaluate`) that parses input
  through a **sandboxed** `parse_expr` (blanked `__builtins__`, SymPy-only
  namespace — so input never executes as Python) and raises `CasError` with a
  stable `code`, mirroring `SolveError`. It auto-detects the working variable
  from the expression's lone free symbol (à la Wolfram Alpha), and `analyze` is a
  SymPy-Gamma-style overview that returns many views at once. Every result also
  carries an ordered, localizable explanation as `CasStep(key, params)` items
  (same i18n-key discipline as errors) — the `cas.step.*` keys. `explain.py` is
  the **learning-content model** (deliberately Physics- and Math-agnostic so it
  can back both): `Reference(label_key, url)` is a link to study material, and
  `Explanation(theory_key, steps_keys, references)` bundles a theory note, the
  "how to solve" steps (defaulting to the shared `DEFAULT_SOLVE_STEPS`), and
  references — all i18n *keys* plus plain URLs, never prose.

- **`domains/`** — declarative formula sets, one module per physics section
  (mechanics, thermodynamics, electromagnetism, waves). `domains/__init__.py`
  exposes the ordered `SECTIONS` dict (section id → formula list); its order is
  the GUI tab order. `domains/references.py` is the **single registry of study
  links**, keyed by a formula's `key`: it maps each formula to a verified OpenStax
  *College Physics* section (`ref.openstax`) and a CollegePhysicsAnswers chapter
  of video solutions (`ref.cpanswers`), and `explanation_for(key)` assembles the
  full `Explanation` (theory at the conventional `theory.<key>` i18n key + default
  steps + those references). To add references for a new formula, add one row to
  `_SOURCES` there — slugs should be checked to resolve (HTTP 200) before commit.

- **`gui/app.py`** — Tkinter window. One tab per section, a converter tab, and a
  CAS tab (`CasPanel`, added by `_build_cas_tab` which falls back to a notice tab
  if SymPy can't be imported). Every section tab *and* the CAS tab is a horizontal
  `PanedWindow`: the calculator/input form on the left, an `ExplanationPanel` (the
  right-hand learning area) on the right. `ExplanationPanel` has two render modes,
  so the same widget serves both: `show(Explanation)` paints a formula's *static*
  theory / how-to-solve / study links, while `show_steps(title_key, segments)`
  paints a *dynamic* worked solution — the CAS tab feeds SymPy's step-by-step
  through it (answers tagged green), and Math will reuse it. Clickable references
  open in a browser. `App` rebuilds *all* its widgets on language change (it
  destroys children and re-runs `_build()`), preserving the selected tab.

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

The **explanation keys** (`theory.<formula>`, the `steps.solve.*` and the short
panel labels `ui.theory`/`ui.how_to_solve`/`ui.learn_more`/`ref.*`) are a
deliberate exception: they are *not* in the test-enforced required set. `en` and
`ru` carry the full theory paragraphs; `es`/`fr`/`uk` have the short labels but
let the longer `theory.*` text fall back to English. `tests/test_references.py`
only requires `theory.*` to exist in `en` (the fallback), plus that every formula
maps to its two study links. Translating the remaining `theory.*` into es/fr/uk
later is purely additive.

### Adding a formula

Add a `Formula` to the relevant `domains/*.py` module with one solver per
variable you want to be computable, then add its `formula.*`, `var.*`, and
`unit.*` keys to all five locale files. To give it the right-hand learning panel,
add a `theory.<key>` paragraph (at least to `en`, ideally `ru`) and one row to
`_SOURCES` in `domains/references.py` mapping it to an OpenStax section slug and a
CollegePhysicsAnswers chapter slug (verify both resolve). The GUI picks all of
this up automatically — no GUI edits needed.
