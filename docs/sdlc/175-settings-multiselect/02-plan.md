# 175 — Settings/Updates-overlay filter: default All/All + multi-select  ·  plan
owner: dev-manager + project-manager  ·  epic #102  ·  **first live board-model run (D24–D29)**

## 0. Code pre-flight (D19 — mandatory; sized from this, not the title)

Read: `core/settings.py`, `web/bridge.py`, `web/screens.py::curriculum_filter_model`,
`frontend/shell.js` (header filter row), `frontend/screens.js` (overlay mirror),
`tests/test_web_shell.py` + `tests/test_settings.py`; `gh` #175/#173/#174/#172/#123/#102/#176.

**Already built (the curriculum filter shipped in #122/#124/#125/#126/#123):**
- **Persistence** — `core/settings.py` already stores `active_grade` / `active_course`
  as **scalars** (`"all"` or a value). `DEFAULTS` already = `active_grade:"all"`,
  `active_course:"all"`. Methods: `set_active_grade` (resets course), `set_active_course`
  (validated against grade via `_course_ok`), `_normalize_filter`, fail-soft coercion.
- **Bridge** — `set_active_grade` / `set_active_course` (scalar); `item_visible(item,
  active_course, lang)` (line 80) takes **one scalar course**; `item_courses` →
  `frozenset`; `navigation_model(active_course, lang)`.
- **Screens** — `curriculum_filter_model(active_grade, active_course)` builds the
  descriptor (`activeGrade`/`activeCourse`/`gradeMap`/`labels`), shared by header + overlay.
- **Frontend** — header `renderFilterControls` = grade `<select>` + dependent course
  `<select>` (single-select) + clear button, with in-flight seq guards
  (`shell.js` 51–134); the overlay mirror is `fillFilterArea` in `screens.js`
  1136–1174 — note it lives in the **Updates overlay** (`updates_screen` /
  `updates__filter-section`), *not* a separate "Settings" screen (see friction F5).
- **i18n** — `ui.filter.*` keys exist (en.json 496–504): grade/course/all/clear/
  badge_aria/no_results(+detail)/settings_heading/settings_hint.
- **Tests** — `tests/test_web_shell.py` 123–178 already pin `item_visible` /
  `navigation_model` / `set_active_course` against the **scalar** signature; these
  are exactly the contract that changes. `tests/test_settings.py` pins the store.

**Genuinely missing (the real #175 work):**
- **Req 2 — scalar → set.** `active_course` (scalar) → an **active-courses set**
  across all five layers: settings store + validation, `item_visible` (ANY active
  course matches), `navigation_model`, `curriculum_filter_model` descriptor, and the
  frontend control (course `<select>` → **checkbox group**). New component in
  `components.js` (checkbox group) + CSS; possibly 1–2 new `ui.filter.*` label keys.
- **Req 1 — default All/All.** ⚠️ **Pre-flight finding:** `DEFAULTS` is *already*
  All/All, so on a fresh install req 1 is effectively a **no-op at the persistence
  layer**. The real "default" question is the *multi-select empty state* (no boxes
  ticked ⇒ All) and what the live UX gate actually saw. BA must confirm what
  "default to All/All" means beyond the existing default (see F6) — likely trivial.

**Related risks:** #176 (bare `Bridge()` in tests reads the **real**
`~/.config/study-calc/settings.json`) — the new set-model tests **must** inject
`Settings(tmp_path)`; flag to test-automator. #174 (course-scope / grade=All) is an
adjacent analysis ticket that may reshape the same descriptor — out of scope here,
but the developer should not "fix" #174 behaviour in this PR.

## 1. Ticket weight — **LARGE** (light end)
- [ ] trivial  [ ] standard  [x] **large**
- **Justification.** It is a **cross-layer data-model change** (scalar→set
  propagating through `core/settings.py` → `web/bridge.py` → `web/screens.py` →
  `frontend/*.js` → CSS) **plus** frontend (design cell) **plus** a hard dependency
  on #173 that needs an **ADR**. The weight rule is explicit: *cross-layer change ⇒
  large*; "round up when unsure." So: large.
- **But scope it down on the record (skips are decisions, not gaps):** **no** SQLite
  schema change (the JSON settings store is *not* `data/schema.sql`), **no** DB reseed,
  **no** `learning/**` content, **no** new formula/unit/error code, **no** content
  track. So `sql-pro` and the content track are **skipped**. It is "large" by the
  cross-layer trigger only — see friction F7 (calibration note: this feels like a
  "standard+", not a true large like a new section/content drop).

## 2. The #173 dependency — order & reconciliation

Both #175 and #173 **edit the same function**, `bridge.py::item_visible` (line 80):
- **#173** changes its *semantics* — a `Problems` item must stay visible and filter
  its *contents* (keep-the-item), and it carries an **open design question** (does the
  same keep-and-filter rule apply to formula `Section`s, or only Problems?).
- **#175** changes its *signature* — scalar `active_course` → a **set** of courses.

**Decision: #175 is BLOCKED-BY #173 for implementation; the architecture is designed
ONCE for both.** Rationale: #173 settles the *meaning* of item_visible (and the
Section-vs-Problems question); #175's set-generalization is mechanical on top of
settled semantics — rebasing #175 onto a merged #173 is far cheaper than the reverse,
and designing item_visible twice risks the exact regression the #123 UX gate caught.

**Therefore:** `architect-reviewer` writes **one ADR** covering *both* the
keep-item-filter-contents semantics (#173) **and** the scalar→set model (#175), so
the function is designed once even though it ships as two PRs (#173 first, then #175).
Sequencing #173 ahead of #175 within epic #102 is a prioritization call that touches
the epic's fast-follow order — recorded for the Dev Director (escalation **EP-7**),
recommendation: **do #173 first**.

## 3. Board column → phases (D24; mark applied / skipped)
Status is the **board column**: Todo → Implementation → QA → *(merge)* → Release → Done.

| Column | # | Phase | Apply? | Agent | Why / why skipped |
|--------|---|-------|--------|-------|-------------------|
| Todo | 0 | BA / requirements | **yes** | business-analyst | nail req-1 scope (F6), grade-vs-course multi-select scope, "Settings"=Updates overlay (F5) |
| Todo | 1 | Plan + sub-issue decomposition (D22) | **yes** | dev-manager | this file |
| Todo→Impl | A | **ADR** (scalar→set + #173 semantics, one ADR) | **yes** | architect-reviewer | cross-layer model change — gate **before** impl |
| Impl | 2 | UX research | **skip** | ux-researcher | need already validated by the live #123 UX gate — record skipped |
| Impl | 2a| Visual design (checkbox group, tokens, a11y intent) | **yes (light)** | ui-designer (+ accessibility-tester for a11y intent) | select→checkbox-group is a real control + group semantics |
| Impl | 2b| Design→code handoff | **yes** | design-bridge | hand the checkbox-group spec to frontend |
| Impl | 3 | Python model impl (`core/settings.py` + `web/bridge.py` + `web/screens.py`) | **yes** | python-pro | the scalar→set contract change (headless-tested) — see F3 ownership note |
| Impl | 3b| Frontend impl (`frontend/shell.js`,`screens.js`,`components.js`,CSS) | **yes** | frontend-developer / javascript-pro | checkbox-group UI in header + Updates-overlay mirror |
| Impl | 3c| Data / DB | **skip** | sql-pro | no schema/seed change — JSON settings store, not SQLite |
| Impl | 5 | Code review **on the PR** (D21/D27) | **yes** | code-reviewer | approval = gate into QA; architect-reviewer pulled in as double-reviewer for the model change |
| QA | 4a| Unit / contract tests | **yes** | test-automator | update `test_web_shell.py` 123–178 + `test_settings.py` to the set model; inject `Settings(tmp_path)` (#176) |
| QA | 4b| UI / functional / visual | **yes** | ui-ux-tester | checkbox multi-select flow + visual |
| QA | 4c| Accessibility (WCAG) | **yes** | accessibility-tester | checkbox group: fieldset/legend, keyboard, screen-reader |
| QA | — | **Human-verification sub-issue** (D23) | **yes** | qa-expert creates | headless can't drive pywebview checkboxes/overlay — the #123 lesson |
| QA | 6 | Docs (same PR, D25) | **yes** | technical-writer | `frontend/README.md` + any locale note; checked by qa-expert |
| QA | — | QA sign-off (gate) | **yes** | qa-expert | tests **+** docs |
| Release | 7 | Release (regression + go/no-go) | **defer** | deployment-engineer / devops | batch under epic #102 / the 0.8.2 train (EP-1) — not a per-ticket tag |

**Full QA cell (large, D20):** test-automator + ui-ux-tester + accessibility-tester +
qa-expert — justified because the deliverable is interactive multi-select with real
keyboard/screen-reader surface.

## 4. Sub-issue decomposition (D22) — proposed (see friction F1/F2 before creating)
Native GitHub sub-issues under #175, one per role. ⚠️ The intended `agent:*`/`type:*`
labels **do not all exist in the repo yet** (F1) and creating issues is a mutation the
dev-manager may not run under its current read-only `gh` access (F2) — so these are
**proposed** for the main thread to create once the label taxonomy is reconciled.

| # | Title | Intended labels | Blocks-on |
|---|-------|-----------------|-----------|
| S1 | ADR: curriculum `item_visible` — keep-item-filter-contents (#173) + scalar→set model | `agent:architect-reviewer`, `type:improvement` | — |
| S2 | Design: multi-select course **checkbox group** (header + Updates overlay), tokens + a11y intent | `agent:ui-designer`, `design`, `type:feature` | S1 |
| S3 | Python model: `active_courses` set in settings + `item_visible`/`navigation_model`/`curriculum_filter_model` | `agent:developer`, `area:filter`, `type:feature` | S1, **#173 merged** |
| S4 | Frontend: course checkbox group in header + overlay mirror, in-flight guard | `agent:developer`, `area:filter`, `type:feature` | S2, S3 |
| S5 | Tests: update `test_web_shell`/`test_settings` to set-model; inject `Settings(tmp_path)` | `agent:developer`, `test`, `type:feature` | S3, S4 |
| S6 | Docs: `frontend/README.md` + locale note | `agent:developer`, `documentation` | S4 |
| S7 | Human-verification (D23): drive checkboxes + overlay in the real window | `area:filter`, `type:bug?` | S4 (QA creates) |

## 5. Dependency order
- **Hard external block:** S3 (Python model) waits on **#173 merged** (settled
  `item_visible` semantics). S1 (ADR) covers both and can start now.
- **Parallel after S1:** S2 (design) ‖ S3 (python model, once #173 lands).
- S4 needs **both** S2 (design spec) and S3 (descriptor shape).
- S5 tracks S3+S4; S6 tracks S4. QA cell after the PR is review-approved.
- Release deferred to the epic train (EP-1) — not blocking.

## 6. Gates (Definition of Done per edge)
- **Todo→Impl:** this plan done; ADR (S1) approved; sub-issues decomposed.
- **within Impl:** `uv run --extra dev pytest` green incl. `test_web_shell`,
  `test_settings`, `test_web_components` (token lint), `test_i18n` (any new
  `ui.filter.*` key in **all five** locales); `code-reviewer` **approved** on the PR
  (`Refs #175`, not `Closes`).
- **Impl→QA:** review approved (the gate).
- **QA→Release (merge, dev-manager):** QA sign-off green (tests **+** docs) +
  human-verification (D23) checklist run + no open blocker.
- **Release→Done:** post-merge regression on `master` green; QA closes.

---

## Dispatch plan (ordered, parallel-aware)

1. **main thread → invoke `business-analyst`**
   · in: `00-brief.md`, this plan §0 · out: `01-requirements.md`
   · gate: req-1 scope resolved (is it more than the existing All/All default? — F6),
   grade-vs-course multi-select scope fixed, "Settings overlay" = Updates overlay (F5),
   acceptance criteria + out-of-scope (no #174 fixes) written.

2. **main thread → invoke `architect-reviewer`** *(can run alongside step 1 once #173 is in flight)*
   · in: `01-requirements.md`, #173 body, `bridge.py::item_visible`, `core/settings.py`
   · out: **one ADR** in `docs/adr/` covering #173 keep-item-filter-contents **and**
   #175 scalar→set; note in `02-plan`/`04-implementation` · gate: ADR approved; the
   `active_courses` set shape + `item_visible` semantics fixed **before** any impl.

3. **main thread → invoke `ui-designer`** (with `accessibility-tester` for a11y intent)
   · in: `01-requirements.md`, ADR, `frontend/shell.js` filter row, `web/tokens.json`
   · out: `03-design.md` (checkbox-group spec, tokens, focus order, fieldset/legend ARIA intent)
   · gate: design sign-off; no new hardcoded colors (token-driven).

4. **main thread → invoke `design-bridge`**
   · in: `03-design.md` · out: handoff notes in `03-design.md` (+ any `tokens.css`)
   · gate: frontend has an unambiguous component contract.

5. **main thread → invoke `python-pro`** *(blocked until **#173 merged**)*
   · in: `02-plan.md`, ADR, `core/settings.py`, `web/bridge.py`, `web/screens.py`
   · out: `04-implementation.md` (python section) + code — `active_courses` set model
   · gate: `pytest` green incl. updated `test_web_shell`/`test_settings`; bridge stays
   PyWebView-import-free; any new `ui.filter.*` key in all five locales.

6. **main thread → invoke `frontend-developer`** *(needs steps 3–4 + 5's descriptor)*
   · in: `03-design.md`, `04-implementation.md`, `frontend/shell.js`,`screens.js`,`components.js`
   · out: `04-implementation.md` (web section) + checkbox-group UI (header + overlay mirror)
   · gate: `test_web_components` token lint green; `test_web_shell` JS-string lint green.

7. **main thread → invoke `code-reviewer`** (delegate `architect-reviewer` as double-reviewer — model change)
   · in: the PR diff (`Refs #175`) · out: PR review + **approval** (no local artifact, D21/D27)
   · gate: no unresolved blocker; **approval = Implementation→QA edge**.

8. **main thread → invoke `qa-expert`** (QA lead; plan + create the D23 human-verification sub-issue)
   · in: `01`–`04`, the PR · out: `05-tests.md` (plan) + S7 sub-issue with launch cmds + checklist.

9. **main thread → invoke `test-automator` ‖ `ui-ux-tester` ‖ `accessibility-tester`** (parallel)
   · in: code + running app · out: `05-tests.md` (results) — unit/contract, functional/visual, WCAG
   · gate: new set behaviour has a failing-without-the-change test; checkbox group keyboard/SR pass.

10. **main thread → invoke `technical-writer`** *(during QA, same PR)*
    · in: diff, `01-requirements.md` · out: `07-docs.md` + `frontend/README.md`/locale note
    · gate: `qa-expert` checks docs as part of sign-off (D25).

11. **main thread → invoke `qa-expert`** (sign-off)
    · in: `05-tests.md` (all executors + human-verification run), docs · out: `05-tests.md` sign-off
    · gate: tests **+** docs green; D23 checklist run → **QA sign-off**.

12. **dev-manager merges** (QA→Release edge — *I* do this, only after: review approved +
    QA sign-off + no blocker), then **defer Release** to the epic #102 / 0.8.2 train (EP-1) —
    ask the Dev Director before any tag.

---

## Process friction (trial #175) — for the Dev Director

First live run of the board-model SDLC surfaced these. F1/F2/F4 also logged as Open
escalations (EP-8/EP-9/EP-10) so they aren't lost.

- **F1 — Label taxonomy is stale & incomplete (blocks D22).** The repo has retired
  `status:planning`/`status:in-dev` (killed by D24) and **lacks** `type:bug`/
  `type:improvement`/`type:feature` (required by D22/D26). The `agent:*` set is the old
  roster (`data-analyst`, `data-scientist`, `ui-ux-designer`, `developer`) — missing
  `python-pro`, `frontend-developer`, `ui-designer`, `qa-expert`, `test-automator`,
  `code-reviewer`, `architect-reviewer`, `technical-writer`. So the sub-issue
  decomposition can't be labelled as the governance prescribes. **Recommend:** a
  one-time label reconciliation — delete retired `status:*`, create the three `type:*`,
  align `agent:*` to the new roster (or collapse to a small set: `agent:developer`/
  `agent:qa`/`agent:design`/`agent:architect`). Needs your sign-off (repo mutation). → **EP-8**

- **F2 — Decomposition is my R/A duty but my `gh` access is read-only (blocks step 1).**
  The RACI makes dev-manager **R/A** for "Decompose into planning sub-issues," but my
  charter restricts `gh` to read-only inspection + status labels — and status labels are
  now retired. So I literally cannot `gh issue create` the sub-issues I'm accountable for.
  **Recommend:** either (a) grant dev-manager scoped `gh issue create`/sub-issue write,
  or (b) make the rule explicit that dev-manager *proposes* the decomposition (as in §4)
  and the **main thread** creates the issues. I've assumed (b) here. → **EP-9**

- **F4 — The board the model calls "source of truth" is unreadable to the agents.**
  `gh project list` fails: token missing `read:project` scope. The classic-projects
  deprecation also breaks default `gh issue view` (must use `--json`). So no agent — nor
  I — can **read or move** the board card the D24 model makes authoritative; "status =
  board column" is currently unenforceable via tooling, and no automation moves cards on
  the transitions. **Recommend:** (a) `gh auth refresh -s read:project,project`; (b)
  define the exact `gh project item-edit` command (or an explicit manual step) each role
  runs for the edge it owns; (c) until then, accept that board moves are a **manual
  Dev-Director/dev-manager step** and say so in `README.md`. → **EP-10**

- **F3 — `web/` Python ownership is ambiguous.** The roster assigns *all* of `web/` to
  the frontend leads, but `web/bridge.py`/`web/screens.py` (and `core/settings.py`) are
  pure-Python, headless-tested **view-model/contract** code — the heart of this ticket's
  scalar→set change. I assigned them to `python-pro` and the `frontend/*.js`+CSS to
  `frontend-developer`. **Recommend** amending the roster wording to: *Python view-model
  files under `web/` → `python-pro`; `frontend/*.js`+CSS → `frontend-developer`.* (Not
  blocking; flag for the next governance pass.)

- **F5 — "Settings overlay" names a screen that doesn't exist.** #175 and the brief say
  "Settings overlay," but the curriculum filter lives in the **Updates overlay**
  (`updates_screen` / `updates__filter-section`). A cold agent told "Settings overlay"
  will hunt for a non-existent Settings screen. BA should reconcile the name in
  `01-requirements.md`. (Minor; absorbed into the BA step.)

- **F6 — Req 1 ("default All/All") is already satisfied at the persistence layer.**
  `DEFAULTS` is already All/All. This is not governance friction but a **validation that
  D19 pre-flight earns its keep**: the brief/title imply two changes; one is a near-no-op.
  BA must confirm what the live UX gate actually wanted (probably the multi-select empty
  state). Flagging so we don't bill design/impl effort for an already-done default.

- **F7 — Weight-boundary calibration (Q1).** This ticket is "large" purely because
  *cross-layer* is a large-trigger, yet it has no schema/content/DB/new-section and each
  layer delta is small — it behaves like a "standard+". The cross-layer trigger may
  over-fire for a small data-model widening. **Recommend** for the Q1 calibration:
  distinguish "cross-layer *content/section/schema*" (true large) from "cross-layer
  *data-model widening*" (could be standard with an ADR). Logged for D13/Q1, no action now.

## Trial resolutions (2026-06-11 — Dev Director ruled)

The friction this plan surfaced was decided the same day; read this plan under the
**revised** governance:

- **EP-7 → resolved.** #173 ships **first**; #175 rebases on it. One ADR
  (`architect-reviewer`) covers both `item_visible` changes. #175 stays in **Todo,
  blocked on #173** — do not dispatch step 1 until #173 lands.
- **EP-8 → resolved.** Labels cleaned: `status:*` + `QA-ready`/`FIX required` **deleted**;
  **kind = the existing `bug`/`enhancement`** labels (improvement = `enhancement`) — **no
  `type:*` namespace** (D26 revised). Wherever this plan's decomposition says `type:*`,
  read `bug`/`enhancement`.
- **EP-9 → resolved (D30).** `dev-manager` now **holds issue-create** — it creates the
  decomposition sub-issues itself (not the main thread).
- **EP-10 → resolved (D24 revised).** The board is a **human view**, not the source of
  truth; status is derived from **issue/PR state**. "Move the card" steps in this plan are
  non-authoritative board upkeep, done by hand.
- **F3 / F5 / F6 / F7** remain flagged for the next governance pass / BA step as above.
