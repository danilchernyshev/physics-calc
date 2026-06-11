# <ticket> — docs  ·  author: technical-writer  ·  checked by: qa-expert

> Docs are written **during QA**, in the **same PR** as the change (D25) — there is
> **no separate Docs column**. `qa-expert` checks this as part of the QA sign-off, so
> a docs gap blocks the QA→Release merge like any other defect.

## What changed
- [ ] README / user-facing docs
- [ ] CLAUDE.md / architecture notes (only if the change affects them)
- [ ] locale notes (new i18n keys / error codes documented where relevant)
- [ ] CHANGELOG / release-note line (consumed in the Release column)

## Links
<paths to the docs edited; anything the reviewer or QA should know>

## QA docs check  (qa-expert)
- [ ] docs match the shipped behavior, no gap → part of sign-off PASS
