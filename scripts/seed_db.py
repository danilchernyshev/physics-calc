"""seed_db.py — populate study_calc/data/knowledgebase.db from JSON sources.

Usage
-----
    python scripts/seed_db.py [--db PATH]

``--db`` defaults to ``study_calc/data/knowledgebase.db`` relative to the
repository root (detected as the directory that contains ``study_calc/``).

The script is idempotent: every table uses ``INSERT OR REPLACE`` so running it
twice produces identical row counts with no duplicates or errors.

Content sources
---------------
- ``study_calc/learning/en/topics/*.json``    → topics, topic_terms, topic_examples
- ``study_calc/learning/en/glossary/*.json``  → concepts
- ``study_calc/learning/en/problems/*.json``  → problems
- ``study_calc/data/elements.json``           → elements

All are seeded with ``language = 'en'``.  Translated rows (other languages)
would be inserted by a separate future script reading non-English learning
directories.

Schema
------
Defined in ``study_calc/data/schema.sql`` (see ADR 0002-knowledgebase-db.md).
List-typed JSON fields are serialised to JSON strings before insertion.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Repository-root detection
# ---------------------------------------------------------------------------

def _repo_root() -> pathlib.Path:
    """Return the repository root by locating the nearest parent that contains
    ``study_calc/`` as a subdirectory."""
    candidate = pathlib.Path(__file__).resolve().parent
    # scripts/ lives one level below the repo root
    candidate = candidate.parent
    if (candidate / "study_calc").is_dir():
        return candidate
    # Fallback: current working directory
    cwd = pathlib.Path.cwd()
    if (cwd / "study_calc").is_dir():
        return cwd
    raise RuntimeError(
        "Cannot locate repository root (directory containing study_calc/). "
        "Run the script from the repository root or pass --db explicitly."
    )


# ---------------------------------------------------------------------------
# Schema application
# ---------------------------------------------------------------------------

def _apply_schema(conn: sqlite3.Connection, schema_path: pathlib.Path) -> None:
    """Execute all DDL statements from schema.sql."""
    ddl = schema_path.read_text(encoding="utf-8")
    conn.executescript(ddl)
    conn.commit()


# ---------------------------------------------------------------------------
# Helper: serialise list/dict fields to JSON strings
# ---------------------------------------------------------------------------

def _jdump(value: Any, default: str = "[]") -> str:
    """Serialise *value* to a compact JSON string.

    Returns *default* when *value* is ``None`` or an empty collection so that
    columns always contain valid JSON.
    """
    if value is None:
        return default
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Seeders per content domain
# ---------------------------------------------------------------------------

def seed_topics(
    conn: sqlite3.Connection,
    topics_dir: pathlib.Path,
    language: str = "en",
) -> dict[str, int]:
    """Seed topics, topic_terms, and topic_examples from ``topics_dir``.

    Returns a dict of ``{table_name: row_count}`` for the summary printout.
    """
    n_topics = 0
    n_terms = 0
    n_examples = 0

    for path in sorted(topics_dir.glob("*.json")):
        topic_id = path.stem
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

        # ---- topics ----
        conn.execute(
            """
            INSERT OR REPLACE INTO topics
                (topic_id, language, summary, formulas_json, method_json, courses_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                language,
                data.get("summary", ""),
                _jdump(data.get("formulas")),
                _jdump(data.get("method")),
                _jdump(data.get("courses")),
            ),
        )
        n_topics += 1

        # ---- topic_terms ----
        terms: list[str] = data.get("terms") or []
        for position, term_id in enumerate(terms):
            conn.execute(
                """
                INSERT OR REPLACE INTO topic_terms
                    (topic_id, language, term_id, position)
                VALUES (?, ?, ?, ?)
                """,
                (topic_id, language, term_id, position),
            )
            n_terms += 1

        # ---- topic_examples ----
        example: dict[str, Any] | None = data.get("example")
        if example is not None:
            conn.execute(
                """
                INSERT OR REPLACE INTO topic_examples
                    (topic_id, language, title, given_json, find, steps_json, answer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    topic_id,
                    language,
                    example.get("title", ""),
                    _jdump(example.get("given")),
                    example.get("find", ""),
                    _jdump(example.get("steps")),
                    example.get("answer", ""),
                ),
            )
            n_examples += 1

    conn.commit()
    return {
        "topics": n_topics,
        "topic_terms": n_terms,
        "topic_examples": n_examples,
    }


def seed_concepts(
    conn: sqlite3.Connection,
    glossary_dir: pathlib.Path,
    language: str = "en",
) -> dict[str, int]:
    """Seed the ``concepts`` table from ``glossary_dir``.

    Returns ``{"concepts": row_count}``.
    """
    n = 0
    for path in sorted(glossary_dir.glob("*.json")):
        term_id = path.stem
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        conn.execute(
            """
            INSERT OR REPLACE INTO concepts
                (term_id, language, title, short, full, formulas_json, see_also_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                term_id,
                language,
                data.get("title", ""),
                data.get("short", ""),
                data.get("full", ""),
                _jdump(data.get("formulas")),
                _jdump(data.get("see_also")),
            ),
        )
        n += 1
    conn.commit()
    return {"concepts": n}


def seed_problems(
    conn: sqlite3.Connection,
    problems_dir: pathlib.Path,
    language: str = "en",
) -> dict[str, int]:
    """Seed the ``problems`` table from ``problems_dir``.

    Returns ``{"problems": row_count}``.
    """
    n = 0
    for path in sorted(problems_dir.glob("*.json")):
        problem_id = path.stem
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        conn.execute(
            """
            INSERT OR REPLACE INTO problems
                (problem_id, language, subject, title, given_json, find,
                 steps_json, answer, video_url, topic_id, courses_json, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                problem_id,
                language,
                data.get("subject", ""),
                data.get("title", ""),
                _jdump(data.get("given")),
                data.get("find", ""),
                _jdump(data.get("steps")),
                data.get("answer", ""),
                data.get("video_url", ""),
                data.get("topic", ""),
                _jdump(data.get("courses")),
                data.get("difficulty", ""),
            ),
        )
        n += 1
    conn.commit()
    return {"problems": n}


def seed_elements(
    conn: sqlite3.Connection,
    elements_path: pathlib.Path,
) -> dict[str, int]:
    """Seed the ``elements`` table from ``elements.json``.

    Returns ``{"elements": row_count}``.

    Field mapping (JSON → column):
      mass  → atomic_mass
      group → group_id  (nullable; some elements have no main-group number)
    """
    elements: list[dict[str, Any]] = json.loads(
        elements_path.read_text(encoding="utf-8")
    )
    n = 0
    for elem in elements:
        conn.execute(
            """
            INSERT OR REPLACE INTO elements
                (number, symbol, name, atomic_mass, group_id, period,
                 category, xpos, ypos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                elem["number"],
                elem["symbol"],
                elem["name"],
                elem["mass"],
                elem.get("group"),      # nullable for lanthanides / actinides
                elem["period"],
                elem.get("category", ""),
                elem["xpos"],
                elem["ypos"],
            ),
        )
        n += 1
    conn.commit()
    return {"elements": n}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Entry point for the seeding script.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code (0 on success).
    """
    parser = argparse.ArgumentParser(
        description="Populate the study_calc knowledgebase SQLite DB from JSON sources."
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help=(
            "Path to the SQLite database file to create/update. "
            "Defaults to study_calc/data/knowledgebase.db relative to the repo root."
        ),
    )
    args = parser.parse_args(argv)

    root = _repo_root()

    db_path = pathlib.Path(args.db) if args.db else root / "study_calc" / "data" / "knowledgebase.db"
    schema_path = root / "study_calc" / "data" / "schema.sql"
    learning_en = root / "study_calc" / "learning" / "en"
    elements_path = root / "study_calc" / "data" / "elements.json"

    # Validate sources exist
    for p in (schema_path, learning_en / "topics", learning_en / "glossary",
              learning_en / "problems", elements_path):
        if not p.exists():
            print(f"ERROR: required path not found: {p}", file=sys.stderr)
            return 1

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"DB: {db_path}")
    print(f"Schema: {schema_path}")

    conn = sqlite3.connect(db_path)
    try:
        _apply_schema(conn, schema_path)

        counts: dict[str, int] = {}

        print("Seeding topics …")
        counts.update(seed_topics(conn, learning_en / "topics"))

        print("Seeding concepts …")
        counts.update(seed_concepts(conn, learning_en / "glossary"))

        print("Seeding problems …")
        counts.update(seed_problems(conn, learning_en / "problems"))

        print("Seeding elements …")
        counts.update(seed_elements(conn, elements_path))

    finally:
        conn.close()

    print("\nInserted rows per table:")
    col_w = max(len(t) for t in counts)
    for table, n in counts.items():
        print(f"  {table:<{col_w}}  {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
