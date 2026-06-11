# <ticket> — tests + docs  ·  QA lead: qa-expert  ·  executors: test-automator, ui-ux-tester, accessibility-tester  ·  docs: technical-writer

> This is the **QA column** (D24): the initial **pre-merge** test pass **plus** the
> docs (authored by `technical-writer` in the same PR — D25). `qa-expert` signs off
> tests **and** docs; that sign-off + the upstream review approval gate the
> **QA→Release merge**. Post-merge **regression** runs later, in the Release column.

## QA plan & strategy  (qa-expert — A/R)
- Risk areas / what must be covered:
- Out of scope for testing:
- Which executions apply: unit ☐ · integration ☐ · UI/E2E ☐ · visual ☐ · a11y ☐
- Headless-coverage gap? → file a **human-verification sub-issue** (D23): ☐ n/a ☐ filed #__

## Unit / integration  (test-automator — R)
- [ ] new behavior fails without the change, passes with it
- [ ] `uv run --extra dev pytest` green
- [ ] contract tests green: test_i18n · test_references · test_learning · test_problems

## UI / functional / visual  (ui-ux-tester — R; only if frontend touched)
- [ ] user flows pass; screens render; touched node re-renders correctly
- [ ] no visual regression on affected screens

## Accessibility  (accessibility-tester — R; only if frontend touched)
- [ ] keyboard nav · contrast · ARIA roles · screen-reader

## Docs  (technical-writer — R; qa-expert checks — A)  ← authored during QA, in the same PR (D25)
- [ ] README / user-facing docs updated for the change
- [ ] CLAUDE.md / locale notes updated where the change affects them
- [ ] CHANGELOG / release-note line drafted (for the Release column)
- [ ] qa-expert reviewed the docs (a docs gap is a sign-off blocker)
- See `07-docs.md` for the detail.

## Results
<paste pytest summary / findings per executor>

## Defect triage  (qa-expert — A/R)
| Defect | Severity | Owner | Status |
|--------|----------|-------|--------|
| | | | |

## Quality sign-off  (qa-expert — A/R)  ← QA gate (tests + docs)
- [ ] all applicable executions green, no open blocker defect
- [ ] docs checked
- [ ] → gate PASS (with the upstream review approval, this opens the QA→Release merge)
