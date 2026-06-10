-- study_calc knowledgebase schema
-- Matches ADR 0002-knowledgebase-db.md
-- All list-typed fields are stored as JSON-encoded strings.
-- Canonical rows have language = 'en'; translated rows override prose fields
-- for the same (id, language) pair.  Callers fall back to 'en' when the
-- requested language row is absent.

-- The shipped knowledgebase.db is a read-only content artifact committed to the
-- repo and installed into a possibly read-only location (Program Files, a
-- PyInstaller bundle).  WAL mode is deliberately NOT set: it persists in the file
-- header and forces the engine to create -wal/-shm sidecars next to the DB on
-- open, which fails when the directory is read-only.  The default rollback
-- journal opens cleanly read-only.  A future writer (e.g. FTS indexing) can opt
-- into WAL per-connection at runtime instead.
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- topics
-- One row per (topic_id, language).  topic_id is a formula key or CAS op name.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topics (
    topic_id      TEXT NOT NULL,
    language      TEXT NOT NULL DEFAULT 'en',
    summary       TEXT NOT NULL DEFAULT '',
    formulas_json TEXT NOT NULL DEFAULT '[]',
    method_json   TEXT NOT NULL DEFAULT '[]',
    courses_json  TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (topic_id, language)
);

-- ---------------------------------------------------------------------------
-- topic_terms
-- Normalised join table for the ordered list of glossary term ids per topic.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topic_terms (
    topic_id TEXT    NOT NULL,
    language TEXT    NOT NULL DEFAULT 'en',
    term_id  TEXT    NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (topic_id, language, term_id)
);

-- ---------------------------------------------------------------------------
-- topic_examples
-- The single worked example embedded in each topic file.
-- Topics without an 'example' key produce no row here.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topic_examples (
    topic_id   TEXT NOT NULL,
    language   TEXT NOT NULL DEFAULT 'en',
    title      TEXT NOT NULL DEFAULT '',
    given_json TEXT NOT NULL DEFAULT '[]',
    find       TEXT NOT NULL DEFAULT '',
    steps_json TEXT NOT NULL DEFAULT '[]',
    answer     TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (topic_id, language)
);

-- ---------------------------------------------------------------------------
-- concepts
-- One row per (term_id, language).  term_id is the glossary file stem.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS concepts (
    term_id       TEXT NOT NULL,
    language      TEXT NOT NULL DEFAULT 'en',
    title         TEXT NOT NULL DEFAULT '',
    short         TEXT NOT NULL DEFAULT '',
    full          TEXT NOT NULL DEFAULT '',
    formulas_json TEXT NOT NULL DEFAULT '[]',
    see_also_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (term_id, language)
);

-- ---------------------------------------------------------------------------
-- problems
-- One row per problem_id (the JSON file stem).  All problems are currently
-- English-only; the language column is present for future translations.
-- difficulty is a placeholder populated by M3-1.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS problems (
    problem_id   TEXT NOT NULL PRIMARY KEY,
    language     TEXT NOT NULL DEFAULT 'en',
    subject      TEXT NOT NULL DEFAULT '',
    title        TEXT NOT NULL DEFAULT '',
    given_json   TEXT NOT NULL DEFAULT '[]',
    find         TEXT NOT NULL DEFAULT '',
    steps_json   TEXT NOT NULL DEFAULT '[]',
    answer       TEXT NOT NULL DEFAULT '',
    video_url    TEXT NOT NULL DEFAULT '',
    topic_id     TEXT NOT NULL DEFAULT '',
    courses_json TEXT NOT NULL DEFAULT '[]',
    difficulty   TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- elements
-- Periodic table loaded from study_calc/data/elements.json.
-- JSON field 'mass' maps to atomic_mass; 'group' maps to group_id (nullable
-- because lanthanides/actinides carry no main-group number).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS elements (
    number      INTEGER NOT NULL PRIMARY KEY,
    symbol      TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    atomic_mass REAL    NOT NULL,
    group_id    INTEGER,
    period      INTEGER NOT NULL,
    category    TEXT    NOT NULL DEFAULT '',
    xpos        INTEGER NOT NULL,
    ypos        INTEGER NOT NULL
);
