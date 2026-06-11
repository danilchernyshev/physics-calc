# 173 — Problems-tab filter — implementation  ·  owner: python-pro

Implements ADR 0003 §1–3.  Scope: `study_calc/web/` only — no `core/`, `domains/`,
schema, DB, or locale change.

## Core / domains (python-pro)

Not touched.  `core/learning.problems_for_subject` stays curriculum-agnostic
(subject-only filter) per ADR 0003 §2 — the active-selection concept stays in the
web layer.

## Web / frontend (python-pro — `web/*.py` are pure-Python view-models)

### `study_calc/web/bridge.py`

**`item_visible` (the primary fix):**  Added an early-return `if isinstance(item,
navigation.Problems): return True` *before* the `item_courses` check.  The `Section`
branch is left exactly as-is (ADR 0003 §2 explicitly does not extend keep-and-filter
to Sections).  The new guard is documented as forward-compatible with #175's
scalar→set widening (the unconditional `return True` for Problems items is
independent of scalar-vs-set).

**`Bridge.problems_screen`:**  Now calls
`screens.problems_screen(subject_id, self._settings.active_course)` instead of
`screens.problems_screen(subject_id)`, threading the persisted selection through
(ADR 0003 §3).

### `study_calc/web/screens.py`

**`problems_screen` signature widened:** `def problems_screen(subject_id: str, active_course: str = "all") -> dict:`.  Default `"all"` keeps all existing callers and existing tests that call it without a course argument working without change.

**Filter logic (screen layer, not core):** Fetches `all_problems` from
`problems_for_subject`, then filters in-place:
```python
if active_course == "all":
    problems = all_problems
else:
    problems = tuple(p for p in all_problems if active_course in p.courses)
```
The comment in the code notes the forward-compat form for #175:
`active_course in p.courses` is the singleton form of `bool(set(p.courses) & active)`.

**Empty-state key selection (ADR 0003 §Empty-state copy — no new i18n key):**
```python
filtered_empty = bool(active_course != "all" and all_problems and not problems)
empty_label   = t("ui.filter.no_results")       if filtered_empty else t("problems.empty")
empty_detail  = t("ui.filter.no_results_detail") if filtered_empty else ""
```
Both keys (`ui.filter.no_results`, `ui.filter.no_results_detail`) already existed in
all five locales (verified by `test_filter_keys_present_in_every_locale`).  No new
key introduced.

**New `emptyDetail` label in the returned dict:**  `labels["emptyDetail"]` is `""` when
no filter is active or the subject is genuinely empty; it is the detail nudge text
when the filter produced an empty result.  The frontend can render it as a secondary
paragraph after `L.empty` (near-zero frontend change — the field is additive).

**`count` and supporting fields** (`curriculumCode`, `courseDescriptors`,
`problemsCount`) now reflect the *filtered* list, not the full list.

### Frontend (`web/frontend/screens.js`)

Not touched in this PR.  The frontend already renders `UI.hint(L.empty)` when the
problem list is empty (L418).  Switching `L.empty` to the filter-specific message is
handled entirely in the Python model — the JS sees a different string but the same key.
The new `L.emptyDetail` field is additive; #180 (conditional) can wire it later if
product wants a second paragraph.

## Database (sql-pro)

Not touched.  No schema change; no reseed needed.

## Tests (`tests/test_web_shell.py`)

### Failing-first regression test added

**`test_problems_tab_visible_and_filtered_by_course`** — added *before* implementing
the fix.

**Before fix (current code):** FAILED at the first assertion:
```
AssertionError: #173: Problems('physics') must stay visible under SCH4U (not its course)
assert False
 +  where False = item_visible(Problems(subject_id='physics'), 'SCH4U')
```
The second assertion would also have failed with `TypeError` because
`screens.problems_screen` had no `active_course` parameter.

**After fix:** PASSES.  Covers:
- `item_visible(Problems("physics"), "SCH4U")` → True
- `item_visible(Problems("math"), "SPH4U")` → True
- `problems_screen("physics", active_course="SCH4U")` returns `problems == []`
- `labels["empty"] == t("ui.filter.no_results")` in filtered-empty state
- `labels["emptyDetail"] == t("ui.filter.no_results_detail")` in filtered-empty state
- `problems_screen("physics", active_course="SPH4U")` returns non-empty list
- `labels["emptyDetail"] == ""` when no filter active
- `Bridge.problems_screen("physics")` under SCH4U returns filtered-empty model

### Existing tests inverted (were pinning the #173 defect)

Four tests had assertions that encoded the bug.  All updated with `# BUG #173 FIX:`
comments explaining the old (wrong) value and the corrected expectation:

| Test | Old (buggy) assertion | New (correct) assertion |
|------|-----------------------|-------------------------|
| `test_filter_sph4u_hides_other_courses` | `math` items = `["tool:cas", "tool:vectors"]` | `["tool:cas", "tool:vectors", "problems:math"]` |
| `test_filter_sph4u_hides_other_courses` | `chemistry` items = `["tool:periodic_table"]` | `["tool:periodic_table", "problems:chemistry"]` |
| `test_filter_sch4u_keeps_untagged_and_chemistry` | `physics` items = `["section:thermodynamics"]` | `["section:thermodynamics", "problems:physics"]` |
| `test_navigation_model_drops_subjects_left_empty` | physics items = `["section:thermodynamics"]` | `["section:thermodynamics", "problems:physics"]` |
| `test_set_active_course_method_filters_and_persists` | `chemistry` under SPH4U = `["tool:periodic_table"]` | `["tool:periodic_table", "problems:chemistry"]` |
| `test_filter_is_stable_across_language_change` | `math` under SPH4U = `["tool:cas", "tool:vectors"]` | `["tool:cas", "tool:vectors", "problems:math"]` |

Tests left **unchanged** (Section behaviour does not move, per ADR 0003 §2):
- `test_item_visible_rules` — Section drop-on-mismatch assertions are correct
- `test_item_courses_unions_topic_and_problem_tags` — item_courses still correct
- `test_filter_all_is_the_full_tree` — no filter → full tree (unchanged)

## Key decisions / trade-offs

- **Only `Problems` items made always-visible** — Sections keep drop-on-mismatch.
  This is the ADR 0003 §2 ruling: "collection vs tool" principle; not inconsistency.
- **No new i18n key** — reused `ui.filter.no_results` + `_detail`; already in all
  five locales.  `test_enforced` required-set is unaffected.
- **`problems_for_subject` untouched** — the active-selection concept stays in the
  web layer, consistent with `item_courses` already living there.
- **`emptyDetail` is additive** — `""` when inactive, never breaks existing callers
  that ignore the field.

## Gate

- [x] `uv run --extra dev pytest` green: **480 passed, 1 skipped** (the skip is
  unrelated — a SymPy-absent CAS test, pre-existing).
- [x] Contract tests green: `test_i18n` · `test_references` · `test_learning` · `test_problems`
- [x] Regression test `test_problems_tab_visible_and_filtered_by_course` fails on
  pre-fix code, passes after fix (confirmed above).
- [x] Inverted tests carry `# BUG #173 FIX:` comment citing the old value.
- [x] No new locale key (no `test_i18n` impact).
- [x] No `core/` / `domains/` / schema / DB change.
