# 173 — Problems-tab filter — plan  ·  owner: dev-manager + project-manager

Second live run of the board-model SDLC (after #175's plan-only trial). #173 lands
**first** in epic #102's fast-follow chain (EP-7); #175 rebases on its settled
`item_visible` semantics. #173 is **not blocked** — it's the one that unblocks #175.

## Code pre-flight (D19) — what's already there vs. missing

Read against the live tree (`web/bridge.py`, `web/screens.py`, `web/frontend/screens.js`,
`tests/test_web_shell.py`, `study_calc/locales/en.json`). Findings:

**The bug (confirmed at the named site).** `web/bridge.py::item_visible` (L80) treats a
`Problems` item exactly like a tagged `Section`: `item_courses()` (L42) unions the
courses across the subject's problems, and `item_visible` returns
`active_course in courses` — so when the active course isn't in the union the whole
`Problems` nav entry is **dropped** by `navigation_model` (L117, `if visible:`). This is
the symptom: select a course Physics-Problems isn't tagged for → the Problems item
vanishes. Logic shipped in #122/#124; #123 only made it user-reachable.

**`problems_screen` is NOT course-aware yet.** `web/screens.py::problems_screen` (L804)
calls `problems_for_subject(subject_id, language)` (`core/learning.py` L369) which filters
by **subject only** — there is no `active_course` parameter anywhere in the problems path.
So "filter the contents" is genuinely missing; it must be added (pass the active course
into `problems_screen` and filter the list).

**An empty-state already exists — reusable.** `problems_screen` already returns an
`empty` label (`problems.empty`, L842) and the frontend already renders it:
`web/frontend/screens.js` L418 — `if (!problems.length) … UI.hint(L.empty)`. The locale
keys exist in en (`problems.empty` L87; `ui.filter.no_results` + `_detail` L501–502) and
should be present across all five locales. **So the no-results UI is already built** —
the frontend change is near-zero unless the ADR wants a filter-specific message distinct
from "no problems yet."

**Tests pin the OLD (buggy) behavior — they must change.** `tests/test_web_shell.py`:
- `test_filter_sph4u_hides_other_courses` (L140) asserts Math **drops** `problems:math`
  (L149) and Chemistry keeps only the periodic tool, i.e. `problems:chemistry` is dropped
  (L151) — both assertions invert under the fix (the Problems item must **stay**).
- `test_set_active_course_method_filters_and_persists` (L177) L181 asserts
  `chemistry == ["tool:periodic_table"]` under SPH4U — also inverts.
- `test_item_visible_rules` (L123) / `test_item_courses_unions...` (L114) pin the
  Section rules; whether they change depends on the ADR's Section ruling.

**Net:** ~10–20 lines in `bridge.py` + `screens.py`, a signature/threading change to pass
the active course into `problems_screen`, a handful of test updates + one new test, an
ADR, and a *conditional* near-zero frontend touch. No core/domains, no schema, no DB
reseed. No new formula/unit/error code (a new empty-state copy key is *possible* but
avoidable by reusing `ui.filter.no_results`).

## Open design question → ADR (#178, shared with #175 — EP-7)

**Question (from the brief):** should "keep the item, filter its contents" apply to
formula `Section`s too, or **only** to `Problems`?

This is a **cross-layer semantics** call and therefore `architect-reviewer`'s, not
dev-manager's (process-only). I flag it for the **shared ADR** (#178) that covers *both*
`item_visible` changes — designed once, shipped as two PRs (#173 then #175). The framing
the ADR must resolve (not my decision):
- **Only Problems** — minimal, matches the literal brief and the symptom. Sections keep
  drop-on-mismatch; only `Problems` becomes keep-and-filter. Simpler contract; the
  formula picker stays untouched.
- **Sections too** — consistent mental model ("a course narrows content, never removes
  navigation"), but pulls in `formula_screen` (filter the formula list + an empty state
  there) and changes more pinned tests; larger blast radius and arguably scope-creep on
  a bug ticket. If chosen, the `Section` work likely warrants its own follow-up.

`architect-reviewer` decides and records it in `docs/adr/` so #175's scalar→set
multi-select consumes the same semantics.

## Ticket weight

- [ ] trivial
- [x] **standard** — one bugfix concentrated in `web/bridge.py` + `web/screens.py`, a
  conditional near-zero frontend empty-state, one shared ADR, and test updates.
- [ ] large
- **Justification:** set from the pre-flight, **not** the "analysis ticket" framing. No
  schema change, no new section, no DB reseed, no new i18n contract key required — so not
  *large*. But it changes **navigation-visibility semantics** (cross-#175, needs an ADR),
  touches the frontend, and rewrites contract-adjacent tests — so not *trivial*. Rounds to
  **standard**. The ADR is about the *semantics decision*, not implementation footprint;
  it does not by itself promote the ticket to large.

## Sub-issues (D22 / D30 — created by dev-manager, linked to #173)

Decomposed one-per-role and created via `gh issue create` (D30 grant), linked as native
GitHub sub-issues of #173:

| # | Role / label | Scope |
|---|--------------|-------|
| #178 | `agent:architect-reviewer` · `design` | **Shared ADR** (with #175): `item_visible` keep-item-filter-contents semantics; Section-vs-Problems ruling |
| #179 | `agent:python-pro` · `bug` | `bridge.py::item_visible` + `screens.py::problems_screen` course-filter + test updates/new test |
| #180 | `agent:frontend-developer` · `bug` | `screens.js` filtered no-results state (near-zero; may fold into #179) |
| #181 | `agent:qa-expert` · `test` | QA plan + sign-off + human-verification (D23) |
| #182 | `agent:technical-writer` · `enhancement` | CHANGELOG/README note, authored in QA (D25) |

`agent:*` labels for the new roster did not exist (old roster only — see Process
friction); dev-manager created them (EP-8 authorized the alignment). The
human-verification sub-issue (D23) is **not** pre-created — it's raised by dev-manager
when `qa-expert` flags the headless gap during QA.

## Stage → phases (mark applied / skipped)

Status is **derived from issue/PR state**; the board just mirrors these stages (D24).

| Column | # | Phase | Apply? | Agent | Why / why skipped |
|--------|---|-------|--------|-------|-------------------|
| Todo | 0 | BA / requirements | light | business-analyst | Brief is thorough + grounded; BA done inline in this plan, no separate `01` pass / sub-issue |
| Todo | 1 | Plan + sub-issue decomposition | yes | dev-manager | this file; #178–#182 created |
| Implementation | — | **ADR** (precedes impl) | **yes** | architect-reviewer | #178 — gates phase 04; shared with #175 |
| Implementation | 2 | Design (visual/tokens) | **skip** | ui-designer | No new visual design — empty-state component (`UI.hint`) + `ui.filter.no_results` copy already exist. Design cell skipped on the record |
| Implementation | 3 | Core impl (core/domains) | **skip** | python-pro | No `core/`/`domains/` change; the bug is in `web/` |
| Implementation | 3b | Impl — `web/` Python view-model | **yes** | python-pro | #179 — `bridge.py` + `screens.py` (pure-Python nav/visibility logic) |
| Implementation | 3b | Impl — `web/frontend/` JS | **conditional** | frontend-developer | #180 — only if a filter-specific message is wanted; else fold into #179 |
| Implementation | 3c | Data / persistence | **skip** | sql-pro | No schema, no DB reseed (no `learning/**` change) |
| Implementation | 5 | Review **on the PR** (D21/D27) | yes | code-reviewer | approval gates → QA; architect-reviewer is Consulted (authored the ADR) |
| QA | 4 | Unit/contract tests | yes (in-phase) | python-pro writes; test-automator not separately spawned | D20 standard: dev writes unit/contract tests in the impl PR |
| QA | 4b | Functional/visual/a11y executor | yes | ui-ux-tester | one combined pass (frontend touched), under qa-expert |
| QA | — | Human-verification (D23) | yes | qa-expert flags → dev-manager creates | pywebview Problems tab can't be driven headlessly |
| QA | 6 | Docs (same PR, D25) | yes (light) | technical-writer | #182 — CHANGELOG/README; checked by qa-expert at sign-off |
| QA | — | QA sign-off (gate) | yes | qa-expert | #181 — tests **+** docs |
| Release | 7 | Release (regression + go/no-go) | epic-level | deployment-engineer / devops | post-merge regression on `master`; tag held for 0.8.2 (EP-1); go/no-go with Dev Director |

## Dependency order

1. **ADR (#178) is the first gate** — it settles the Section-vs-Problems semantics that
   both #179 (this ticket) and #175 implement. Implementation does **not** start until
   the ADR is merged.
2. After the ADR: **#179 (python) is the critical path.** #180 (frontend) is conditional
   and, if needed at all, can run in parallel once the ADR's copy decision is known;
   most likely it folds into #179 (the empty-state already renders).
3. Review (code-reviewer, on the PR) gates Implementation→QA.
4. QA (one combined `ui-ux-tester` pass + qa-expert sign-off) + docs (#182) run in the
   QA column on the same PR. The human-verification sub-issue (D23) must close green
   before sign-off.
5. **dev-manager merges** (QA→Release edge) once review approved + QA sign-off (tests +
   docs) green + no open blocker (D29). PR body uses `Refs #173` (EP-6a) — QA closes.
6. Release/regression is **epic-level** — likely batched with the rest of #102's
   fast-follows under the held 0.8.2 tag; go/no-go is a dev-manager + Dev Director call.
7. **Cross-ticket:** on merge of #173, notify that #175 can unblock and rebase on the
   shipped `item_visible` semantics.

## Dispatch plan

Ordered, parallel-aware. Each step: `main thread → invoke <agent>` with inputs/outputs +
the gate that closes it.

1. **main thread → invoke `architect-reviewer`** (#178) · in: `00-brief.md`, `02-plan.md`,
   the pre-flight above, the #175 brief · out: new ADR in `docs/adr/` (shared
   item_visible semantics; Section-vs-Problems ruling) · **gate:** ADR merged; the
   `navigation_model` / `problems_screen` (+ `formula_screen` if Sections in scope)
   contract is written down. *Blocks all implementation.*

2. **main thread → invoke `python-pro`** (#179) · in: ADR (#178), `02-plan.md`,
   `tests/test_web_shell.py` · out: `04-implementation.md` (web section) + code:
   `item_visible` keeps `Problems` (Sections per ADR), `problems_screen` filters by active
   course, updated/new tests; open a PR `Refs #173` · **gate:** `uv run --extra dev pytest`
   green incl. contract tests (`test_i18n`, `test_references`, `test_learning`,
   `test_problems`); the kept-and-filtered Problems behavior has a failing-without-the-fix
   test.

3. *(conditional, parallel with 2 once ADR copy decision is known)* **main thread →
   invoke `frontend-developer`** (#180) · in: ADR (#178), `screens.js` (L414 `problems`) ·
   out: `04-implementation.md` (frontend section) — filter-specific no-results message **iff**
   the ADR wants one; any new key added to all five locales · **gate:**
   `tests/test_web_components.py` green (no hardcoded colors). *Skip/fold into step 2 if no
   new copy is needed — record the skip in `04-implementation.md`.*

4. **main thread → invoke `code-reviewer`** on the PR · in: the PR diff, ADR (#178) · out:
   PR review + **approval** (no local artifact — D21/D27); if it needs architecture
   re-confirmation it asks dev-manager (architect-reviewer already Consulted via the ADR) ·
   **gate:** approved, no open blocker-severity finding → Implementation→QA.

5. **main thread → invoke `qa-expert`** (#181) · in: `01`–`04`, the running app · out:
   `05-tests.md` (plan) + defect triage; **flags the headless gap → dev-manager creates the
   D23 human-verification sub-issue** (launch cmd + checklist) · **gate:** plan written;
   human-verification raised.
   - 5a. **main thread → invoke `ui-ux-tester`** · in: running app, `05-tests.md` plan ·
     out: `05-tests.md` (functional/visual/a11y results — Problems tab stays, list narrows,
     empty state on no-match, clear restores) · gate: executor pass recorded.

6. **main thread → invoke `technical-writer`** (#182) · in: the PR diff, `00-brief.md` ·
   out: `07-docs.md` + CHANGELOG/README note (same PR) · **gate:** docs present (checked by
   qa-expert in sign-off, D25).

7. **main thread → invoke `qa-expert`** (sign-off) · in: `05-tests.md`, `07-docs.md`,
   human-verification result · out: `05-tests.md` sign-off · **gate:** tests **+** docs
   green; human-verification green → QA→Release.

8. **dev-manager merges** the PR (QA→Release edge, D29): review approved + QA sign-off green
   + no open blocker. PR body `Refs #173`. Then **main thread → invoke `deployment-engineer`
   / devops** for post-merge **regression on `master`**; go/no-go with the Dev Director;
   tag held for 0.8.2 (EP-1) → `08-release.md`.

9. **QA closes #173** after regression green. dev-manager notifies that **#175 can unblock**
   and rebase on the shipped `item_visible` semantics.

---

## Process friction (run #173)

Stress-test feedback on the **just-revised** governance (D23–D30), prioritizing things
that *changed* since #175 and now read wrong on a real bug ticket, and the D30
issue-create grant.

1. **D30 issue-create worked — but the `agent:*` label roster was missing (EP-8 only
   half-done).** The grant itself is fine: `gh issue create` + `gh label create` + the
   GraphQL `addSubIssue` mutation all succeeded, and #173 was already a native sub-issue
   of #102, so the pattern is proven. **But** EP-8 was marked Resolved with "`agent:*`
   extended as needed," yet the repo still only had the **old** roster
   (`agent:developer`, `agent:data-scientist`, `agent:ui-ux-designer`, `agent:data-analyst`)
   — none of `python-pro` / `frontend-developer` / `architect-reviewer` / `qa-expert` /
   `technical-writer`. I created the five missing labels under the EP-8 authorization, but
   this is a gap: **the label set is not reconciled to the agent roster the governance
   names.** *Recommendation:* do the one-time `agent:*` reconciliation for real (create the
   full new-roster set, retire/alias `agent:developer` etc.), and add a pre-flight check to
   the plan step so dev-manager isn't silently minting labels mid-decomposition. Mild —
   needs a Dev Director nod since it's a repo-taxonomy mutation. *(Logging as a re-surfaced
   EP-8 follow-up.)*

2. **D23 vs D30 contradiction: who *creates* the human-verification sub-issue?** D23 (as
   written in my charter and CLAUDE.md) says "**QA creates** a human-verification
   sub-issue." D30 + the GitHub-actions RACI say **only dev-manager** holds issue-create
   and QA *flags*; dev-manager creates. On this ticket the two collide directly (the
   pywebview Problems tab is exactly a headless gap). I resolved it in the dispatch plan as
   "qa-expert **flags** → dev-manager **creates**," but the governing text still says QA
   creates. *Recommendation:* reword D23 to "QA **flags** the headless gap; dev-manager
   creates the human-verification sub-issue" across `CLAUDE.md`, `dev-manager.md`, and
   `docs/sdlc/README.md`. Needs Dev Director sign-off (it touches an agent charter).

3. **The kind label for an ADR / architecture sub-issue is undefined.** D26 fixes kind =
   `bug` / `enhancement`. An ADR sub-issue (#178) is neither — it's a decision doc. I used
   the repo's existing `design` label, but D26's text only blesses `bug`/`enhancement` as
   "kind" (with `design`/`test`/`epic` mentioned only in passing). *Recommendation:*
   explicitly state that `design` and `test` are valid kind labels for ADR/QA sub-issues
   (they already exist in the repo), so the kind taxonomy matches what decomposition
   actually needs. Low stakes; a one-line clarification.

4. **`web/*.py` ownership is ambiguous between the python and frontend leads.** The
   phase→agent map assigns `core/`+`domains/` to `python-pro` and `web/`+`frontend/` to
   `javascript-pro`/`frontend-developer`. But the #173 fix lives in `web/bridge.py` +
   `web/screens.py`, which are **pure-Python view-models**, not JS. Literally read, the map
   hands them to the frontend lead; in practice `python-pro` is the right owner for nav/
   visibility logic and the JS lead owns only `frontend/*.js`. I split it that way (#179
   python / #180 frontend) but the map is genuinely ambiguous here. *Recommendation:* refine
   the map to "`web/**.py` (bridge/screens view-models) → `python-pro`; `web/frontend/**`
   → `frontend-developer`/`javascript-pro`." This recurs on every bridge/screens ticket.

5. **"Standard ⇒ one sub-issue per role" risks over-decomposition on a ~15-line bugfix.**
   D22 + D20 produced 5 sub-issues (ADR, python, frontend, QA, docs) for a fix whose code
   delta is tiny and whose frontend/docs parts are near-zero. It's defensible (each is a
   different agent + a real gate), but on a bug this small the overhead-to-work ratio is
   high. I flagged #180 as fold-able and kept BA inline. *Recommendation:* allow dev-manager
   discretion at standard weight to **fold near-zero roles into the lead's sub-issue** and
   record the fold (rather than a strict one-per-role). Calibrate against #175's actual
   decomposition once both run. Provisional — worth a DECISIONS note after this run.

6. **Tests that pin buggy behavior aren't called out as a gate hazard anywhere.** The
   impl gate is "pytest green," but here the *correct* fix makes currently-green tests fail
   until they're rewritten (`test_filter_sph4u_hides_other_courses` etc.). A naive developer
   could "make pytest green" by *not* changing the assertions, masking the fix. Not a
   governance bug, but the gate wording ("pytest green") is insufficient for bugfix tickets
   where existing tests encode the defect. *Recommendation:* for `bug` tickets, the impl
   gate should read "pytest green **and** the assertions that encoded the old behavior are
   updated, with a test that fails without the fix." Minor wording add to the
   Implementation gate. *(Captured here; raise with #2/#5 as a batch.)*
