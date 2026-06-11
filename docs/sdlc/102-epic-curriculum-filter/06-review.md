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

---

## Re-review (PR #177) — 2026-06-11 · code-reviewer

Second pass over the review-fix commit `27165eb` (delta only; `edd4de5` reviewed
above). Touched in the delta: `shell.js`, `components.js`, and the two artifacts —
**no CSS, no Python** changed by the fix. Gate re-run: `uv run --extra dev pytest -q`
→ **479 passed, 1 skipped**; `test_web_components.py` token-lint → 10 passed.

### First-review findings — disposition
| Prior finding | Status |
|---------------|--------|
| **major** overlay closes on grade/course change; in-place re-populate dead | **Resolved.** `render({ keepOverlays = false })` (shell.js:356) gates `Screens.closeOverlays()` behind `if (!keepOverlays)`; `setActiveGrade`/`setActiveCourse` (shell.js:69-85) call `render({ keepOverlays: true })`. The overlay is appended to `document.body` outside `#app` (screens.js:1197), and `render()` only rebuilds `#app` via `replaceChildren`, so the live `.modal--updates` node is untouched and `fillFilterArea(nf)` (screens.js:1156/1165) now mutates a still-connected `filterSection`. Verified live in-place update path. |
| **minor** no in-flight guard | **Resolved (common case).** `_gradeSeq`/`_courseSeq` (shell.js:67-68) captured pre-`await`, compared post-`await`; stale responses return `null` → discarded, last-write-wins. Correct. |
| **minor** header/overlay helper duplication | **Resolved.** `updatesApi.setGrade/setCourse` now delegate (shell.js:32-33). |
| **minor** a11y label not associated | **Resolved.** `UI.field(label, control, id=null)` (components.js:62) generates a unique `field-N` id, sets `control.id` + label `for`. Monotonic counter, old nodes dropped on re-render → no live-DOM duplicate-id collisions. Explicit-`id` param lets self-managed controls opt out. Sound. |
| **minor** `screens.py:946` grade string-sort | Out of scope, model file untouched — still acknowledged for follow-up. |
| **minor** hex-lint-in-comments smell | Informational, unchanged. |

### Delta correctness — verified clean
- **No listener leak / no double-render.** The overlay node is not recreated under
  `keepOverlays`, so its `click`/`keydown` (focus-trap) listeners are not duplicated;
  `fillFilterArea`'s `replaceChildren` discards the old `<select>` nodes (and their
  `onchange`) for GC and wires fresh ones. Header controls (in `#app`) and the overlay
  `filterSection` (on `body`) are disjoint subtrees — no node is rendered twice.
- **`updatesApi` → helper delegation is hoist-safe** (`setActiveGrade` is a hoisted
  function declaration; the arrows in the `const updatesApi` only dereference it at
  call time).
- **`keepOverlays:true` from the header path is harmless** — body overlays are modal
  with focus traps, so the header selects are unreachable while one is open; skipping
  `closeOverlays()` there is a no-op in practice.

### Live-gate defects (#172–#176) — confirmed NOT introduced by this PR
This delta touches only `shell.js` / `components.js` / docs. **#173** (course selection
hides the whole Problems tab) is rooted in the already-merged `web/bridge.py::item_visible`,
which this PR does not touch — confirmed not a regression of #177. #172/#174/#175/#176 are
likewise outside this diff. No new defect introduced.

### Non-blocking nits (follow-up, do not block merge)
1. **Focus on the just-changed select is still dropped.** `fillFilterArea`
   (screens.js:1137-1173) unconditionally rebuilds *both* selects on any change, so the
   control the user just operated is replaced → focus falls to `document.body`. The major
   (overlay vanishing) is fixed, but `04-implementation.md`'s "preserves focus" claim is
   only partially met. Pre-existing `fillFilterArea` design, not introduced by this delta.
   Cheap hardening: on a *course* change nothing structural changes, so the
   `if (nf) fillFilterArea(nf)` at screens.js:1165 can be skipped (or restore focus to the
   live course `<select>` after rebuild).
2. **Cross-endpoint race not guarded.** `_gradeSeq` and `_courseSeq` are independent, so
   interleaving a grade change with a course change inside the same in-flight window isn't
   covered (both write `state.data` wholesale). Practically unreachable in this sequential
   UI; note only — matches the first review's "acceptable" call.

### Verdict: **APPROVE**
All first-review findings resolved; the major is genuinely fixed (overlay survives, in-place
re-populate now live, no leak/double-render); a11y association and in-flight guard are sound;
no token violations (delta has no CSS; PR-added CSS is token-only); gate green (479/1). The
two nits above are non-blocking follow-ups. No `blocker`/`major` open → **review status:
approved**. (Merge remains `dev-manager`'s action per the GitHub-actions RACI.)
