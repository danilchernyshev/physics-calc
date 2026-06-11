# 3. Curriculum-filter visibility semantics for `item_visible`

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** architect-reviewer (technical authority); study-calc maintainers
- **Issue:** [#178 — Shared ADR: `item_visible` keep-item / filter-contents semantics](https://github.com/danilchernyshev/study-calc/issues/178)
- **Epic:** [#102 — Curriculum filter](https://github.com/danilchernyshev/study-calc/issues/102)
- **Settles for:** [#173](https://github.com/danilchernyshev/study-calc/issues/173) (the bug, shipped now) **and** [#175](https://github.com/danilchernyshev/study-calc/issues/175) (scalar → set multi-select, rebases on this)
- **Related:** [#123](https://github.com/danilchernyshev/study-calc/issues/123) (made the filter user-reachable), #122 / #124 (shipped the backend)

## Context

The curriculum filter (epic #102) lets a student narrow the app to a single
Ontario course (`SPH4U`, `MHF4U`, `SCH4U`, …). The persisted selection lives in
`core/settings.py` as a scalar `active_course` (default `"all"`), and the web
bridge applies it when it builds the navigation tree.

Today (`study_calc/web/bridge.py`) the application is **uniform across item
kinds**:

- `item_courses(item, language)` (L42) computes the union of Ontario course codes
  an item carries — for a `Section`, the union over each formula's backing
  topic's `courses`; for a `Problems` item, the union over that subject's
  problems' `courses`. Tools and placeholders carry none.
- `item_visible(item, active_course, language)` (L80) returns
  `active_course in item_courses(...)` for any tagged item (after exempting
  `"all"`, tools, placeholders, and untagged items).
- `navigation_model` (L117) **drops** any item for which `item_visible` is false,
  and omits a subject left with no visible items.

### The bug (#173)

A `Problems` nav item is treated exactly like a tagged `Section`: when the active
course is not in the union of its problems' courses, the **entire `Problems` nav
entry disappears**. Selecting a course that Physics-Problems isn't tagged for
makes the Problems tab vanish instead of showing "no problems for this course."
That contradicts the #123 intent — *"the filter applies to the problems
displayed"* — i.e. it was meant to narrow the **list inside** the surface, not
remove the surface from navigation. The defect shipped latent in #122/#124 and
became user-reachable in #123.

`web/screens.py::problems_screen` (L804) is **not course-aware at all** today: it
calls `core/learning.py::problems_for_subject(subject, language)` (L369), which
filters by subject only. So "filter the contents" is genuinely unimplemented —
there is no path that narrows the problem list by course.

### The open design question this ADR must settle

The brief and the dev-manager plan both flag one unresolved question, deliberately
routed here as a **cross-layer semantics** call rather than a process call:

> Should the *"keep the item, filter its contents"* rule also apply to formula
> `Section` items, or **only** to `Problems`?

Because #175 turns the scalar `active_course` into a **set** of active courses
(multi-select checkboxes, default Grade = All / Course = All), the visibility
model must be designed **once** so both tickets consume the same contract. #173
ships first; #175 rebases on it.

## Decision drivers

1. **Honour the #123 intent.** The filter was specified to scope the *problems a
   student practises*, not to reshape the calculator surfaces.
2. **A coherent mental model**, without forcing two genuinely different surfaces
   to behave identically just for symmetry's sake.
3. **Minimal, justified blast radius** on a bug ticket — avoid scope-creep onto
   `formula_screen` and onto `core/learning`.
4. **Clean forward extension** from one active course (scalar) to a set (#175),
   with an unambiguous All/All default.
5. **i18n contract intact** — no display strings in the engine; any empty-state
   copy is an existing i18n *key*.

## Decision

### 1. `Problems` items — keep the item, filter its contents (the fix)

A `Problems` nav item is **always visible** when the curriculum filter is active.
`item_visible` no longer drops it. The active course is instead pushed **into**
the surface: `problems_screen` filters the problem list to those whose `courses`
match the active selection, and when none match the screen renders an explicit
**filtered-empty state** (an i18n key — see below). The `Problems` tab therefore
never disappears; it either lists the matching problems or tells the student the
current course has none.

### 2. `Section` items — unchanged (drop-on-mismatch); the keep-and-filter rule does **not** extend to them

This is the crux. `Section` items **keep their current behaviour**: a tagged
`Section` is hidden when the active course is not among its formulas' topic
courses (untagged sections, like today, always show). This ADR makes **no change
to `Section` visibility and does not touch `formula_screen`.**

The two item kinds are treated differently because they are **different kinds of
surface**, not because of inconsistency:

- A **`Problems` item is a content collection** — a list the user browses and the
  curriculum filter exists precisely to narrow. Emptying that list is a
  *meaningful, informative state* ("no problems for this course — widen the
  filter"), so the surface must stay reachable to show it. This *is* the surface
  #123 named.
- A **`Section` is a calculator** — a fixed toolset (a formula picker + solver).
  Its course tags are **incidental**: they come from the backing topic's grade
  *badge*, not from a curriculum-scoping intent. A student in any grade may
  legitimately reach for any formula (`F = ma` is not "Grade 12 content").
  Adopting symmetric keep-and-filter for sections would mean:
  - pulling the curriculum concept into `formula_screen` and **silently hiding
    individual formulas from a calculator** — surprising and arguably wrong UX;
  - **designing a formula-picker empty state that does not exist today**, on a
    bug ticket whose literal scope is the Problems tab — scope-creep the plan
    explicitly warned against.

So the unifying principle is *not* "every kind keeps its item." It is:

> **The curriculum filter narrows *content collections* (`Problems`); it does not
> reshape *tool surfaces* (`Section`, `Tool`).** `Problems` stays-and-filters;
> `Section`/`Tool`/`Placeholder` keep their existing show/hide behaviour.

Whether `Section` visibility should *also* change later — and if so, toward
**exempt-always-visible** (treat formulas as universal, like `Tool`) rather than
toward keep-and-filter — is a **separate, deliberately deferred question**. It is
a UX/curriculum-design decision, not part of fixing this bug, and is recorded as
out of scope here so it gets its own ticket and (if it changes the contract) its
own ADR.

### 3. Forward-compatibility with #175 (scalar → set)

The contract is defined so #175 is a **type widening, not a redesign**. When the
active selection becomes a set of courses:

- **Representation.** The active selection is a `frozenset[str]` of course codes,
  with **the empty set meaning "All" (no filter)**. This replaces the scalar
  `"all"` sentinel cleanly: "no courses selected" == "show everything", which is
  also the Grade = All / Course = All default. (#175 maps a chosen grade to its
  set of course codes via `CURRICULUM_GRADES`; Grade = All contributes no
  constraint.) The persisted `Settings` field migrates scalar `str` → a
  serialised set; the magic `"all"` string is retired in favour of the empty set.
- **Union semantics for items.** A tagged `Section` is visible when the active
  set is empty (All) **or** its course set **intersects** the active set
  (`item_courses(item) & active`). "Show content matching course A **or** B."
- **Union semantics for contents.** A problem is kept when the active set is empty
  **or** `set(problem.courses) & active` is non-empty. The filtered-empty state
  shows only when the active set is non-empty and the intersection is empty for
  every problem.
- **`Problems` items stay always-visible** regardless of set size — the
  keep-the-item rule is independent of scalar-vs-set; only the *narrowing* inside
  `problems_screen` reads the selection.

The scalar case (#173) is exactly this contract with a one-element (or All) set:
`active_course in courses` is the singleton form of `{active_course} & courses`.
Implementing #173 against a single course and #175 against a set therefore share
one predicate — *intersection is non-empty, or the selection is All*.

### Empty-state copy — reuse existing keys, no new key

Two existing keys already cover both states, and both are present in **all five
locales** (`en/es/fr/uk/ru` — verified):

- `problems.empty` ("No problems for this subject yet…") — the subject genuinely
  has **no problems at all**, independent of any filter.
- `ui.filter.no_results` (+ `ui.filter.no_results_detail`) — the subject **has**
  problems but **none match the active course(s)**; the detail nudges the student
  to change course or clear the filter.

Rule: `problems_screen` shows `ui.filter.no_results` when a filter is active and
the *unfiltered* subject has problems but the *filtered* list is empty; it shows
`problems.empty` when the subject has no problems regardless of filter. **No new
i18n key is introduced**, so the test-enforced i18n required-set is unaffected.
(If product later wants a single message, that is an additive copy change, not a
contract change.)

## Consequences

**Positive**

- The Problems tab can no longer vanish; the filter does what #123 specified —
  narrows the list, with an informative empty state.
- One predicate ("intersection non-empty, or All") serves both #173 (scalar) and
  #175 (set); #175 becomes a type widening with no semantic surprises.
- The bug fix stays tightly scoped: `web/` only, no `core/`/`domains`/schema/DB
  change, no `formula_screen` change, no new i18n key.
- The engine stays curriculum-agnostic: `core/learning.problems_for_subject`
  keeps filtering by subject only; the *active-selection* notion lives in the
  bridge/screens layer, consistent with `item_courses` already living there
  "rather than `navigation`… content-layer-free".

**Negative / risks**

- **An intentional asymmetry** between `Problems` (stays-and-filters) and
  `Section` (drop-on-mismatch). Mitigated by the explicit "collection vs tool"
  principle above; documented so it reads as a decision, not an oversight.
- **`Section` drop-on-mismatch is left unresolved**, not endorsed as ideal — it
  may itself deserve revisiting (toward exempt-always-visible). Carried as
  deferred follow-up, not silently accepted.
- **Tests pinning the old behaviour must be rewritten** (see implementation
  notes). For a `bug` ticket this means "pytest green" is *insufficient* as a
  gate: the assertions that encoded the defect must be inverted, with at least one
  test that fails *without* the fix.

**Neutral**

- The frontend already renders an empty-state for a zero-length problem list
  (`web/frontend/screens.js` L418, `UI.hint(L.empty)`); selecting which of the two
  keys to feed it is a Python-side decision in `problems_screen`. The frontend
  change is therefore near-zero (only if a filter-specific message is wired).

## Implementation notes (for `python-pro`, #179)

Scope for #173 is `study_calc/web/` only. Concretely:

1. **`bridge.py::item_visible`** — short-circuit `Problems` to **always visible**:
   add `if isinstance(item, navigation.Problems): return True` *before* the
   `item_courses` check. Leave the `Section` branch exactly as-is. (`item_courses`
   no longer needs a `Problems` branch for visibility, but leaving it is harmless;
   prefer removing the now-dead `Problems` case to keep intent clear.)

2. **`screens.py::problems_screen`** — add an active-course parameter and filter
   the list:
   - new signature `problems_screen(subject_id: str, active_course: str = "all")`
     (default keeps existing callers/tests working);
   - keep `problems_for_subject(subject, language)` **curriculum-agnostic**
     (subject-only) and filter its result *inside* `problems_screen`:
     keep a problem when `active_course == "all"` or `active_course in
     p.courses`. **Do not** push curriculum filtering into
     `core/learning.problems_for_subject` — the active-selection notion stays in
     the web layer (same rationale as `item_courses`);
   - choose the empty-state key per the rule above: if the filter is active and
     the *unfiltered* subject has problems but the filtered list is empty, set the
     `empty` label to `ui.filter.no_results` (+ surface `ui.filter.no_results_detail`);
     otherwise keep `problems.empty`.

3. **`bridge.py::Bridge.problems_screen`** (L274) — thread the persisted selection
   through: `return screens.problems_screen(subject_id, self._settings.active_course)`.

4. **Tests** (`tests/test_web_shell.py`) — invert the assertions that pinned the
   defect: `test_filter_sph4u_hides_other_courses` (Math/Chemistry `Problems` must
   now **stay**), `test_set_active_course_method_filters_and_persists`. Leave the
   `Section` rules (`test_item_visible_rules`, `test_item_courses_unions…`)
   **unchanged** — Section behaviour does not move. Add a test that asserts a
   `Problems` item survives a non-matching course **and** that
   `problems_screen(..., active_course=X)` narrows the list / yields the
   filtered-empty label — i.e. a test that fails *without* the fix.

### What the scalar → set extension (#175) will need later

- **`Settings`** — migrate `active_course` from a scalar `str` (with `"all"`
  sentinel) to a serialised `frozenset[str]`, **empty set == All**; add
  `set_active_courses(...)` (the grade dimension expands to a set of codes too).
  Provide a one-time read migration for the persisted scalar value.
- **`item_visible`** — replace the singleton check with
  `not active or bool(item_courses(item) & active)` for tagged `Section`s;
  `Problems` stays the unconditional `return True`; `Tool`/`Placeholder` unchanged.
- **`problems_screen`** — take `active: frozenset[str]` (default empty == All) and
  keep a problem when `not active or set(p.courses) & active`. The scalar code
  written for #173 is the singleton form of this, so the diff is mechanical.
- **No `core/`/`domains`/schema change** for either ticket — the curriculum data
  (`Problem.courses`, `Topic.courses`) and the DB are already sets of codes; only
  the *active selection* type widens, entirely within `web/` + `core/settings`.
