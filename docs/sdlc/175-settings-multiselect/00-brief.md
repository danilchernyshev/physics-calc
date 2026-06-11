# 175 — Settings-overlay filter: default All/All + multi-select (checkboxes)

- **Ask:** In the Settings overlay, (1) default the curriculum filter to Grade = All,
  Course = All; (2) replace the single-select course control with **checkboxes** so a
  user can pick several courses at once — changing the filter model from one active
  course to a **set** of active courses (`item_visible` + the persisted setting move
  from a scalar to a set).
- **Source:** GitHub issue #175 (epic #102; related #123, #173). Found in the live UX
  gate for #123. Labels: `enhancement`, `design`, `area:filter`.
- **Touches frontend?** **yes** — Settings-overlay controls (checkboxes), header mirror.
- **Touches engine (core/ or domains/)?** no core/domains; **yes `web/bridge.py`** —
  the filter model becomes scalar → set (`item_visible`, persisted setting). A
  **cross-layer model change** → route through `architect-reviewer` before impl.
- **New formula / unit / error code?** no (but check for any new i18n label keys for
  the multi-select UI).
- **Dependency:** issue #175 says *coordinate with #173 (filter-scope analysis) before
  implementing* — the scalar→set change overlaps #173's `item_visible` fix. dev-manager
  must resolve the order in `02-plan.md` (pre-flight the real `bridge.py` first — D19).

> First trial of the **board-model SDLC** (D24–D29): Todo → Implementation (incl. review
> on the PR) → QA (tests + docs) → merge → Release → Done. Hand this folder to the
> `dev-manager` agent to produce `02-plan.md`.
