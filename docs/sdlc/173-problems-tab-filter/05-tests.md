# 173 — Problems-tab filter — tests  ·  QA lead: qa-expert  ·  Refs #181

Pre-merge QA pass on branch `fix/173-problems-tab-filter` (PR #183).  Code-reviewer
approval already posted (✅ APPROVE, no blockers — see PR #183 comment thread).

---

## QA plan & strategy  (qa-expert — A/R)

**Risk areas requiring coverage:**

- `item_visible` semantics: Problems item must stay visible for *every* active
  course, including courses none of its problems are tagged for.
- Contents filter: `problems_screen(subject_id, active_course)` must narrow the
  problem list; the filtered-empty path must use `ui.filter.no_results`, not
  `problems.empty`.
- Persisted selection thread-through: `Bridge.problems_screen` must read
  `self._settings.active_course` and pass it to `screens.problems_screen`.
- Inverted assertions: the six assertions that encoded the bug must now assert the
  correct (fixed) behavior, each annotated `# BUG #173 FIX:` with the old value.
- Section rules unchanged: `test_item_visible_rules` and
  `test_item_courses_unions_topic_and_problem_tags` must remain unmodified (ADR
  0003 §2 explicitly does not extend keep-and-filter to `Section`s).
- i18n contract intact: no new locale key; all five locales carry both reused
  empty-state keys (`ui.filter.no_results`, `ui.filter.no_results_detail`).
- Forward-compatibility note in code: the `active_course in p.courses` predicate
  is the singleton form of the #175 set-intersection contract; no structural change
  needed when #175 widens to `frozenset`.

**Out of scope for this test pass:**

- `emptyDetail` secondary-paragraph rendering — open #180 (`frontend-developer`).
  The model emits the field correctly; wiring `L.emptyDetail` in `screens.js::
  problems()` is #180's work.  The missing rendering is **not a defect in this PR**;
  the primary `L.empty` already switches to `ui.filter.no_results`.
- `Section` keep-and-filter behavior — deliberately deferred to a future ticket
  per ADR 0003 §2.
- #175 scalar-to-set widening — out of scope; this ticket is the scalar fix only.
- Post-merge regression suite — epic-level release gate for 0.8.2.

**Which executions apply:**

- [x] unit / integration — `uv run --extra dev pytest` (primary gate)
- [x] reasoning-based failing-first verification (no throwaway worktree needed —
      see below)
- [ ] UI / E2E — pywebview cannot be driven headlessly; see Human-verification
      section
- [ ] visual — no CSS changed in this PR
- [ ] accessibility — no HTML / ARIA changed in this PR

---

## Unit / integration  (qa-expert executing — test-automator not separately spawned, D20 standard)

### Full suite run

```
uv run --extra dev pytest
480 passed, 1 skipped in 2.95s
```

The 1 skipped test is the pre-existing SymPy-absent CAS test, unrelated to this PR.
All 480 other tests pass.  All 32 tests in `tests/test_web_shell.py` pass.

### Contract tests (individually confirmed)

```
uv run --extra dev pytest tests/test_i18n.py tests/test_references.py \
    tests/test_learning.py tests/test_problems.py
69 passed in 0.77s
```

- `test_i18n` — no new locale key introduced; required-set unaffected.  All five
  locales carry both reused empty-state keys (`test_filter_keys_present_in_every_locale`
  parametrized over en/es/fr/ru/uk — all green).
- `test_references` — no formula/reference change.
- `test_learning` — no `learning/` content change.
- `test_problems` — no problem-data change; `problems_for_subject` stays
  curriculum-agnostic (subject-only filter).

### Regression test

```
uv run --extra dev pytest \
    tests/test_web_shell.py::test_problems_tab_visible_and_filtered_by_course
1 passed in 0.17s
```

---

## Failing-first verification

**Method: reasoned inspection** of `origin/master` (the pre-fix commit).  No throwaway
worktree was needed — the pre-fix and post-fix code are both directly readable, and the
code-reviewer independently verified the same failure empirically.

**Pre-fix state on `origin/master`:**

`study_calc/web/bridge.py` L80–95 — `item_visible` had no
`isinstance(item, navigation.Problems)` branch.  A `Problems` item fell through to
`item_courses(item)` = `frozenset({"SPH4U"})` for physics, then the final line returned
`active_course in courses` = `"SCH4U" in frozenset({"SPH4U"})` = `False`.

`study_calc/web/screens.py` L804 — `def problems_screen(subject_id: str)`: no
`active_course` parameter at all.

**Consequence for `test_problems_tab_visible_and_filtered_by_course`:**

First assertion:
```python
assert item_visible(navigation.Problems("physics"), "SCH4U")
```
Returns `False` on pre-fix code.  FAILS with:
```
AssertionError: #173: Problems('physics') must stay visible under SCH4U (not its course)
assert False
 +  where False = item_visible(Problems(subject_id='physics'), 'SCH4U')
```
(Matches exactly the failure message quoted in `04-implementation.md`.)

Second block (would be reached only if assertion 1 somehow passed):
```python
screens.problems_screen("physics", active_course="SCH4U")
```
Raises `TypeError: problems_screen() got an unexpected keyword argument 'active_course'`.

**Conclusion:** The regression test is a genuine failing-first test — it fails on the
bug, passes on the fix.  It is not made-to-pass.  Confirmed independently by code-reviewer:
"Verified the failing-first premise empirically (physics problems carry only `SPH4U`, so
old `item_visible(Problems('physics'), 'SCH4U')` returned `False`)."

---

## Coverage & correctness assessment

### Inverted assertions — do they reflect ADR 0003?

Six assertions across four tests were updated with `# BUG #173 FIX:` comments:

| Test | Inverted assertion | ADR basis |
|------|--------------------|-----------|
| `test_filter_sph4u_hides_other_courses` | `problems:math` stays in math items | ADR §1 |
| `test_filter_sph4u_hides_other_courses` | `problems:chemistry` stays in chemistry items | ADR §1 |
| `test_filter_sch4u_keeps_untagged_and_chemistry` | `problems:physics` stays in physics items under SCH4U | ADR §1 |
| `test_navigation_model_drops_subjects_left_empty` | `problems:physics` stays under synthetic ZZZ9U | ADR §1 |
| `test_set_active_course_method_filters_and_persists` | `problems:chemistry` stays in chemistry under SPH4U | ADR §1 |
| `test_filter_is_stable_across_language_change` | `problems:math` stays in math under SPH4U in both languages | ADR §1 |

All six inversions are **correct** — each adds exactly the `problems:*` item the ADR
mandates for its subject.  They are not made-to-pass: the old values would pass on
pre-fix code and would *fail* on fixed code; the new values reflect the intended behavior.

### Unchanged tests — Section rules intact (ADR §2)

- `test_item_visible_rules` — unchanged.  Still asserts `not item_visible(Section("mechanics"), "SCH4U")` (Section drop-on-mismatch preserved).
- `test_item_courses_unions_topic_and_problem_tags` — unchanged.  `item_courses` contract unmodified.
- `test_filter_all_is_the_full_tree` — unchanged.  "All" baseline unaffected.

This correctly implements ADR 0003 §2: the keep-and-filter rule does **not** extend to
`Section` items.

### Untested edges / gaps

The following edges are **not blocked** but are noted for tracking:

1. **Empty subject + active filter**: `problems_screen("subject_with_no_problems", active_course="SPH4U")`.
   The `filtered_empty` predicate correctly returns `False` (because `all_problems` is empty,
   so `bool(active_course != "all" and all_problems and not problems)` = False) → empty label
   stays `problems.empty`.  Logic is correct, but this path has no explicit test.  Risk: low
   (the branching is unambiguous); worth a one-line assertion in a follow-up test pass.

2. **Representative chip off filtered set**: `curriculumCode` in the returned model is now
   computed off the *filtered* problem list, not the full list.  No assertion verifies that
   the chip value changes between filtered and unfiltered.  The code-reviewer noted this as
   "correct UX"; it is untested.  Risk: low; can be added as a regression note for #175.

3. **Non-Physics subject filter in `problems_screen`**: The regression test uses only
   `problems_screen("physics", ...)`.  Math (`MDM4U`/`MHF4U`) and Chemistry (`SCH4U`)
   subjects are exercised at the navigation-model level (item stays visible) but not at the
   `problems_screen` filter level.  The filtering logic is subject-agnostic, so risk is low;
   a future multi-subject parametrized test would close this gap completely.

None of these gaps are blockers.  They are logged here for the follow-up test maintenance
cycle.

---

## Docs check (D25)

`07-docs.md` verdict: **no user-facing documentation change needed.**

Assessment: correct.

- `README.md` — the filter behavior was never documented as a user-facing feature spec;
  a bug fix that brings the code into line with stated intent (`#123`: "the filter applies
  to the problems displayed") does not warrant a user-doc entry.  Verified: no README change
  in the diff.
- i18n / locale files — no new key.  Both empty-state keys (`ui.filter.no_results`,
  `ui.filter.no_results_detail`) already present in all five locales; confirmed by
  `test_filter_keys_present_in_every_locale` (parametrized, green).
- ADR 0003 — checked in at `docs/adr/0003-curriculum-filter-visibility.md`.  Complete:
  covers the problem, the "collection vs tool" decision principle, forward-compat with #175,
  empty-state copy rule, and the deliberately-deferred Section question.
- CHANGELOG — no `CHANGELOG.md` exists in the repo (confirmed; recent `1c0f0ce` used
  README + AppStream, not a separate changelog).  Commit message `fix(#173): Problems tab
  stays visible; curriculum filter narrows its contents` is sufficient for GitHub
  auto-generated release notes.
- `07-docs.md` QA checklist — all items ticked, each verified against the diff and the
  live locale files.

One minor note: the `07-docs.md` says `#180` (`emptyDetail` rendering) "may fold into
#179" — it did not fold; #180 remains open.  This is not a docs gap; the note in the file
is a plan-time possibility that resolved to "stay open," which is the correct outcome
per the ADR's "additive frontend change" framing.

---

## Headless gap — human-verification required (EP-12 operational rule)

**Why this gap exists:** The original bug (#173) was found in a live pywebview run.
The Python test suite exercises view-models as pure Python data structures — it cannot
drive the actual desktop window, its JS shell, or the GTK/WebKit2 rendering layer.
The following behaviors are therefore **not covered by the automated suite** and require
a human operator to verify in the live app:

- The Problems tab is actually visible in the rendered navigation (not just in the
  view-model dict) when a non-matching course is selected.
- The JS shell re-renders the nav tree and the problem list when `set_active_course`
  is called from the Settings overlay.
- The empty-state hint (`UI.hint(L.empty)`) renders with the filter-specific message
  when the filtered list is empty.
- The `emptyDetail` secondary paragraph does NOT show yet (pending #180) — this is
  expected, not a regression.

**Human-verification checklist (dev-manager to file as D23 sub-issue of #173):**

```
Launch: uv run python -m study_calc
Requires: graphical session (X11 or Wayland); WebKit2GTK on Linux.

[ ] 1. App opens; shell header shows the grade/course filter controls.
[ ] 2. Open Settings overlay (gear icon / Settings button).
        Set Grade = "12", Course = "SCH4U". Close overlay.
[ ] 3. Navigate to "Physics" subject in the left sidebar.
        EXPECTED: "Problems" tab IS visible in the nav items list.
        WAS (bug): Problems tab vanished entirely.
[ ] 4. Click the Problems tab.
        EXPECTED: empty state shows — message reads "No content matches the
        current filter" (ui.filter.no_results).
        NOTE: secondary detail paragraph (ui.filter.no_results_detail) will NOT
        render yet — open #180 (emptyDetail wiring). Primary message is sufficient.
[ ] 5. Open Settings; set Course = "SPH4U". Close.
        EXPECTED: Physics Problems tab still visible; list now shows SPH4U problems
        (non-empty). Confirm at least one problem card appears.
[ ] 6. Navigate to "Math" subject.
        EXPECTED: "Problems" tab visible under SPH4U filter (MDM4U/MHF4U content
        does not match; list is empty with filter-specific message).
[ ] 7. Navigate to "Chemistry" subject.
        EXPECTED: "Problems" tab visible under SPH4U filter.
[ ] 8. Open Settings; set Grade = "All", Course = "All". Close.
        EXPECTED: all subjects restore fully; Problems tabs in all subjects show
        their complete problem lists.
[ ] 9. Repeat steps 2-5 with Course = "MDM4U".
        EXPECTED: Math Problems tab shows MDM4U-tagged problems (non-empty); Physics
        Problems shows filter-specific empty state.
```

**Note on #180:** `emptyDetail` rendering (the secondary nudge paragraph) is the open
`bug` sub-issue #180 assigned to `frontend-developer`.  Its absence in the live app is
expected and is NOT a regression introduced by this PR.  The human-verification checklist
does not require it to be present to pass.

**Per D23/D30 governance:** QA flags this headless gap here; dev-manager creates the
human-verification sub-issue linked to #173.  QA does not create the issue directly.

---

## Functional / visual / accessibility

**Frontend not touched in this PR.** No HTML, CSS, JS, or ARIA changed.  The JS layer
sees only a different string value in `L.empty` and a new `L.emptyDetail` field
(currently ignored by `screens.js`).  Functional/visual/a11y execution passes are not
applicable.

- [ ] UI/functional — not applicable (no frontend change in this PR)
- [ ] visual — not applicable (no CSS/layout change)
- [ ] accessibility — not applicable (no HTML/ARIA change)

---

## Defect triage  (qa-expert — A/R)

| Defect | Severity | Owner | Status |
|--------|----------|-------|--------|
| `emptyDetail` not rendered in `screens.js::problems()` | minor / fast-follow | #180 (`frontend-developer`) | Open — pre-existing before this PR; primary message renders correctly |
| None else | — | — | — |

No new defects introduced by this PR.  The `emptyDetail` rendering gap is a **known
open item tracked in #180**, not a defect introduced here.

---

## Quality sign-off  (qa-expert — A/R)  ← test gate

- [x] Full suite green: **480 passed, 1 skipped** (pre-existing skip, unrelated)
- [x] Contract tests green: `test_i18n` · `test_references` · `test_learning` · `test_problems`
- [x] Regression test `test_problems_tab_visible_and_filtered_by_course` passes on branch
- [x] Regression test is genuine failing-first (verified by inspection + code-reviewer empirical check)
- [x] Inverted assertions are correct (reflect ADR 0003 §1), not made-to-pass
- [x] Section-rule tests unchanged (ADR 0003 §2 honored)
- [x] No new i18n key; both reused keys present in all five locales
- [x] `07-docs.md` verdict correct — no user-facing doc change needed; ADR complete
- [x] `emptyDetail` rendering gap noted; open #180 is the correct and sufficient home
- [x] Human-verification checklist documented; dev-manager to file D23 sub-issue

**Verdict: PASS — merge-ready (pending human-verification as a tracked follow-up, not a blocker).**

The fix is correctly scoped, the regression is genuine, the inverted assertions are right,
the ADR is honored, the i18n contract is intact, and the docs assessment is sound.  The
only live-window behavior that cannot be confirmed headlessly is documented above as a
human-verification checklist for dev-manager to file.  The `emptyDetail` rendering gap is
an open fast-follow (#180), not a defect in this PR.

Combined with the code-reviewer's ✅ APPROVE (no blockers), this QA sign-off clears the
gate for dev-manager to merge PR #183.

