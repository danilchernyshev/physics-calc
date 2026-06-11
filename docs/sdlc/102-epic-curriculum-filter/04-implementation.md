# 123 — implementation  ·  owner: javascript-pro

One artifact, one section per layer touched.

## Core / domains (python-pro)

Not touched. All persistence and bridge logic was already merged in #124/#125/#126.
No `core/` or `domains/` change.

## Web / frontend (javascript-pro)

### Files changed

| File | Change |
|------|--------|
| `study_calc/web/frontend/shell.js` | Header filter controls + no-results state + selection clamping |
| `study_calc/web/frontend/screens.js` | Settings overlay filter section in `openUpdates` |
| `study_calc/web/frontend/shell.css` | `.header__filter-row`, `.filter__clear`, `.filter-empty` |
| `study_calc/web/frontend/screens.css` | `.updates__filter-section`, `.updates__filter-controls` |

### What changed

**`shell.js`**

1. Two async helpers (`setActiveGrade`, `setActiveCourse`) encapsulate the
   two-method API calls. Each calls the real bridge method (`set_active_grade` /
   `set_active_course`), stores the returned fresh state into `state.data`, and
   calls `render()`. This is the authoritative path for grade/course changes from
   both the header and the overlay.

2. `updatesApi` extended with `setGrade` and `setCourse` methods. These call the
   same bridge methods and return `newState.filter` (the fresh filter descriptor)
   so the Settings overlay can update its course list in-place without closing.

3. `renderFilterControls(data)` builds the inline grade + course selects using
   `UI.select` from `components.js`. Grade options come from `data.filter.grades`
   (model-provided, never hardcoded); course options are derived from
   `data.filter.gradeMap[activeGrade]` (empty if grade is "all"). The "Clear
   filter" button calls `setActiveGrade('all')` and is only rendered when
   `activeGrade !== 'all'`. All label strings come from `data.filter.labels.*`.

4. `renderNoResults(data)` renders the no-results empty state (filter controls +
   a message) when the filtered subject list is empty.

5. `renderContent` now includes `renderFilterControls(data)` between the title row
   and the subject subtitle, so the selects appear on every screen.

6. `render()` guards the empty-subjects case (calls `renderNoResults`) and clamps
   `state.subject` / `state.item` to valid indices after a filter change may have
   shortened the lists.

**`screens.js` — `openUpdates`**

Added a `filterSection` container and a `fillFilterArea(fm)` closure (defined
inside `openUpdates` so it closes over `api`). On initial render it populates the
section with a heading (`labels.settingsHeading`), a hint (`labels.settingsHint`),
and the two `UI.select` controls. When grade changes in the overlay, `api.setGrade`
is awaited; the returned fresh filter descriptor is passed back to `fillFilterArea`
to update the course options in-place (like `fillStatus` updates the status region).
`api.setCourse` follows the same pattern. Both guard on the method's presence so the
static browser preview (`__STUDY_CALC_API__` stubs) degrades gracefully.
The `filterSection` div is the last entry in `bodyNodes`.

**`shell.css`**

- `.header__filter-row`: flex row (`align-items: flex-end`, `flex-wrap: wrap`,
  `gap: var(--space-sm)`) with a small bottom margin.
- `.header__filter-row .field`: `flex: 0 1 160px; min-width: 110px` so the two
  selects sit compactly side-by-side and wrap on narrow viewports.
- `.filter__clear`: link-style button (`color: var(--color-accent-link)`, no
  background), `:hover` adds underline, `:focus-visible` ring uses
  `var(--color-brand-primary)`.
- `.filter-empty` / `.filter-empty__title` / `.filter-empty__detail`: same surface
  pattern as `.placeholder` — card with border, title in `--color-text-strong`,
  detail in `--color-text-muted`.

**`screens.css`**

- `.updates__filter-section`: top border + padding separator at the foot of the
  updates dialog; `:empty` hides it when the filter model is absent (static preview).
- `.updates__filter-heading`: semibold heading using base font size.
- `.updates__filter-controls`: flex row matching the header filter layout.
- `.updates__filter-controls .field`: same compact sizing as the header.

No hardcoded colors anywhere — every value is a `var(--*)` token.
`tests/test_web_components.py::test_frontend_css_has_no_hardcoded_hex_colors`
passes. Issue references in CSS comments use `epic 102` form (not `#102` or `#123`)
to avoid the `#NN` hex-literal false positive the regex lints against.

### Two-method API wiring

The spec reconciliation in `02-plan.md` (EP-3) is fully applied:

- Grade `onchange` → `set_active_grade(value)` → bridge returns full refreshed
  `get_state()` → `state.data = newState` → `render()`. The bridge's
  `Settings.set_active_grade` resets the active course to "all" as a side-effect
  (proven by `test_changing_grade_resets_course`). The frontend re-render then
  reflects the reset course in both the header and, if the overlay is open, the
  overlay's course select.
- Course `onchange` → `set_active_course(value)` → same re-render path.
- "Clear" affordance → `set_active_grade("all")` (same path, grade resets course).
- The non-existent `set_curriculum_filter` from the original issue body is NOT
  called; this reconciliation is recorded here for the PR description.

### Model gap noted

No fields were missing from the Python model (`curriculum_filter_model` supplies
`grades`, `gradeMap`, `activeGrade`, `activeCourse`, `labels.*` — everything the
frontend needs). `screens.py` was not changed.

One cosmetic observation: `grades` is sorted by Python's default string sort
(`["all", "11", "12"]` for the current `CURRICULUM_GRADES`). This is correct for
the existing data (only grades 11 and 12 are registered), but would produce
`["10", "11", "12", "9"]` if grade 9 or 10 courses were added. The JS consumer
renders in model order; a future-proof numeric sort in `curriculum_filter_model`
is recommended but out of scope for this ticket.

### Key decisions

- **In-place overlay update**: rather than closing and re-opening the Settings
  overlay on grade change, `fillFilterArea` updates `filterSection` in-place (like
  `fillStatus` for the update result). This preserves scroll position and focus.
- **Selection clamping**: `render()` now clamps `state.subject`/`state.item`
  indices before using them. This prevents a potential out-of-bounds crash when a
  filter change removes the previously selected subject entirely.
- **`filter__clear` always uses `set_active_grade('all')`**: grade reset also
  resets course (bridge side-effect), so one click restores the "all" state
  without a second bridge call.
- **No `screens.py` change**: all required fields were already present.

## Review fixes (javascript-pro, post-review commit)

Addressed all findings from `06-review.md`.

### Fix 1 — Major: overlay grade/course change closed the Settings overlay

Root cause: `updatesApi.setGrade/setCourse` called the shell-wide `render()`, which
unconditionally called `Screens.closeOverlays()`. That removed every `.modal` node
from `document.body`, including the live `.modal--updates` overlay. The subsequent
`fillFilterArea(nf)` then mutated a detached `filterSection` node, so the course
list never updated and focus dropped to `document.body`.

Fix applied in `shell.js`:

- `render()` now accepts `{ keepOverlays = false } = {}`. When `keepOverlays` is
  true, `Screens.closeOverlays()` is skipped. The overlay is attached to
  `document.body` outside `#app`; the `app.replaceChildren()` call inside `render()`
  does not touch it, so only the `closeOverlays()` step would have removed it.
- `setActiveGrade` / `setActiveCourse` now call `render({ keepOverlays: true })`.
  With the overlay intact and `filterSection` still in the DOM, `fillFilterArea(nf)`
  runs on the live node and updates the course `<select>` in-place as designed.
  The nav and header filter controls inside `#app` are rebuilt correctly.

### Fix 2 — Minor a11y: label not programmatically associated

`UI.field` in `components.js` rendered `<label>` with no `for` and the control had
no `id`, so assistive tech could not announce the label for the grade/course selects.

Fix: added a module-level `_fieldIdSeq` counter. `UI.field(label, control, id=null)`
now generates `field-N` ids when no explicit id is passed, sets `control.id = lid`,
and sets `for: lid` on the `<label>`. All existing callers (`UI.textInput`,
`UI.select`, any screen that calls `UI.field` directly) benefit automatically since
the third parameter defaults to `null`. The `id` parameter exists for callers like
the auto-check checkbox that already manage their own id.

### Fix 3 — Minor: in-flight guard for rapid grade/course changes

Added `_gradeSeq` / `_courseSeq` module-level counters in `shell.js`. Each call to
`setActiveGrade` / `setActiveCourse` increments its counter and captures the value;
after the `await`, if the counter has advanced (a newer call was issued), the
response is discarded and `null` is returned. The overlay's existing `if (nf)`
guard means a discarded response leaves the filter area unchanged, and the winning
call (highest seq) performs the full update.

### Fix 4 — Optional: header vs overlay helper consolidation

`updatesApi.setGrade/setCourse` previously duplicated `setActiveGrade/setActiveCourse`
with only a cosmetic difference (returning `newState.filter`). After fixes 1–3 they
are identical. `updatesApi.setGrade/setCourse` now simply delegate to the shared
helpers: `setGrade: (grade) => setActiveGrade(grade)`.

### Gate (post-review)

`uv run --extra dev pytest -q` → **479 passed, 1 skipped** (unchanged pass count).

## Database (sql-pro)

Not touched. No schema change, no learning-JSON change, no DB reseed.

## Gate

- [x] `uv run --extra dev pytest` green — 479 passed, 1 skipped
- [x] `tests/test_web_components.py::test_frontend_css_has_no_hardcoded_hex_colors` green
- [x] `tests/test_web_screens.py::test_screens_css_uses_only_tokens` green
- [x] `tests/test_web_shell.py` green (all curriculum-filter model tests pass)
- [x] Header selects wired to `set_active_grade` / `set_active_course`
- [x] Settings overlay mirrors the same selects from `model.filter`
- [x] No hardcoded colors in any hand-written CSS
- [x] `screens.py` not changed
