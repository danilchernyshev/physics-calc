# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the GUI
python -m study_calc          # or: uv run python -m study_calc

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

Layers, deliberately decoupled so the domain logic stays UI- and
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
  references — all i18n *keys* plus plain URLs, never prose. `learning.py` is the
  **rich learning-material loader**: where `explain.py` stores i18n *keys* for the
  short static note, `learning.py` loads *prose* (`Topic`/`Concept`/`WorkedExample`
  frozen dataclasses) from the separate `study_calc/learning/` content folder
  (see below), with English fallback — so the panel can show a topic summary, the
  useful formulas, a step-by-step method, reusable glossary terms, and a worked
  example. `learning.py` also loads the **practice problems** (the `Problem`
  dataclass — a tagged `WorkedExample` plus an optional video link and backing
  topic) and exposes `problems_for_subject(subject, lang)`. `CURRICULUM_GRADES`
  maps Ontario course codes (`SPH4U`, `SCH4U`, `MDM4U`, `MHF4U`, `MCV4U`, …) to a
  grade level, rendered as a curriculum badge wherever a topic or problem carries
  `courses`. `load_topic` / `load_concept` / `load_problem` are `lru_cache`d.

- **`navigation.py`** — the **navigation layer**, kept free of Tkinter so it is
  unit-testable headlessly. `SUBJECTS` is the single source of truth for the tab
  tree: an ordered list of subjects (Physics, Math, Tools, Chemistry), each holding
  items of four kinds — `Section` (a `domains.SECTIONS` id), `Tool` (`converter`/
  `cas`/`vectors`), `Problems` (a subject's practice surface), or `Placeholder` (a
  "coming soon" notice). `gui/app.py` maps each item to a concrete widget; adding or
  reordering a subject is a one-line edit here with no widget code to touch.

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

- **`gui/app.py`** — Tkinter window. It walks `navigation.SUBJECTS` and builds one
  outer tab per subject; a subject with several items renders an inner notebook, a
  single-item subject renders that panel directly. Items become widgets via
  `_item_widget`: a `Section` → a formula panel, a `Tool` → the converter / `CasPanel`
  / vectors panel (CAS falls back to a notice tab if SymPy can't be imported), a
  `Problems` → a `ProblemsPanel` (a problem list on the left, its worked solution in
  the `ExplanationPanel` on the right). Every formula tab *and* the CAS tab is a
  horizontal `PanedWindow`: the calculator/input form on the left, an
  `ExplanationPanel` (the right-hand learning area) on the right. All read-only rich text (the panel and
  the pop-up window) is built on the shared `_RichText` widget (heading / body /
  formula / link styling; a "link" opens a URL *or* runs a callback).
  `ExplanationPanel` has three render modes on one widget: `show(Explanation,
  Topic)` paints a formula's *static* learning area — theory, **useful formulas**,
  how-to-solve, **key terms** (each a short inline blurb + an "Open full
  explanation →" link that opens a `ConceptWindow` pop-up), a **worked example**,
  and study links; `show_topic(title_key, Topic)` paints the same rich material on
  its own (the CAS tab shows it for the selected operation *before* a result);
  `show_steps(title_key, segments)` paints a *dynamic* worked solution — the CAS
  tab feeds SymPy's step-by-step through it (answers tagged green). `ConceptWindow`
  is the term pop-up: full definition + related formulas + clickable "See also"
  terms; `show_problem(Problem)` paints a practice problem's worked solution.
  Clickable references/terms open in a browser or a new window. `App`
  rebuilds *all* its widgets on language change (it destroys children and re-runs
  `_build()`), preserving the selected tab.

### Learning materials (`study_calc/learning/`)

A **separate, format-flexible content folder** (data, not code — parallel to
`locales/`) holding the *prose* the right panel shows, loaded by
`core/learning.py`. Three content kinds under `learning/<lang>/`:
`topics/<id>.json` (one bundle per problem type — a formula `key` for physics,
`cas_<op>` for Math/CAS, plus subject-prefixed ids like `chem_*`, `mdm_*`, `sph_*`),
`glossary/<term_id>.json` (reusable term definitions), and `problems/<id>.json` (a
single practice problem). `en` is canonical and the fallback (a file missing in
another language is served from `en`, mirroring i18n). A topic carries `summary`,
`terms[]` (glossary ids), `formulas[]`, `method[]`, a worked `example`, and
`courses[]` (Ontario codes for the grade badge); a concept carries `title`, `short`
(inline), `full` (pop-up), `formulas[]`, `see_also[]`; a problem carries `subject`
(a `navigation.SUBJECTS` id), the worked-example fields, an optional `video_url` and
backing `topic`, and `courses[]`. All content is **original** (written from OpenStax
+ general knowledge); CollegePhysicsAnswers videos are linked only, never copied.
`tests/test_learning.py` enforces that every formula and CAS op has a topic, every
referenced term resolves, and `see_also` links don't dangle; `tests/test_problems.py`
checks the problem set (subject filtering, course codes, video URLs). See
`learning/README.md` for the schema and how to extend it.

### The i18n contract (most important to preserve)

The domain layer **never stores display strings** — only message *keys*
(`Variable.name_key` like `"var.force"`, `unit_key` like `"unit.newton"`,
`Formula.name_key`). Likewise `units.py` uses language-neutral ids
(`"length"`, `"celsius"`) resolved via `category.<id>` / `unit.<id>` keys.
Errors carry a machine `code` + params, not prose. All resolution happens in
`i18n.py` (the `i18n` singleton and `t()` shortcut) and the GUI.

Each language is a flat `{key: text}` JSON file in `study_calc/locales/`
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
CollegePhysicsAnswers chapter slug (verify both resolve). For the **rich learning
material** (useful formulas, method, key terms, worked example), add
`learning/en/topics/<key>.json` and a `learning/en/glossary/<term_id>.json` for any
term it references that doesn't exist yet (`tests/test_learning.py` requires both).
The GUI picks all of this up automatically — no GUI edits needed.
