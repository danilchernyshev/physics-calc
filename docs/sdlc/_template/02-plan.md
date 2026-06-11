# <ticket> — plan  ·  owner: dev-manager + project-manager

## Ticket weight
- [ ] trivial — typo / one string / doc tweak → impl + PR review only
- [ ] standard — one feature/formula/bugfix → 01 · 02 · 04 · review(PR) · 05 QA · 07 docs (+03 design if frontend)
- [ ] large — new section / cross-layer / schema / content drop → full track
- Justification: <why this weight; i18n-contract or learning+DB ⇒ ≥ standard; schema/new section ⇒ large>

## Stage → phases (mark applied / skipped)
Status is **derived from issue/PR state**; the board just mirrors these stages (D24):
Todo → Implementation → QA → *(merge)* → Release → Done.

| Column | # | Phase | Apply? | Agent | Why / why skipped |
|--------|---|-------|--------|-------|-------------------|
| Todo | 0 | BA | yes | business-analyst | |
| Todo | 1 | Plan + sub-issue decomposition (D22) | yes | dev-manager | |
| Implementation | 2 | Design | ? | ui-designer | skip if no UI change |
| Implementation | 3 | Core impl | ? | python-pro | |
| Implementation | 3b| Frontend impl | ? | frontend-developer | |
| Implementation | 5 | Review **on the PR** (D21/D27) | yes | code-reviewer | approval gates → QA |
| QA | 4 | Unit/contract tests | yes | test-automator | dev writes them in-phase |
| QA | 4b| Visual/UI/a11y | ? | ui-ux-tester | only if frontend touched |
| QA | 6 | Docs (same PR, D25) | ? | technical-writer | checked by qa-expert |
| QA | — | QA sign-off (gate) | yes | qa-expert | tests **+** docs |
| Release | 7 | Release (regression + go/no-go) | ? | deployment-engineer / devops | epic/milestone-level |

## Dependency order
<what runs in parallel vs. what blocks what>

## Dispatch plan
1. main thread → invoke <agent> · in: <artifacts> · out: <artifact> · gate: <condition>
2. ...
