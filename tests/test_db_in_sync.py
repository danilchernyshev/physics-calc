"""Guard: the committed knowledgebase.db must match a fresh seed from JSON.

``core/learning.py`` now serves all learning content from the committed
``study_calc/data/knowledgebase.db`` at runtime.  That artifact is reproducible
from the ``study_calc/learning/`` JSON sources via ``scripts/seed_db.py`` — but
nothing stops an author editing a JSON file and forgetting to re-seed, which
would silently serve stale content to the app (and to every other test that
reads through the loaders).

This test re-seeds a throwaway database from the current JSON sources and
asserts every table matches the committed DB row-for-row.  If it fails, run::

    python scripts/seed_db.py

and commit the regenerated ``knowledgebase.db``.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
import tempfile

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import seed_db  # noqa: E402  (inserted after sys.path manipulation)

LEARNING_EN = _REPO_ROOT / "study_calc" / "learning" / "en"
DATA_DIR = _REPO_ROOT / "study_calc" / "data"
COMMITTED_DB = DATA_DIR / "knowledgebase.db"

_TABLES = ("topics", "topic_terms", "topic_examples", "concepts", "problems", "elements")


def _seed_fresh() -> pathlib.Path:
    """Seed a fresh temporary DB from the current JSON sources; return its path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = pathlib.Path(f.name)
    conn = sqlite3.connect(db_path)
    try:
        seed_db._apply_schema(conn, DATA_DIR / "schema.sql")
        seed_db.seed_topics(conn, LEARNING_EN / "topics")
        seed_db.seed_concepts(conn, LEARNING_EN / "glossary")
        seed_db.seed_problems(conn, LEARNING_EN / "problems")
        seed_db.seed_elements(conn, DATA_DIR / "elements.json")
    finally:
        conn.close()
    return db_path


def _dump(db_path: pathlib.Path, table: str) -> list[tuple]:
    """Return every row of *table* as a sorted list of value tuples."""
    conn = sqlite3.connect(db_path)
    try:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        rows = conn.execute(
            f"SELECT {', '.join(cols)} FROM {table}"
        ).fetchall()
    finally:
        conn.close()
    return sorted(rows)


@pytest.mark.skipif(not COMMITTED_DB.exists(), reason="committed knowledgebase.db absent")
def test_committed_db_matches_fresh_seed():
    """Every table in the committed DB equals a fresh seed from the JSON sources."""
    fresh = _seed_fresh()
    try:
        for table in _TABLES:
            committed_rows = _dump(COMMITTED_DB, table)
            fresh_rows = _dump(fresh, table)
            assert committed_rows == fresh_rows, (
                f"table {table!r} in the committed knowledgebase.db is out of sync "
                f"with the JSON sources ({len(committed_rows)} vs {len(fresh_rows)} "
                "rows, or differing content). Re-run `python scripts/seed_db.py` "
                "and commit the regenerated DB."
            )
    finally:
        fresh.unlink(missing_ok=True)
