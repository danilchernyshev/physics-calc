# AI-SDLC handoff contract

This folder is the **memory bus** for the agent dev team. Subagents start cold —
they don't see the conversation or each other — so every phase reads and writes
plain files here. One subfolder per ticket: `docs/sdlc/<ticket>/` (e.g.
`docs/sdlc/172-add-optics-section/`).

Copy `_template/` to start a ticket. Each artifact is owned by one phase; later
phases read earlier ones. The **Dev Manager** agent (`.claude/agents/dev-manager.md`)
decides which phases apply and in what order; the **main thread** dispatches the
specialist agents per its plan.

## Two tracks

Most tickets run the **code track** (00→07). Big study-content drops — reviewing
public resources, building a study plan, authoring problems/solutions into
`learning/` — run the **content track** (R1→R4) instead. A dedicated
`curriculum-author` agent is **deferred to future work** (`ai-sdlc/future/`);
interim, the content track is led by **installed** research agents
(`research-analyst`, `search-specialist`, `scientific-literature-researcher`) + the
main thread. The `dev-manager` decides which track a ticket is, in `02-plan.md`.

## Code track artifacts (the contract)

| File | Owner phase | Lead agent | Purpose |
|------|-------------|-----------|---------|
| `00-brief.md` | intake | human / main thread | the raw ask + links |
| `01-requirements.md` | BA | `business-analyst` | scope, acceptance criteria, out-of-scope |
| `02-plan.md` | Plan | `dev-manager` + `project-manager` | track choice, phase breakdown, dependencies, skipped phases, dispatch order |
| `03-design.md` | Design | `ui-designer` | UI/UX decisions, tokens, Figma links (omit for engine-only tickets) |
| `04-implementation.md` | **Implementation** | `python-pro` (core/domains) · `javascript-pro` / `frontend-developer` (web/frontend) · `sql-pro` (db) | what changed in each layer, schema & migration notes, key decisions, files touched |
| `05-tests.md` | Test | `test-automator`, `ui-ux-tester` | test plan + results; unit, visual, a11y |
| `07-docs.md` | Docs (in the **QA** column) | `technical-writer` | docs/README/locale notes — authored during QA in the same PR, **checked by `qa-expert`** as part of QA sign-off |
| `08-release.md` | Release | `deployment-engineer` + `git-workflow-manager` | version bump, CI status, PR/release notes |

**Code Review has no local artifact** — it happens on the GitHub PR (D21), inside
the **Implementation** column (there is no separate Code Review column — D27); the
reviewer's approval is the gate into QA. So `06` is retired from the file set — the
PR is the review record.

**Implementation (`04`) is where python / js / db dev actually happens** — one
artifact, multiple leads by layer, each writing its section: `python-pro` for
`core/` + `domains/` engine, `javascript-pro` / `frontend-developer` for
`web/` + `frontend/`, `sql-pro` for the database.

The project **already ships a SQLite knowledgebase** (`core/db.py`,
`data/schema.sql`, `data/knowledgebase.db` — a read-only content store mirroring
`learning/`, per [ADR 0002](../adr/0002-knowledgebase-db.md)). So `sql-pro` is a
standing implementation lead, not a future role: it owns schema changes and
migrations, recorded in `04-implementation.md`. The i18n contract holds in the DB
too — rows are keyed by `(id, language)` with `en` canonical and fallback, never
display strings hard-coded into engine code.

## Content track artifacts (interim: installed research agents — dedicated agent is future)

| File | Purpose |
|------|---------|
| `00-brief.md` | the raw ask (subjects/courses in scope) |
| `R1-research.md` | public resources reviewed; link + license/originality note per source |
| `R2-study-plan.md` | study plan: subjects → courses (Ontario codes) → topics → intended problems; engine deps for `dev-manager` |
| `R3-content-drafts/` | the authored `topics/` · `glossary/` · `problems/` JSON (English first) |
| `R4-content-review.md` | originality confirmed, links 200, course codes valid, `test_learning`/`test_problems` green, locale plan |

Content gates: `uv run --extra dev pytest tests/test_learning.py tests/test_problems.py
tests/test_db_in_sync.py` green, every referenced glossary term resolves, no
dangling `see_also`, every study link HTTP 200, all content original (videos/sites
linked not copied), `en` authored as canonical (es/fr/uk additive afterwards).

### Content ↔ database bridge (don't skip the reseed)

The JSON under `study_calc/learning/**` (and `data/elements.json`) is the **source
of truth**, but the app does **not** read it at runtime — `core/learning.py` serves
everything from the committed SQLite artifact `study_calc/data/knowledgebase.db`,
which is *derived* from the JSON by `scripts/seed_db.py` (per ADR 0002). So any
content change has a mandatory last step:

```bash
python scripts/seed_db.py                       # rebuild knowledgebase.db from JSON
uv run --extra dev pytest tests/test_db_in_sync.py   # gate: committed DB == fresh seed
git add study_calc/learning/ study_calc/data/knowledgebase.db   # commit BOTH
```

`tests/test_db_in_sync.py` fails if you edit JSON and forget to reseed — that's
the guard against silently serving stale content. Ownership splits in two:

- **Content-only change** (new/edited topic, problem, glossary on the existing
  schema): `curriculum-author` edits JSON, runs the reseed, commits both. `sql-pro`
  is *Informed*.
- **Schema change** (new field, table, or content kind): `sql-pro` owns
  `study_calc/data/schema.sql` **and** the matching `scripts/seed_db.py` update in
  phase `04-implementation` (db section); `curriculum-author` is *Consulted*. Then
  the reseed runs.

Translations (es/fr/uk) are currently seeded `en`-only; a non-English seed path is
future work — note it, don't hand-edit the DB.

Rules of the bus:

- **Read before you write.** Each agent's prompt names the exact input artifacts.
- **No prose context in the dispatch.** Pass file paths, not pasted text.
- **A skipped phase is recorded,** not silent — note it in `02-plan.md`.
- **Gates live in the Dev Manager.** A phase advances only when its artifact
  proves the gate (green pytest incl. the i18n/references/learning/problems
  contract tests; review with no blockers).

## Lifecycle, stages & status transitions

A ticket's status is **derived from its issue + PR state** plus the
`docs/sdlc/<ticket>/` artifacts — that's what cold agents can actually read: no PR
yet → Implementation · PR open, not approved → in review · PR approved → QA · PR
merged → Release · issue closed → Done. The **GitHub Project board**
(`github.com/users/danilchernyshev/projects/1`) is a **human-facing view** that
mirrors these stages for the Dev Director — moving a card is a convenience, **not**
an authoritative signal (D24). The old `status:*` labels are **retired** (D24,
supersedes D15) — they duplicated state already derivable from the issue/PR.

**Stage → phases** (the stages are also the board-view columns):

| Stage | Phases | What happens here |
|--------|--------|-------------------|
| **Todo** | 00 brief · 01 requirements · 02 plan | intake, BA, dev-manager plan + sub-issue decomposition (D22) |
| **Implementation** | 03 design (frontend only) · 04 implementation · **review** | code + unit/contract tests in one PR (`Refs #N`); **`code-reviewer` reviews on the PR** (D21) — the review/fix loop stays in this column; reviewer **approval is the gate to QA** (D27) |
| **QA** | 05 tests · 07 docs | QA **initial** (pre-merge) test pass; **`technical-writer` writes the docs in the same PR**; `qa-expert` checks tests **and docs** for sign-off (D25) |
| **Release** | 08 release | post-merge **regression** on `master`; dev-manager + Dev Director go/no-go; devops executes (epic/milestone-level) |
| **Done** | — | QA closes the ticket |

**Code review lives inside Implementation** (no separate column — D27); it
**precedes QA**, and its approval is the Implementation→QA gate (cheap correctness
findings first; no point QA-ing code the reviewer will bounce). **Merge happens
between QA and Release** — once QA sign-off (tests **+** docs) is green (review was
already approved upstream), `dev-manager` merges; regression and Release run on
`master`. There is **no Docs column** (D25): docs are authored by `technical-writer`
during QA and are part of QA's gate.

### Status-transition gates (who advances each stage, and the action that does it)

A ticket advances only when that edge's gate is met. **R** = performs the advancing
action (opens the PR, approves, merges…); **A** = accountable. The board card is
updated to match — manually, for now (D24). The Dev Director overrides any row.

| Transition | R (advances) | A | Gate |
|------------|----------------|---|------|
| Todo → Implementation | dev-manager | dev-manager | `02-plan.md` done; sub-issues decomposed (standard/large) |
| *within Implementation: review/fix loop* | code-reviewer ⇄ developer | code-reviewer | reviewer requests changes → developer fixes & pushes → re-review |
| Implementation → QA | code-reviewer | code-reviewer | code done; unit/contract tests green; PR open `Refs #N`; **reviewer approved** (= comment, single-account caveat — D21); non-blocking findings filed as sub-issues |
| QA → Implementation *(bounce/fix)* | qa-expert | qa-expert | QA-initial defect in feature logic, or a docs gap, with a clear direct fix → FIX sub-issue, same owner |
| QA → Todo *(re-plan)* | qa-expert | **dev-manager** | QA judges the work needs re-planning / re-prioritization (not a direct fix — scope shift, ambiguity, design rethink) → dev-manager reviews, prioritizes what's next and who takes it |
| **QA → Release** *(merge)* | **dev-manager** | dev-manager | QA sign-off green (initial tests **+** docs); review already approved; no open blocker → dev-manager merges (D29) |
| Release → Done | devops (executes) | dev-manager **+ Dev Director** | regression on `master` green; go decision taken; release shipped → QA closes |

Only `dev-manager` performs the **merge** edge; only **QA** performs the **Done**
close (it raises a fix sub-issue / reopens if regression fails). Each role performs
only the transitions it owns above; the board view is then updated to match.

## Labels

Status is derived from issue/PR state (D24), so labels are **not** status. Two kinds:

- **`agent:*`** — scope: whose queue a ticket/sub-issue is in (extend to the active
  roster as needed).
- **kind** — the standard GitHub labels already in the repo: **`bug`**,
  **`enhancement`** (= improvement), `design`, `test`, `epic` (no parallel `type:*`
  namespace — D26).

Any of **QA, the developer, or the code-reviewer** may **flag** a defect/improvement
they spot in the work in flight (D26); the sub-issue is then **created by
`dev-manager`** (who holds issue-create — D30) with `bug`/`enhancement` + the right
`agent:*` scope:

- **QA** and the **developer** flag `bug`s for defects in the feature's changed logic;
- the **code-reviewer** flags one when a finding is better fixed in a **separate PR**
  and the current PR is self-sufficient (so it doesn't block the open PR).

Bugs in the changed feature attach to that feature/epic; broader improvements are
standalone backlog items. dev-manager owns the planning decomposition and creates the
sub-issues (D22/D30); the Dev Director owns new epics/milestones.

## GitHub actions RACI — who may change issues & PRs

Separate from the *phase* RACIs: this governs **mutations on GitHub** (who may open,
review, merge, close). **R** does it · **A** owns/authorises · **C** consulted ·
**I** informed · **✗** explicitly not allowed. The **Dev Director (Danil)** can
override any row.

| GitHub action | Dev Manager | developer | code-reviewer | QA | Dev Director |
|---------------|:-----------:|:---------:|:-------------:|:--:|:-----------:|
| Open a PR | I | **R** | I | I | I |
| Comment on a PR / issue | C | C | **R** | C | C |
| Request changes / "decline" a PR | A | I | **R** | C | I |
| Approve a PR | A | I | **R** | I | C |
| **Merge a PR** | **R/A** | ✗ never | C (approved upstream) | C (initial pass) | A (override) |
| Delegate extra / double reviewers | **R/A** | I | **requests it** | I | I |
| Decide if the review was sufficient | **R/A** | I | C | I | C |
| **Close an issue (done)** | C | I | I | **R/A** | A (override) |
| Reopen an issue | R | C | C | R | A |
| Update the board view (mirror issue/PR state) | R | R | R | R | A |
| Flag a `bug`/`enhancement` found in flight | C | **R** | **R** | **R** | I |
| **Create / label a sub-issue** | **R/A** (issue-create, D30) | I | I | I | A |
| Decompose into planning sub-issues | **R/A** | C | C | C | I |
| Create a new epic / milestone | R | C | C | C | **A** |

**Merge policy.** Only the **Dev Manager** merges (the QA→Release edge), and only
when *all* hold: (a) `code-reviewer` has **approved** (a comment, single-account
caveat — D21; the approval was the Implementation→QA gate), (b) the **QA initial
(pre-merge) sign-off** is green — tests **+** docs — plus the contract tests, (c) no
open blocker. **Developers never merge** — not even their own PR. Post-merge,
**regression** runs on `master` in the **Release** column before ship.

**Double-review delegation.** If a PR needs expertise beyond the `code-reviewer`'s
scope (e.g. security, architecture, a specific language/DB), the code-reviewer does
**not** recruit reviewers itself — it **asks the Dev Manager**, who either (a)
delegates specific specialist reviewers (`security-auditor`, `architect-reviewer`,
`sql-pro`, a language specialist…) or (b) judges the existing review sufficient and
proceeds. That call is the Dev Manager's.

**Close policy.** Only **QA** closes a ticket, after verifying it's genuinely done
(release shipped + post-merge regression green). Everyone else proposes closing; QA
(or the Dev Director) acts.

> **Note — policy vs enforcement.** This is the agreed *policy*; GitHub doesn't
> enforce it yet. Branch-protection rules (require review approval, block direct
> merges) could enforce "developers can't merge" technically — that's a repo-settings
> change, deferred as an open question (see `ai-sdlc/ROADMAP.md` Q6).
