"""Thin SQLite connection helper for the study_calc knowledgebase.

The knowledgebase is a read-only content artifact committed to the repository at
``study_calc/data/knowledgebase.db``.  The path can be overridden with the
``STUDY_CALC_DB`` environment variable, which is useful for tests that want to
point at an isolated temporary database.

Connection caching
------------------
:func:`get_connection` reads the current ``STUDY_CALC_DB`` value on every call
and delegates to :func:`_open`, which is ``lru_cache``-keyed on the *resolved*
absolute path string.  That means:

* Repeated calls with the same effective path re-use the same
  :class:`sqlite3.Connection` (no reconnection overhead).
* Changing ``STUDY_CALC_DB`` between calls transparently opens a *new*
  connection for the new path while keeping the old one in cache (important for
  tests that swap the database between fixture setup and teardown).

Note for tests that combine ``STUDY_CALC_DB`` with the ``lru_cache``-decorated
loader functions in :mod:`study_calc.core.learning`: those caches are keyed on
``(item_id, language)`` arguments, not on the DB path.  If a test needs to
reload the same ``(item_id, language)`` pair from a different database it must
call ``load_<X>.cache_clear()`` (or ``learning.cache_clear()`` if a wrapper is
added) after switching the env var.
"""

from __future__ import annotations

import os
import sqlite3
from functools import lru_cache
from pathlib import Path

# Resolved at import time so the default is stable even if cwd changes.
_DEFAULT_DB: Path = Path(__file__).parent.parent / "data" / "knowledgebase.db"


@lru_cache(maxsize=None)
def _open(resolved_path: str) -> sqlite3.Connection:
    """Open (and cache) a :class:`sqlite3.Connection` for *resolved_path*.

    Args:
        resolved_path: The absolute, resolved path to the SQLite file.  Passing
            a resolved path means the cache key is canonical even if the caller
            supplies the path in different relative forms.

    Returns:
        An open :class:`sqlite3.Connection` with :attr:`~sqlite3.Connection.row_factory`
        set to :class:`sqlite3.Row` for name-based column access.
    """
    conn = sqlite3.connect(resolved_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_connection() -> sqlite3.Connection:
    """Return a cached :class:`sqlite3.Connection` for the configured database.

    The database path is resolved in this order:

    1. The ``STUDY_CALC_DB`` environment variable (if set and non-empty).
    2. ``study_calc/data/knowledgebase.db`` relative to this package.

    Returns:
        An open :class:`sqlite3.Connection` with :class:`sqlite3.Row` as the
        row factory, shared across calls that resolve to the same path.
    """
    env_path = os.environ.get("STUDY_CALC_DB", "").strip()
    raw = Path(env_path) if env_path else _DEFAULT_DB
    return _open(str(raw.resolve()))
