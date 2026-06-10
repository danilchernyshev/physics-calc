"""Thin SQLite connection helper for the study_calc knowledgebase.

The knowledgebase is a read-only content artifact committed to the repository at
``study_calc/data/knowledgebase.db``.  The path can be overridden with the
``STUDY_CALC_DB`` environment variable, which is useful for tests that want to
point at an isolated temporary database.

Connection model
----------------
:func:`get_connection` reads the current ``STUDY_CALC_DB`` value on every call
and returns a connection cached **per thread** (a :class:`threading.local`
keyed on the resolved absolute path).  A :class:`sqlite3.Connection` is not safe
to share across threads, and the web bridge dispatches ``js_api`` calls on a
PyWebView worker thread distinct from the importing thread; giving each thread
its own connection avoids interleaved-cursor errors without a global lock.  That
means:

* Repeated calls on the same thread with the same effective path re-use the same
  connection (no reconnection overhead).
* Changing ``STUDY_CALC_DB`` between calls transparently opens a *new*
  connection for the new path while keeping the old one cached (important for
  tests that swap the database between fixture setup and teardown).

Note for tests that combine ``STUDY_CALC_DB`` with the ``lru_cache``-decorated
loader functions in :mod:`study_calc.core.learning`: those caches are keyed on
``(item_id, language)`` arguments, not on the DB path.  If a test needs to
reload the same ``(item_id, language)`` pair from a different database it must
call ``load_<X>.cache_clear()`` after switching the env var.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

# Resolved at import time so the default is stable even if cwd changes.
_DEFAULT_DB: Path = Path(__file__).parent.parent / "data" / "knowledgebase.db"

# Per-thread cache: each thread holds its own ``{resolved_path: Connection}``
# map, because a sqlite3.Connection must not be shared between threads.
_local = threading.local()


def get_connection() -> sqlite3.Connection:
    """Return a per-thread cached :class:`sqlite3.Connection` for the DB.

    The database path is resolved in this order:

    1. The ``STUDY_CALC_DB`` environment variable (if set and non-empty).
    2. ``study_calc/data/knowledgebase.db`` relative to this package.

    Returns:
        An open :class:`sqlite3.Connection` with :class:`sqlite3.Row` as the
        row factory, reused across calls on the same thread that resolve to the
        same path.
    """
    env_path = os.environ.get("STUDY_CALC_DB", "").strip()
    raw = Path(env_path) if env_path else _DEFAULT_DB
    key = str(raw.resolve())

    cache: dict[str, sqlite3.Connection] | None = getattr(_local, "conns", None)
    if cache is None:
        cache = _local.conns = {}

    conn = cache.get(key)
    if conn is None:
        # check_same_thread defaults to True: the connection is only ever used
        # from the thread that created (and cached) it.
        conn = sqlite3.connect(key)
        conn.row_factory = sqlite3.Row
        cache[key] = conn
    return conn
