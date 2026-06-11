# 173 — Problems-tab filter — documentation  ·  owner: technical-writer

**Summary:** No user-facing documentation change is warranted. The fix is a pure backend defect correction with comprehensive architectural documentation already in place (ADR 0003).

## Doc impact assessment

### README.md
**No change needed.** The curriculum filter feature is mentioned incidentally (the Ontario course badges exist, the filter persists across subjects), but the filter's **behavior** — how it affects each surface — was never documented in the main user guide. This is appropriate: the README documents *features*, not UI details; a bug fix that corrects internal broken behavior doesn't warrant a user-doc change.

### User-facing strings & i18n
**No change needed.** The fix reuses two existing i18n keys (`ui.filter.no_results` + `ui.filter.no_results_detail`) already present in all five locales. No new strings were introduced. The i18n contract is intact; `test_i18n` passes unchanged.

### Architectural documentation
**Complete.** ADR 0003 ("Curriculum-filter visibility semantics for `item_visible`") comprehensively documents:
- The problem (§Context): Problems tab disappears on course mismatch
- The decision: Problems items stay visible + filter contents; Sections remain drop-on-mismatch
- The principle: "collection vs tool" — `Problems` is a content list the filter narrows; `Section` is a calculator tool
- Forward compatibility with #175 (scalar → set multi-select)
- Why no `formula_screen` change is needed (out of scope, separate decision if it ever changes)

The ADR is checked into the codebase (`docs/adr/0003-curriculum-filter-visibility.md`) and will live in the repo history.

### Release notes
**Implicit in commit message.** The PR title and commit message ("fix(#173): Problems tab stays visible; curriculum filter narrows its contents") serve as the release note. When version 0.8.2 (or the next release) is tagged, GitHub's auto-generated release notes will include this commit message as part of the release description. No separate changelog file is maintained (verified: no `CHANGELOG.md` in the root; recent commit `1c0f0ce` synced README + AppStream with feature set, not a separate changelog).

## Scope detail

**What was touched:**
- `study_calc/web/bridge.py` — `item_visible()` short-circuits `Problems` to always True
- `study_calc/web/screens.py` — `problems_screen()` filters by active course; empty-state key selection
- `tests/test_web_shell.py` — regression test + inverted assertions (6 assertions across 4 tests corrected with `# BUG #173 FIX:` comments)

**What was NOT touched:**
- `core/` or `domains/` — no formula/unit/error code changes
- `study_calc/locales/` — no new i18n key; no locale JSON updates
- `pyproject.toml` or schema — no version bump, no DB change
- `README.md` — the filter behavior is not documented there; no user-facing feature changed, only an internal defect fixed

## Process notes

The bug was latent in #122/#124 (backend), made user-reachable by #123 (filter UI). Because the filter applied to Problems incorrectly (hiding the whole tab), the feature was arguably not working, so no prior user-doc exists to update. The fix **enables the intended behavior**, bringing the code into line with the #123 brief ("filter applies to the problems displayed").

## QA docs checklist

- [x] No README.md change needed — verified filter behavior not documented there
- [x] No new i18n key introduced — verified both empty-state keys exist in all five locales
- [x] ADR complete and checked in — ADR 0003, comprehensive, covers both #173 + #175
- [x] Commit message sufficient for release notes — "fix(#173): ..." is clear
- [x] Test assertions inverted with clear comments — all 6 corrected with `# BUG #173 FIX:` lines
- [x] Contract tests unchanged — `test_i18n`, `test_references`, `test_learning`, `test_problems` all pass
- [x] No scope creep — web layer only, no formula/learning-content changes
