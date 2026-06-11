# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (opens the PyWebView desktop window)
uv run python -m study_calc   # or: uv run study-calc-web

# Tests (no graphical environment needed — they cover core + i18n, not the web UI)
uv run --extra dev pytest       # or: pytest
uv run --extra dev pytest tests/test_formulas.py::test_name   # a single test
```

Requires Python ≥ 3.10 and a graphical session (the app is a desktop window).
The runtime dependencies are `sympy` (powers the symbolic-math / CAS screen) and
`pywebview` (draws the window over each platform's native web view — WebView2 on
Windows, WebKit on macOS, WebKit2GTK on Linux); on Linux that GTK backend also
needs the distro's PyGObject + WebKit2GTK system packages (see README.md). The
physics/chemistry-formula, converter, vectors and periodic-table screens use
nothing but the standard library, and the CAS screen degrades to a notice if
`sympy` is somehow absent. `pytest` is the sole dev dependency. (`matplotlib`
lives behind the reserved `graph` extra for a not-yet-built web graphing surface,
and the historical `web` extra is now a no-op alias kept so older `--extra web`
invocations still resolve.)

## Architecture

> **Paths in this doc** are relative to the `study_calc/` package — `web/bridge.py`
> means `study_calc/web/bridge.py`, `core/` means `study_calc/core/`. The one trap:
> **`navigation.py` lives at the package root** (`study_calc/navigation.py`), *not*
> under `web/`. Agents reading handoff briefs should use these real paths (EP-17).

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
  `periodic.py` is the **chemistry engine** (the counterpart to `cas`/`vectors`,
  standard library only): it loads the 118-element periodic table from the
  separate `study_calc/data/elements.json` and offers `molar_mass()` (parses a
  formula like `Ca(OH)2`, nested parentheses included, summing IUPAC atomic
  weights), `composition()`, and `balance()` (exact integer coefficients via the
  `Fraction` null space of the element-count matrix). Failures raise `ChemError`
  with a stable `code`, mirroring `SolveError`/`CasError`/`VectorError`.

- **`navigation.py`** — the **navigation layer**, kept free of any UI framework so
  it is unit-testable headlessly. `SUBJECTS` is the single source of truth for the
  nav tree: an ordered list of subjects (Physics, Math, Tools, Chemistry), each
  holding items of four kinds — `Section` (a `domains.SECTIONS` id), `Tool`
  (`converter`/`cas`/`vectors`/`periodic_table`), `Problems` (a subject's practice
  surface), or `Placeholder` (a "coming soon" notice). The Chemistry subject
  bundles two formula `Section`s, the periodic-table `Tool`, and its `Problems`.
  `web/bridge.py` maps each item to a screen; adding or reordering a subject is a
  one-line edit here with no frontend code to touch. The `item_kind` / `item_id` /
  `item_label_key` helpers expose each item's kind, a stable id, and its i18n label
  key, so the bridge derives every label the same way.

- **`web/`** — the **frontend** and the project's only UI (ADR 0001 chose a
  PyWebView web UI over Tkinter, which has since been removed; see
  `docs/adr/0001-ui-framework.md`). It reuses `core`/`domains`/`navigation`/i18n
  unchanged. `tokens.json` is the framework-agnostic design-token source of truth
  (`tokens.py` emits `frontend/tokens.css` — beside the other stylesheets, since
  PyWebView serves `frontend/` as the web root; `docs/design-tokens.md`).
  `bridge.py` is the **JS↔Python `js_api`** — pure Python, no PyWebView import, so
  it's unit-tested headlessly: it builds the localized shell model (subjects/items
  + chrome labels) entirely from `navigation.SUBJECTS`, dispatches each item to its
  per-screen model from `screens.py`, and `set_language` relabels without
  restructuring. `screens.py` builds every **per-screen view-model** in pure Python
  (`formula_screen`/`solve_formula`, `cas_screen`/`cas_run`, `vector_screen`,
  `converter_screen`, `periodic_screen`, `problems_screen`, `guide_screen`), so the
  solve flow and the learning blocks are unit-tested headlessly. `app.py` imports
  PyWebView (now a core dependency) to open the window over `frontend/`
  (`index.html` + `shell.css` using the tokens + vanilla-JS `shell.js`), and
  `render_preview_html()` inlines the state for a browser/screenshot preview without
  the bridge. The frontend is **vanilla JS, no build step** (the framework choice
  settled in #5): `frontend/dom.js` exposes the `h()` hyperscript helper and
  `frontend/components.js` (`window.UI`) the shared component factories — `card`,
  `textInput`, `select`, `button`, `chips`, `result` (green answer chip),
  `errorStrip`, `steps`, `rich` (folds the legacy `_RichText` vocabulary) — all
  styled by `components.css` strictly on the tokens (no hardcoded colors;
  `tests/test_web_components.py` lints this). `frontend/screens.js`
  (`window.Screens`) renders each view-model into a self-contained interactive node;
  `frontend/gallery.html` is the living component reference. See `frontend/README.md`.
  Run it with `python -m study_calc` (or `python -m study_calc.web`).

- **`domains/`** — declarative formula sets, one module per section: physics
  (mechanics, thermodynamics, electromagnetism, waves) plus `chemistry.py`
  (Solutions and Acids & bases — molarity, dilution, moles, pH), all using the same
  `Formula` model. `domains/__init__.py` exposes the ordered `SECTIONS` dict
  (section id → formula list, its order the nav order) and `CHEMISTRY_SECTIONS`
  (the chemistry section ids). `domains/references.py` is the **single registry of
  study links**, keyed by a formula's `key`, and is **subject-aware**: physics
  formulas map to a verified OpenStax *College Physics 2e* section (`ref.openstax`)
  plus a CollegePhysicsAnswers video chapter (`ref.cpanswers`); chemistry formulas
  (in `_CHEM_SOURCES`) carry a single OpenStax *Chemistry 2e* link (no physics
  videos). `explanation_for(key)` assembles the full `Explanation` (theory at the
  conventional `theory.<key>` i18n key + default steps + those references). To add
  references for a new formula, add one row to `_SOURCES` / `_CHEM_SOURCES` — slugs
  should be checked to resolve (HTTP 200) before commit.

### Screen rendering (`web/screens.py` + `frontend/screens.js`)

`web/screens.py` walks `navigation.SUBJECTS` and builds one view-model per item —
all pure Python, all unit-tested headlessly. A `Section` → `formula_screen`
(picker + per-variable fields + the learning blocks), a `Tool` → `cas_screen` /
`vector_screen` / `converter_screen` / `periodic_screen` (CAS yields a
SymPy-absent notice if `core.cas` can't import), a `Problems` →
`problems_screen` (a problem list plus each problem's worked solution). The
periodic screen is the chemistry tool: a clickable 118-element table (laid out by
each element's grid position, coloured by series) plus a molar-mass box and an
equation balancer, all of which render `ChemError` codes through i18n. The solve
endpoints (`solve_formula`, `cas_run`, `vector_run`, `convert_run`,
`molar_mass_run`, `balance_run`) return the same view-model shape, so the
frontend re-renders only the touched node. The learning blocks are the shared
right-hand learning vocabulary: a *static* learning area — theory, **useful
formulas**, how-to-solve, **key terms** (each a short inline blurb + an "Open full
explanation →" link that opens a concept pop-up), a **worked example**, and study
links; a topic shown on its own (the CAS screen shows it for the selected
operation *before* a result); and a *dynamic* worked solution — the CAS screen
feeds SymPy's step-by-step through it (answer lines tagged green). `frontend/
screens.js` (`window.Screens`) turns each model into a self-contained interactive
node, with `renderTerm`/`openConcept` rendering the concept pop-up (full
definition + related formulas + clickable "See also" terms). Clickable
references/terms open in a browser or a pop-up. The shell (`frontend/shell.js`)
re-renders the whole view on language or nav change, preserving the selected item.

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
`i18n.py` (the `i18n` singleton and `t()` shortcut) and the web bridge.

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
maps to its study links (two for physics, one OpenStax *Chemistry 2e* link for
chemistry). Translating the remaining `theory.*` into es/fr/uk later is purely
additive.

New machine error codes (e.g. the `chem_*` ones from `core/periodic.py`) must be
added to **all five** locales *and* to the `_ERROR_KEYS` list in
`tests/test_i18n.py`, which asserts every catalog carries every error key.

### Adding a formula

Add a `Formula` to the relevant `domains/*.py` module with one solver per
variable you want to be computable, then add its `formula.*`, `var.*`, and
`unit.*` keys to all five locale files. To give it the right-hand learning panel,
add a `theory.<key>` paragraph (at least to `en`, ideally `ru`) and one row to
`_SOURCES` in `domains/references.py` mapping it to an OpenStax section slug and a
CollegePhysicsAnswers chapter slug (verify both resolve). A **chemistry** formula
instead goes in `domains/chemistry.py` (so its section id lands in
`CHEMISTRY_SECTIONS`) with a `_CHEM_SOURCES` row pointing at a single OpenStax
*Chemistry 2e* slug. For the **rich learning material** (useful formulas, method,
key terms, worked example), add
`learning/en/topics/<key>.json` and a `learning/en/glossary/<term_id>.json` for any
term it references that doesn't exist yet (`tests/test_learning.py` requires both).
The app picks all of this up automatically — no frontend edits needed.

## AI-SDLC workflow (agent dev team)

This project is built by a coordinated team of subagents. Two Claude Code facts
shape the whole setup: **subagents start cold** (they don't share the
conversation or each other's memory, so cross-phase context travels through files
in `docs/sdlc/<ticket>/`, never through chat), and **only the main thread spawns
agents** (the `dev-manager` agent *plans* the team and dependencies; the main
session *executes* its dispatch plan — a subagent cannot dispatch another).

**Roles → agents** (all installed globally in `~/.claude/agents/`; the project
`dev-manager` agent wraps the team-planning role of `agent-organizer`):

| Function | Lead agent | Backup / review |
|----------|-----------|-----------------|
| BA / requirements | `business-analyst` | `product-manager`, `assumption-mapping` |
| Plan & dependencies | `dev-manager` (wraps `agent-organizer`) + `project-manager` / `scrum-master` | `task-distributor`, `context-manager` |
| Solution architecture / tech authority | `architect-reviewer` (owns ADRs + the technical "how"; **A** on implementation) | `dev-manager` stays process-only |
| Design — visual & system (lead) | `ui-designer` (+ Figma MCP; owns tokens, **A** on design) | `accessibility-tester` (a11y intent) |
| Design — UX research & validation | `ux-researcher` | `product-manager` |
| Design — design→code translation & handoff | `design-bridge` | `frontend-developer` |
| Core implementation | `python-pro` | `architect-reviewer` |
| Frontend implementation | `javascript-pro` / `frontend-developer` | `fullstack-developer` |
| Data / persistence (SQLite) | `sql-pro` | `database-optimizer`, `database-administrator` |
| QA strategy & quality sign-off | `qa-expert` (QA lead, owns the test gate) | — |
| Unit / integration tests | `test-automator` | `qa-expert` (A) |
| UI / functional / visual tests | `ui-ux-tester` | `qa-expert` (A) |
| Accessibility (WCAG) tests | `accessibility-tester` | `ui-ux-tester` |
| CI pipeline | `deployment-engineer` / `devops-engineer` | `build-engineer`, `git-workflow-manager` |
| Release | `deployment-engineer` + `git-workflow-manager` | `project-manager` |
| Documentation | `documentation-engineer` / `technical-writer` | `readme-generator`, `api-documenter` |
| Quality gate | `code-reviewer` | `security-auditor`, `architect-reviewer` |
| Curriculum & study content (**future**) | _deferred — interim: installed agents + main thread_ | `research-analyst`, `search-specialist`, `scientific-literature-researcher` |

The **Curriculum & study content** role is a separate *content track*, not a code
ticket: reviewing public study resources, building study plans, and authoring
problems/solutions per subject and course into `learning/`. A **dedicated
curriculum agent is deferred to future work** (a big task — draft preserved in
`ai-sdlc/future/curriculum-author.draft.md`); until it's built, content work is led
by **installed** agents (`research-analyst`, `search-specialist`,
`scientific-literature-researcher`) plus the main thread. The content track's
artifact flow + the content↔DB seed bridge still apply — see `docs/sdlc/README.md`.

There is **no separate Tech Lead / Solution Architect agent** (deliberate). The
technical authority is `architect-reviewer`: it owns the architecture, authors and
reviews **ADRs** (`docs/adr/`), guards cross-layer consistency
(`core` ↔ `web` ↔ `db` ↔ `learning`) and the i18n contract as architectural
invariants, and is **Accountable** for the technical soundness of phase
`04-implementation` — it arbitrates between the `python-pro` / `javascript-pro` /
`sql-pro` leads. Any cross-layer change, new dependency, or tech-choice goes
through it (and a new ADR) **before** implementation. `dev-manager` stays purely
process — "when and who", never "how and why".

**`dev-manager` owns the SDLC itself.** Beyond planning individual tickets, it is
solely responsible for the process working and the team functioning — detecting
gaps in any process, gate, RACI, artifact contract, or agent instruction,
escalating them to the **Dev Director (the user)** with a concrete proposed fix,
and implementing the approved change across `CLAUDE.md`, the agent files, and
`docs/sdlc/`. It proposes; the Dev Director decides; it executes — it does not
rewrite the process or an agent's charter unilaterally.

**How a ticket flows:** start by invoking the `dev-manager` agent on the ticket
folder; it first classifies the ticket by **weight** (trivial / standard / large)
and runs only the phases that weight earns, then returns the phases, the agent per
phase, and a dispatch plan. Anything touching the i18n contract or `learning/`+DB
is at least *standard*; a schema change or new section is *large*. The main
thread then invokes each specialist per that plan, each reading/writing its
artifact in `docs/sdlc/<ticket>/` (see `docs/sdlc/README.md` for the artifact
contract and `docs/sdlc/_template/` for the starting files). Phases that don't
apply are skipped *on the record* in `02-plan.md`.

**Status is derived from issue/PR state; the board is a view (D24).** A ticket's
status comes from its **issue + PR state** (+ the `docs/sdlc/<ticket>/` artifacts) —
what cold agents read — and the **GitHub Project board** just mirrors it for the Dev
Director. Stages: **Todo** (00–02) → **Implementation** (03–04 + code review on the
PR — D21/D27) → **QA** (05 tests + 07 docs by `technical-writer`, checked by
`qa-expert` — D25) → *(dev-manager merges)* → **Release** (post-merge regression +
go/no-go by dev-manager + Dev Director + devops) → **Done** (QA closes). Code review
**precedes** QA and lives inside Implementation; QA may bounce a ticket to
Implementation (direct fix) or back to **Todo** (re-plan). `status:*` labels are
**retired**; labels are `agent:*` (scope) + the standard `bug`/`enhancement` kind
labels, never status (D26). `dev-manager` owns the merge / re-plan / sign-off
transitions and **creates the decomposition sub-issues** (D30); full transition
matrix in `docs/sdlc/README.md`.

**GitHub action authority.** Who may mutate issues/PRs is governed by a RACI
(`docs/sdlc/README.md` → "GitHub actions RACI"): developers **open** PRs but
**never merge**; `code-reviewer` comments / requests-changes / approves; **only
`dev-manager` merges** (after review approval + green gates); each agent **closes its
own role/work sub-issue when delivered** (or `dev-manager` closes it if the agent has no
`gh`), while **only QA closes the parent ticket** after verifying it's done (D32); if a
PR needs extra expertise, `code-reviewer` asks `dev-manager` to delegate specialist
reviewers. The Dev Director (the user) overrides any of it.

**Gates (pragmatic):** a phase advances only when its artifact proves it — for
implementation that means `uv run --extra dev pytest` green *including* the
contract tests (`test_i18n`, `test_references`, `test_learning`, `test_problems`)
and any new formula/unit/error code present in all five locales; for review, the
`code-reviewer`'s **approval on the PR** with no open blocker (review is on the PR,
no local artifact — D21/D27). For a **`bug`** ticket, "pytest green" is *not enough*
on its own — the existing tests may encode the defect (green on broken code); the
gate also requires a **failing-first regression test** (red without the fix) and that
any assertions pinning the old behavior are inverted (EP-16). **Implementation
(`04-implementation.md`) is the python/js/db dev phase** — split by **language, not
folder** (EP-14): `python-pro` owns all **Python** — `core/`, `domains/`, and the
Python view-models under `web/` (`bridge.py`, `screens.py`, `navigation.py`);
`javascript-pro`/`frontend-developer` own `web/frontend/` (JS + CSS); `sql-pro`
owns the SQLite knowledgebase (`core/db.py`, `data/schema.sql`, ADR 0002). Design
and visual/a11y phases run only when the ticket touches the frontend.
