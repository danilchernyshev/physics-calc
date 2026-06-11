# Authoring learning content

The calculator's study material — topics, glossary concepts, and practice
problems — is authored as JSON under [`study_calc/learning/`](../study_calc/learning/)
but **served at runtime from the SQLite knowledgebase**
(`study_calc/data/knowledgebase.db`), seeded from those JSON files by
[`scripts/seed_db.py`](../scripts/seed_db.py). This split (see
[ADR 0002](adr/0002-knowledgebase-db.md)) keeps authoring in readable, diffable,
per-item files while the app reads from one fast, indexed, read-only artifact.

The practical consequence: **the committed DB — not the JSON — is what the app
and the tests read.** Editing a JSON file without re-seeding changes nothing the
loaders see. The workflow below is therefore: edit JSON → seed → test → verify.

## The loop

```
add/edit JSON  →  python scripts/seed_db.py  →  pytest  →  verify in the UI
```

### 1. Add or edit the JSON

Pick the content type and write the file under the **English** tree (`en` is
canonical and the fallback for every other language):

| Type    | Path                                  | Id (= file stem) is…                          |
| ------- | ------------------------------------- | --------------------------------------------- |
| Topic   | `study_calc/learning/en/topics/<id>.json`   | a formula `key`, a `cas_<op>`, or a `chem_*`/`mdm_*`/`sph_*` id |
| Concept | `study_calc/learning/en/glossary/<id>.json` | a reusable glossary term id                   |
| Problem | `study_calc/learning/en/problems/<id>.json` | a practice-problem id                         |

The full schema for each type — required and optional fields — is documented in
[`study_calc/learning/README.md`](../study_calc/learning/README.md). Two rules
matter most:

- **Stable keys never change.** A file's stem is its database primary key and is
  referenced by other content (a problem's `topic`, a topic's `terms`, a
  concept's `see_also`). Renaming an id breaks those links. Edit in place; only
  *add* new ids.
- **Cross-references must resolve.** A topic's `terms[]` and a concept's
  `see_also[]` must point at existing glossary files; a problem's `topic` must
  point at an existing topic file. The tests below enforce all three.

A translation is purely additive: drop a `study_calc/learning/<lang>/<type>/<id>.json`
mirroring the English file. Anything missing in `<lang>` falls back to `en`.

### 2. Re-seed the database

```bash
python scripts/seed_db.py
```

This repopulates every content table from the JSON sources (each row via
`INSERT OR REPLACE`, keyed on the stable id) and writes
`study_calc/data/knowledgebase.db`. The seeder is **idempotent** — running it
twice yields identical rows. **Commit the regenerated `knowledgebase.db`** along
with your JSON changes; it is a checked-in artifact.

> Because rows are replaced by id rather than the tables being dropped, *deleting*
> a JSON file leaves its stale row behind in an in-place re-seed. To remove
> content cleanly, seed a fresh DB (delete `knowledgebase.db` first, or seed to a
> new `--db` path and swap it in); `test_db_in_sync.py` always compares against a
> from-scratch seed, so it will catch the leftover.

To seed a throwaway DB instead (e.g. to inspect it) pass `--db`:

```bash
python scripts/seed_db.py --db /tmp/scratch.db
```

### 3. Run the tests

```bash
uv run --extra dev pytest tests/test_learning.py tests/test_problems.py tests/test_db_seed.py tests/test_db_in_sync.py -v
```

then the full suite:

```bash
uv run --extra dev pytest
```

What these guard:

- **`test_db_in_sync.py`** — the committed `knowledgebase.db` matches a fresh
  seed of the current JSON, row for row. *This is the test that fails when you
  forget to re-seed.* Fix: run `python scripts/seed_db.py` and commit the DB.
- **`test_db_seed.py`** — schema correctness, row counts, the stable-key contract
  (every JSON stem appears as an id in the DB), seeding idempotency, and
  **foreign-key integrity** (every problem's non-empty `topic` resolves to a real
  English topic).
- **`test_learning.py` / `test_problems.py`** — content integrity through the
  loaders (every referenced term resolves, no dangling `see_also`, every problem
  is complete and tagged with a known subject). These run against a fresh,
  session-scoped temporary DB seeded by `tests/conftest.py`, so they validate the
  *content* rather than depending on whoever last ran the seeder.

The test suite never touches your default DB: `conftest.py` seeds a temp file and
points `STUDY_CALC_DB` at it for the session, and the seeder tests use their own
temp DBs.

### 4. Verify in the UI

```bash
uv run study-calc-web
```

Open the relevant surface and confirm it renders:

- a **topic** shows on the matching formula / CAS / chemistry screen (theory,
  useful formulas, method, key terms, worked example);
- a **concept** shows inline beside a term, with "Open full explanation →"
  opening the pop-up;
- a **problem** shows in the Problems list for its `subject`, with its worked
  solution, grade badge (from `courses`), and any `video_url` link.

## The `difficulty` placeholder

The `problems` table carries a `difficulty` column that is **not authored yet**:
it defaults to the empty string `""` and is left out of the problem JSON. A later
milestone (**M3-1**) introduces difficulty tiers and populates this column; until
then, do not add a `difficulty` field to problem files.
