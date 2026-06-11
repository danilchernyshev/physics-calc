# 123 — tests  ·  QA lead: qa-expert  ·  2026-06-11

## QA cell (lightened — standard-weight ticket)

Standard-weight tickets in the SDLC earn a lightened QA cell: QA lead (plan +
sign-off) plus ONE combined executor pass. Per the Dev Director's ruling the
executor pass was a **live human UX run** on the real desktop app (display :0),
replacing the separate test-automator / ui-ux-tester / accessibility-tester
executor roles. The automated regression suite is run by QA lead independently
to confirm the test-gate assertion.

Rationale for lightening: the ticket is frontend-only (four JS/CSS files, no
Python contract change); the backend model and bridge methods (`curriculum_filter_model`,
`set_active_grade`, `set_active_course`, `item_visible`) were already merged and
tested in #122/#124. The risk surface for this ticket is the frontend wiring
plus the overlay-interaction fix — well-bounded and confirmed by human observation
of the live desktop window.

---

## Scope

### In scope
- Grade and Course `<select>` controls in the shell header (every screen).
- Settings overlay filter section (`openUpdates`).
- `render({ keepOverlays })` fix — overlay survives grade/course changes.
- `UI.field` a11y fix — `id`/`for` association on all `UI.select` / `UI.textInput` fields.
- In-flight sequence guards (`_gradeSeq`/`_courseSeq`).
- No-results empty state and selection clamping.
- CSS (token-only, no hardcoded colors).

### Explicitly out of scope for this test pass
- Backend bridge/model (already merged, covered by prior test cycle).
- `screens.py` / `bridge.py` — unchanged by this PR.
- Defects #172–#176 (externalized, tracked separately).
- Grade string-sort for grades 9/10 (model file untouched, acknowledged follow-up).

---

## Test-gate run (qa-expert, self-executed)

Command: `uv run --extra dev pytest -q`
Working directory: `/home/danil/dev/study-calc`
Result: **479 passed, 1 skipped** in 2.85 s

Contract tests specifically confirmed green:
- `test_i18n` — all five locales complete including `ui.filter.*` keys.
- `test_references` — reference registry intact.
- `test_learning` — all topic/concept/problem files resolve.
- `test_problems` — problem set coherent.
- `test_web_components.py::test_frontend_css_has_no_hardcoded_hex_colors` — no hex literals in CSS.
- `test_web_screens.py::test_screens_css_uses_only_tokens` — CSS declarations token-only.
- `test_web_shell.py` — curriculum-filter model tests (grade/course/gradeMap/labels).

This matches the developer's reported gate result and the code-reviewer's independent
gate run — three independent confirmations of the same count.

---

## Live UX gate (human executor pass — verified observations)

Run on the real desktop application (PyWebView + GTK, display :0).

| Check | Result |
|-------|--------|
| Grade + Course dropdowns present in the shell header on every screen | PASS |
| Selecting a grade populates the course dropdown | PASS |
| Selecting a course filters the nav/cards accordingly | PASS |
| Settings overlay remains OPEN while changing grade/course inside it (`keepOverlays` fix) | PASS |
| Course list and header controls update in-place when changed from the overlay | PASS |
| "Clear filter" button resets both selects to All | PASS |

---

## Code-review gate

First review: changes-requested (one major — overlay closed on grade/course change).
Review-fix commit `27165eb`: addressed all findings (major resolved, three minors resolved).
Re-review (PR #177): **APPROVE** — no open blocker or major, gate green (479/1), no
new defect introduced, delta correctness verified (no listener leak, no double-render,
a11y fix sound, in-flight guards correct).

---

## Defect triage

| Defect | Severity | Finding | Dev Director ruling | QA disposition |
|--------|----------|---------|-------------------|----------------|
| #172 | Minor | Dropdowns lack a selectable affordance (visual/design) | Non-blocking | Externalized |
| #173 | Major | Selecting a course hides the entire Problems tab — root cause in already-merged `bridge.py::item_visible`; NOT introduced by PR #177 | Non-blocking for #123 | Externalized |
| #174 | Minor | Course list not subject-scoped; grade=All locks course select; sparse course coverage | Non-blocking | Externalized |
| #175 | Minor | Settings filter: default All/All + multi-select checkboxes (enhancement) | Non-blocking | Externalized |
| #176 | Minor | Test isolation: bare `Bridge()` reads real `~/.config`; already mitigated (tests green) | Non-blocking | Externalized |

No defect introduced by PR #177 itself. The code reviewer confirmed #173's root cause
is pre-existing in the already-merged `bridge.py::item_visible` (which this PR does not
touch).

---

## Residual risk statement

**#173 is the one risk I name explicitly.**

When a user selects any course value (i.e., not "All"), `item_visible` in the
already-merged bridge code hides the Problems tab entirely rather than filtering its
list. This is user-visible: anyone who uses the curriculum filter and then clicks on
Problems will find the tab gone from the nav. The root cause is upstream of this PR
and was present before this branch was opened.

The Dev Director's ruling that it does not block #123 is technically well-founded:
the defect is reproducible on master without this PR's changes (the filter itself is
what surfaces it, and the filter model was merged earlier). However, this PR makes
the filter interactive for the first time, so from the user's perspective #173 becomes
reachable immediately upon merging #177. It is not a blocker on a technicality — it
is a behavior defect that will land in production with this merge.

My QA assessment: the ruling is correct that #123's OWN scope is sound and complete.
I sign off on that scope. I note the residual risk clearly so the Dev Director
and dev-manager can assess urgency of #173 relative to release timing. If there is
any expectation that users will encounter the curriculum filter before #173 is
resolved, I recommend scheduling #173 as the first fix after merge. The epic (#102)
staying open is the right accountability channel.

The two non-blocking nits from the re-review (focus drop on the just-operated select;
independent grade/course in-flight sequences) are low-severity UX rough edges, not
defects; they do not affect correctness.

---

## Quality sign-off

Test gate: **PASS**

- Automated regression suite: 479 passed, 1 skipped — GREEN (confirmed independently).
- Contract tests (test_i18n / test_references / test_learning / test_problems): GREEN.
- Token-lint (no hardcoded hex colors, CSS declarations token-only): GREEN.
- Code review: APPROVE, no open blocker or major.
- Live UX gate: all core user flows confirmed on real desktop.
- PR #177 scope: frontend wiring complete and correct; no Python contract change;
  no new defect introduced.
- All live-gate defects (#172–#176) correctly externalized; none introduced by this PR;
  Dev Director ruling accepted.

**Condition attached:** #173 (course selection hides Problems tab) must be resolved
and verified before epic #102 is closed. This sign-off covers ticket #123 / PR #177
only — it does not constitute a release sign-off for the full curriculum-filter epic.

Merge authority: dev-manager (per GitHub-actions RACI).
Epic closure authority: QA, after post-merge validation that #173 is resolved.
