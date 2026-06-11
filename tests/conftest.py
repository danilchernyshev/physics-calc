"""Shared pytest fixtures for the study_calc test suite.

The learning content now lives in the SQLite knowledgebase
(``study_calc/data/knowledgebase.db``), served by ``study_calc/core/db.py`` and
the loaders in ``study_calc/core/learning.py``.  The committed DB is kept in sync
with the JSON sources by ``tests/test_db_in_sync.py`` — but the rest of the suite
should not silently depend on whoever last ran the seeder.  This module seeds a
fresh database from the current JSON sources once per session and points
``STUDY_CALC_DB`` at it, so ``test_learning.py`` / ``test_problems.py`` (and any
other test that reads through the loaders) validate the *content*, not a possibly
stale committed artifact.

A temporary **file** DB is used rather than the literal ``:memory:`` the issue
suggests: ``db.get_connection`` caches a connection per thread (the web bridge
runs on a PyWebView worker thread), and each ``:memory:`` connection is a
*separate* empty database — a file path is shared safely across threads while
still giving the session its own isolated DB.
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

_LEARNING_EN = _REPO_ROOT / "study_calc" / "learning" / "en"
_DATA_DIR = _REPO_ROOT / "study_calc" / "data"


def _seed_fresh_db(db_path: pathlib.Path) -> None:
    """Seed *db_path* from the current JSON sources (same path as the seeder)."""
    conn = sqlite3.connect(db_path)
    try:
        seed_db._apply_schema(conn, _DATA_DIR / "schema.sql")
        seed_db.seed_topics(conn, _LEARNING_EN / "topics")
        seed_db.seed_concepts(conn, _LEARNING_EN / "glossary")
        seed_db.seed_problems(conn, _LEARNING_EN / "problems")
        seed_db.seed_elements(conn, _DATA_DIR / "elements.json")
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _fresh_knowledgebase(tmp_path_factory: pytest.TempPathFactory):
    """Point ``STUDY_CALC_DB`` at a freshly-seeded temp DB for the whole session.

    Loaders cache on ``(item_id, language)`` rather than the DB path, so the
    three ``lru_cache``-decorated loaders are cleared on entry and exit to keep a
    run that touched the default DB (during collection/import) from leaking rows.
    """
    from study_calc.core import learning

    db_dir = tmp_path_factory.mktemp("knowledgebase")
    db_path = db_dir / "test_knowledgebase.db"
    _seed_fresh_db(db_path)

    learning.load_topic.cache_clear()
    learning.load_concept.cache_clear()
    learning.load_problem.cache_clear()

    import os

    previous = os.environ.get("STUDY_CALC_DB")
    os.environ["STUDY_CALC_DB"] = str(db_path)
    try:
        yield db_path
    finally:
        if previous is None:
            os.environ.pop("STUDY_CALC_DB", None)
        else:
            os.environ["STUDY_CALC_DB"] = previous
        learning.load_topic.cache_clear()
        learning.load_concept.cache_clear()
        learning.load_problem.cache_clear()
