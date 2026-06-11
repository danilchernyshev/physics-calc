# 173 — Curriculum filter hides the whole Problems tab instead of filtering its contents

- **Ask:** Fix `web/bridge.py::item_visible` so that selecting a course **keeps** the
  Problems nav item visible and narrows the *list of problems inside it* (with an
  empty / no-results state when none match), instead of dropping the whole nav entry.
  **Decide & document** (open design question) whether the same "keep the item, filter
  its contents" rule should also apply to formula `Section`s, or only to `Problems`.
- **Source:** GitHub issue #173 (epic #102; related #123). Found in the live UX gate
  for #123. Labels: `bug`, `area:filter`. **Analysis ticket**, not a UI nit.
- **Root cause (grounded in the issue):** `item_visible` (≈ line 80) treats a
  `Problems` item like a tagged `Section` — unions the subject's problem courses and
  drops the item when the active course isn't in the set. Shipped in #122/#124
  (backend), only made user-reachable by #123.
- **Touches frontend?** partial — the fix is in `web/bridge.py` (Python view-model);
  the **Problems screen** likely needs an empty/no-results state in `frontend/`.
- **Touches engine (core/ or domains/)?** no core/domains; **yes `web/bridge.py`**
  (navigation/visibility model). The design question is a **cross-layer semantics**
  call → ADR.
- **New formula / unit / error code?** no (check for any new i18n key for the
  empty-state copy).
- **Dependency / ordering (EP-7):** #173 lands **first**; #175 (scalar→set multi-select)
  rebases on it. **One ADR** (`architect-reviewer`) covers *both* `item_visible`
  changes — design the semantics once.

> Second live run of the board-model SDLC (after #175's plan-only trial). Hand this
> folder to the `dev-manager` agent to produce `02-plan.md`.
