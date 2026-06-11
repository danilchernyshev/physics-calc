# 123 — review  ·  owner: code-reviewer (+ architect-reviewer, security-auditor)

Scope: frontend implementation of #123 (curriculum-filter controls) on
`feat/123-filter-controls`, diff vs `master`. Changed files:
`web/frontend/shell.js`, `web/frontend/screens.js`, `web/frontend/shell.css`,
`web/frontend/screens.css`, artifact `04-implementation.md`.

Gate run by reviewer: `uv run --extra dev pytest -q` → **479 passed, 1 skipped**
(matches the developer's report). `ui.filter.*` keys present in all five locales.
Token-lint tests (`test_web_components.py`, screens-css token test) green in the run.
No Python contract file changed (`screens.py`/`bridge.py` untouched) — contract preserved.

## Findings
| Severity | File:line | Finding | Resolved? |
|----------|-----------|---------|-----------|
| blocker  | — | None. | — |
| major    | `shell.js:33-42` + `screens.js:1156-1163` | **Changing grade/course from the Settings overlay closes the overlay.** The overlay's `<select>` onchange calls `updatesApi.setGrade`/`setCourse` (shell.js:33-42), which call `render()`. `render()` runs `Screens.closeOverlays()` (screens.js:757-761), which destroys every `.modal` node — including the `.modal--updates` dialog itself. The subsequent `fillFilterArea(nf)` (screens.js:1156-1163) then mutates a now-detached node, so the documented "update the course list **in-place without closing and re-opening the dialog** … preserves scroll position and focus" (04-implementation.md, "Key decisions") does **not** happen — and that re-populate code is effectively dead. The selection still persists and the header updates (no crash, no data loss), but the overlay-mirror UX contradicts its spec and focus is dropped to `document.body` mid-interaction. | **No** |
| minor    | `shell.js:64-72` & `shell.js:33-42` | **No in-flight guard / out-of-order risk** in the four async `set_active_*` helpers. Each awaits the bridge then overwrites `state.data` with a full fresh state and re-renders. Rapid successive changes issue overlapping calls; an earlier response resolving last would clobber a newer selection. Low risk (sequential UI, fast local bridge) — acceptable, but a disable-while-pending or last-write-wins guard would harden it. | No (acceptable) |
| minor    | `shell.js:64-72` vs `shell.js:33-42` | **Duplication:** `setActiveGrade`/`setActiveCourse` (header) and `updatesApi.setGrade`/`setCourse` (overlay) are near-identical; they differ only in the return value (overlay returns `newState.filter`). Could collapse to one helper returning the fresh state. Cosmetic. | No (cosmetic) |
| minor    | `components.js:53-58` (consumed by the new selects) | **a11y: label not programmatically associated.** `UI.select` → `UI.field` renders a `<label class="field__label">` with no `for`, and the `<select>` has no `id`, so the new grade/course labels are visual-only — not linked for AT. This is **pre-existing shared-component behavior** reused here (not a regression introduced by this PR), but the new filter selects inherit it. Flag to `accessibility-tester`; a proper fix belongs in `UI.field` (generate an id + `for`), not in this ticket. | No (pre-existing) |
| minor    | `screens.py:946` (not changed by this PR) | **grades string-sort** — `["all", *sorted(grade_map)]` mis-orders if grades 9/10 are ever registered (`["10","11","12","9"]`). Correct for the current `{11,12}` data; the JS renders in model order so the fix is a numeric sort in `curriculum_filter_model`. Already disclosed by the developer; out of scope (model file untouched). | No (future, acknowledged) |
| minor    | `shell.css` / `screens.css` comments | **Hex-lint workaround** — CSS comments say "epic 102" instead of "#102"/"#123" to dodge the `#NN` false-positive in `test_web_components.py`'s hardcoded-hex regex. Harmless here, but it's a smell that the lint matches inside comments; worth a follow-up to scope the regex to declarations so authors aren't constrained in prose. Not a defect in this PR. | No (informational) |

## Notes / things verified clean
- **No-results state** (`shell.js:renderNoResults`, `render()` empty branch): correct.
  `renderFilterControls(data)` is included in the empty state so the user can clear/change
  the filter and escape — good recovery path. The bridge omits subjects with zero visible
  items (bridge.py:122,128), so the `state.subject`/`state.item` clamps cannot land on an
  empty `items` list — defensive clamp is sound.
- **Dependent-course logic**: course options derive from `filter.gradeMap[activeGrade]`
  with grade="all" ⇒ course-list = just "All"; grade reset → course reset is the bridge's
  server-side side-effect, surfaced correctly on re-render. Correct.
- **`h()` null-child tolerance** (dom.js:20-21) makes the `clearBtn`-null case and
  `renderFilterControls` returning null both crash-safe.
- **i18n**: every label sourced from `filter.labels.*` / `model.filter.labels.*`; no
  hardcoded user strings. Course codes (`SPH3U`) rendered raw, which is correct (they are
  codes, not translatable).
- **CSS token-only**: all new declarations use `var(--*)` tokens (incl. the focus ring);
  token-lint tests pass.
- **Contract adherence**: vanilla-JS no-build, reuses `UI.select`; no PyWebView import in
  reviewed JS-consumed Python; `screens.py`/`bridge.py` unchanged — merged Python contract
  not behavior-changed.

## Verdict
**Request changes** — one **major** (overlay closes on grade/course change; in-place
re-populate is dead code). No **blocker** finding, so the review gate as defined
("advances only when no `blocker` row is unresolved") is **not** failed on a blocker;
however, the major contradicts the documented overlay-mirror behavior and should be fixed
before merge. Suggested fix direction: from the overlay path, avoid the full `render()`
(or re-open / preserve the overlay after it) so the Settings mirror updates in place as
designed — e.g. have the overlay helpers persist + return the fresh filter without the
shell-wide `closeOverlays()`, and refresh the nav separately. No cross-layer/architecture
escalation needed (no contract or Python change); this is contained in the frontend lane.

**Gate:** no unresolved `blocker` → technically passes; **review status: changes-requested**
on the open `major`. Re-review after the overlay-close fix.
