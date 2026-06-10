# 2. Knowledgebase database technology and schema

- **Status:** Accepted
- **Date:** 2026-06-10
- **Deciders:** study-calc maintainers
- **Issue:** [#28 — Knowledgebase: DB technology spike and schema design](https://github.com/danilchernyshev/study-calc/issues/28)
- **Milestone:** M2 — Knowledgebase

## Context

`study_calc/core/learning.py` loads study content from flat JSON files under
`study_calc/learning/<lang>/` using `lru_cache`d file reads. This works while
the data set is small and each loader reads exactly one file per call.  As the
knowledgebase grows the model shows three limits:

1. **Non-queryable** — filtering problems by subject, course code, or
   difficulty requires loading all files and filtering in Python.
2. **No cross-content joins** — e.g. "all problems that reference term X"
   requires iterating every file.
3. **File-system coupling** — paths are baked into `load_topic` / `load_concept`
   / `load_problem`; the loader cannot be swapped without touching callers.
4. **No full-text search** — a future "search across all topics" feature would
   be impractical on flat files.

Before migrating data or rewriting loaders, the schema decision must be
documented so all downstream tickets build on a single agreed model.

## Decision drivers

1. **Zero new runtime dependencies** — the project currently uses only stdlib
   plus `sympy`; adding a DB client package would widen the install footprint.
2. **Single-file portability** — the app ships as a Windows installer and must
   also run on macOS and Linux; a file-based DB avoids a server dependency.
3. **Frozen-bundle compatibility** — PyInstaller/cx_Freeze builds must be able
   to carry the database.
4. **SQL expressiveness** — future queries (filtering, FTS, joins) should use
   standard SQL without an ORM overhead.
5. **Preserve i18n fallback semantics** — the current file-fallback (query
   requested language, fall back to `'en'`) must survive intact.

## Decision

**Use SQLite via the stdlib `sqlite3` module.**

### Why SQLite

- `sqlite3` ships with every CPython ≥ 3.10 on all platforms; no `pip install`
  needed.
- A single `.db` file can be committed to the repo alongside the JSON content
  or regenerated from it, making the artifact portable and diff-friendly.
- SQLite databases are fully supported inside PyInstaller-frozen bundles (the
  file is extracted to a temp directory or accessed from the bundle's data
  path).
- SQLite's WAL mode and full-text-search extension (`FTS5`) provide an upgrade
  path for search without switching engines.
- Every downstream ticket that queries content speaks plain SQL; no ORM is
  needed at this scale.

### DB file location and commit policy

`study_calc/data/knowledgebase.db` — **committed to the repository** after
each seeding run.  Rationale: the DB is fully reproducible from the JSON
sources via `scripts/seed_db.py`, but committing it means a fresh checkout
already has a working DB without requiring the seeding step.  `knowledgebase.db`
is added to the repository and updated whenever the JSON content changes.  To
regenerate from scratch:

```bash
python scripts/seed_db.py --db study_calc/data/knowledgebase.db
```

## Schema design

All tables use explicit `TEXT` / `INTEGER` / `REAL` types.  List-typed fields
(`formulas`, `method`, `steps`, `given`, `see_also`, `courses`) are stored as
JSON-encoded strings so no pivot tables are needed for ordered arrays of
plain scalars.  The `topic_terms` join table preserves the ordered list of
glossary term ids referenced by a topic.  The `topic_examples` table stores the
single worked example that each topic carries.

### `topics`

```sql
CREATE TABLE topics (
    topic_id     TEXT NOT NULL,
    language     TEXT NOT NULL DEFAULT 'en',
    summary      TEXT NOT NULL DEFAULT '',
    formulas_json TEXT NOT NULL DEFAULT '[]',
    method_json  TEXT NOT NULL DEFAULT '[]',
    courses_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (topic_id, language)
);
```

`topic_id` is a formula key (e.g. `newton_2`, `kinetic_energy`) or a CAS
operation name (`cas_factor`, `cas_derivative`, …).  The `courses_json` column
holds an ordered JSON array of Ontario course codes (e.g. `["SPH4U", "MHF4U"]`).

### `topic_terms`

```sql
CREATE TABLE topic_terms (
    topic_id  TEXT NOT NULL,
    language  TEXT NOT NULL DEFAULT 'en',
    term_id   TEXT NOT NULL,
    position  INTEGER NOT NULL,
    PRIMARY KEY (topic_id, language, term_id)
);
```

Normalises the `terms` array from each topic JSON file.  `position` is the
0-based index within the array so callers can reconstruct the original order.

### `topic_examples`

```sql
CREATE TABLE topic_examples (
    topic_id   TEXT NOT NULL,
    language   TEXT NOT NULL DEFAULT 'en',
    title      TEXT NOT NULL DEFAULT '',
    given_json TEXT NOT NULL DEFAULT '[]',
    find       TEXT NOT NULL DEFAULT '',
    steps_json TEXT NOT NULL DEFAULT '[]',
    answer     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (topic_id, language)
);
```

One row per `(topic_id, language)`, holding the worked example embedded in each
topic file.  Topics without an `example` key produce no row.

### `concepts`

```sql
CREATE TABLE concepts (
    term_id      TEXT NOT NULL,
    language     TEXT NOT NULL DEFAULT 'en',
    title        TEXT NOT NULL DEFAULT '',
    short        TEXT NOT NULL DEFAULT '',
    full         TEXT NOT NULL DEFAULT '',
    formulas_json TEXT NOT NULL DEFAULT '[]',
    see_also_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (term_id, language)
);
```

Corresponds to `study_calc/learning/<lang>/glossary/<term_id>.json`.

### `problems`

```sql
CREATE TABLE problems (
    problem_id  TEXT NOT NULL PRIMARY KEY,
    language    TEXT NOT NULL DEFAULT 'en',
    subject     TEXT NOT NULL DEFAULT '',
    title       TEXT NOT NULL DEFAULT '',
    given_json  TEXT NOT NULL DEFAULT '[]',
    find        TEXT NOT NULL DEFAULT '',
    steps_json  TEXT NOT NULL DEFAULT '[]',
    answer      TEXT NOT NULL DEFAULT '',
    video_url   TEXT NOT NULL DEFAULT '',
    topic_id    TEXT NOT NULL DEFAULT '',
    courses_json TEXT NOT NULL DEFAULT '[]',
    difficulty  TEXT NOT NULL DEFAULT ''
);
```

`problem_id` is the JSON file stem (e.g. `sph_kinetic_energy`).  The
`difficulty` column is a **placeholder for milestone M3-1** — it is seeded as
an empty string and updated later when a difficulty-rating feature is
implemented.

### `elements`

```sql
CREATE TABLE elements (
    number      INTEGER NOT NULL PRIMARY KEY,
    symbol      TEXT NOT NULL,
    name        TEXT NOT NULL,
    atomic_mass REAL NOT NULL,
    group_id    INTEGER,
    period      INTEGER NOT NULL,
    category    TEXT NOT NULL DEFAULT '',
    xpos        INTEGER NOT NULL,
    ypos        INTEGER NOT NULL
);
```

Loaded from `study_calc/data/elements.json`.  The JSON field `mass` maps to
`atomic_mass`; `group` maps to `group_id` (nullable because lanthanides and
actinides have no main-group number in some periodic-table conventions).

## i18n row model

The DB mirrors the current file-fallback strategy exactly:

- **Canonical rows** have `language = 'en'`.  They are always present.
- **Translated rows** carry the same `topic_id` / `term_id` / `problem_id` and
  a different `language` value; they override the prose fields for that
  language.
- **Query pattern:** request the row for the target language; if no row exists,
  fall back to `language = 'en'`.  In SQL:

```sql
SELECT * FROM concepts
WHERE term_id = ?
  AND language = COALESCE(
        (SELECT language FROM concepts WHERE term_id = ? AND language = ?),
        'en'
      );
```

  Or equivalently, order by `language = 'en'` ascending and take the first
  matching row with `language IN (?, 'en') ORDER BY language = 'en' LIMIT 1`.

This preserves the existing semantics: a partial translation never leaves the
panel blank; English is always the ultimate fallback.

## Stable-key contract

`topic_id`, `term_id`, and `problem_id` values are **immutable across
migrations**.  They are derived from the JSON file names (formula keys / CAS
operation names / file stems) which are themselves part of the public i18n key
contract (`theory.<topic_id>`, `var.<name>`).  Any rename would break existing
locale files, cross-references in `domains/references.py`, and any external
links.  New content must use new ids; existing ids must never be changed.

## Consequences

**Positive**

- Single-file portability; no server process; no new runtime dependency.
- All five content domains in one query-able store — enables filtering,
  joining, and future FTS without changing callers in `core/`.
- The `difficulty` placeholder column aligns M2-2 DDL with M3-1 rating feature
  from the start.
- Idempotent seeding via `INSERT OR REPLACE` keeps the DB regenerable from
  JSON at any time.

**Negative / risks**

- The `.db` file is binary; diffs in pull requests show only size changes, not
  content changes.  Content reviews must inspect the JSON sources instead.
- SQLite's single-writer model is sufficient for a desktop app but would need
  re-evaluation if the project ever moved to a multi-user web service.

**Neutral**

- `core/learning.py` and `core/periodic.py` remain JSON-based in M2-2; they
  are rewritten to query the DB in M2-3.  No callers change in this milestone.

## Constraints imposed on downstream issues

- **M2-2 (DDL + seeding):** use `study_calc/data/schema.sql` as the
  authoritative DDL; run `scripts/seed_db.py` to populate.  Output DB at
  `study_calc/data/knowledgebase.db`.
- **M2-3 (loader rewrite):** replace file reads in `load_topic` /
  `load_concept` / `load_problem` with `sqlite3` queries on the committed DB;
  apply the two-step language fallback query shown above.
- **M3-1 (difficulty rating):** populate `problems.difficulty` via an `UPDATE`
  statement; the column already exists with an empty-string default.
