"""Loader for the rich learning materials stored in the knowledgebase SQLite DB.

This is the engine behind the right-hand learning area.  Unlike
:mod:`study_calc.core.explain` (which stores i18n *keys* for the short, static
theory note and the study links), this module loads *prose* content from the
knowledgebase database (``study_calc/data/knowledgebase.db``, seeded from the
``study_calc/learning/`` content folder by ``scripts/seed_db.py``).

The public API is identical to the previous JSON-file-backed implementation so
no caller — GUI, web bridge, or tests — needs to change.

i18n fallback contract
-----------------------
Each lookup first tries the requested language; if no row exists for that
``(id, language)`` pair it falls back to ``"en"`` (English is the canonical
language and is always present).  This mirrors the previous file-based fallback
where a missing ``learning/<lang>/...`` file caused a retry from
``learning/en/...``.

A **topic** bundles everything shown for one kind of problem: a short summary,
the glossary terms needed to understand it, the useful formulas, a
step-by-step solving method, and one worked example.  A **concept** is a
single reusable term definition (short inline blurb + full explanation),
shared across topics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from study_calc.core import db as _db

DEFAULT_LANGUAGE = "en"

# Ontario course code -> grade level, for the curriculum badge shown on a topic
# or a practice problem. MCR3U: Functions (Gr. 11); MHF4U: Advanced Functions
# (Gr. 12); MCV4U: Calculus and Vectors (Gr. 12); MDM4U: Mathematics of Data
# Management (Gr. 12); SPH4U: Physics (Gr. 12); SCH4U: Chemistry (Gr. 12). Codes
# not listed render without a grade.
CURRICULUM_GRADES: dict[str, int] = {
    "MCR3U": 11,
    "MHF4U": 12,
    "MCV4U": 12,
    "MDM4U": 12,
    "SPH4U": 12,
    "SCH4U": 12,
}


@dataclass(frozen=True)
class Concept:
    """A reusable glossary term: a short inline blurb plus a full explanation.

    :param term_id: stable id, also the glossary file name (e.g. ``"momentum"``).
    :param title: display name of the term.
    :param short: one or two sentences shown inline in the panel.
    :param full: the longer explanation shown in the pop-up window.
    :param formulas: related formula strings worth listing with the term.
    :param see_also: ids of related concepts (rendered as further links).
    """

    term_id: str
    title: str
    short: str
    full: str
    formulas: tuple[str, ...] = ()
    see_also: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkedExample:
    """One original worked example for a topic (never copied from a paid source).

    :param title: a short caption for the example.
    :param given: the known quantities, one per line.
    :param find: what the example asks to find.
    :param steps: the ordered solution steps (plain prose / math).
    :param answer: the final result line.
    """

    title: str
    given: tuple[str, ...]
    find: str
    steps: tuple[str, ...]
    answer: str


@dataclass(frozen=True)
class Topic:
    """All the learning material for one problem type (a formula or a CAS op).

    :param topic_id: stable id — a :class:`~study_calc.core.formula.Formula` ``key``
        for physics, or ``"cas_<operation>"`` for a Math/CAS operation.
    :param summary: a short overview of what this kind of problem is about.
    :param terms: ids of the glossary :class:`Concept` s needed to solve it.
    :param formulas: useful related formula strings for this problem type.
    :param method: an ordered, topic-specific "how to approach it" recipe.
    :param example: one worked example, or ``None``.
    :param courses: Ontario course codes this topic supports (e.g. ``("MHF4U",)``),
        rendered as a curriculum badge. See :data:`CURRICULUM_GRADES`.
    """

    topic_id: str
    summary: str
    terms: tuple[str, ...] = ()
    formulas: tuple[str, ...] = ()
    method: tuple[str, ...] = ()
    example: WorkedExample | None = None
    courses: tuple[str, ...] = ()


@dataclass(frozen=True)
class Problem:
    """One practice problem for the Problems helper.

    A :class:`WorkedExample` (statement + steps + answer) tagged with the subject it
    belongs to and, optionally, a video walkthrough and the learning topic that
    teaches it.

    :param problem_id: stable id, also the problem file name.
    :param subject: navigation subject id (e.g. ``"physics"``, ``"math"``).
    :param example: the statement, solution steps and answer.
    :param video_url: optional link to a video solution (opened in the browser).
    :param topic_id: optional :class:`Topic` id whose theory backs this problem.
    :param courses: Ontario course codes this problem belongs to (e.g.
        ``("SCH4U",)``), rendered as a curriculum badge. See
        :data:`CURRICULUM_GRADES`.
    :param difficulty: optional difficulty tag (e.g. ``"easy"``, ``"hard"``).
        Populated by the M3-1 milestone; empty string until then.
    """

    problem_id: str
    subject: str
    example: WorkedExample
    video_url: str = ""
    topic_id: str = ""
    courses: tuple[str, ...] = ()
    difficulty: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _as_example_from_row(row: object | None) -> WorkedExample | None:
    """Reconstruct a :class:`WorkedExample` from a ``topic_examples`` DB row.

    Args:
        row: A :class:`sqlite3.Row` from the ``topic_examples`` table, or
            ``None`` when the topic has no worked example.

    Returns:
        A :class:`WorkedExample` instance, or ``None`` if *row* is ``None``.
    """
    if row is None:
        return None
    return WorkedExample(
        title=row["title"],
        given=tuple(json.loads(row["given_json"])),
        find=row["find"],
        steps=tuple(json.loads(row["steps_json"])),
        answer=row["answer"],
    )


def _fetch_localized(
    table: str,
    id_col: str,
    item_id: str,
    language: str,
) -> object | None:
    """Fetch the full row for ``(item_id, language)``, falling back to English.

    Tries *language* first; if no row exists falls back to ``DEFAULT_LANGUAGE``
    (``"en"``, the canonical language).  This single fetch-then-fallback also
    yields the *effective* language via the row's ``language`` column, so
    callers needing related-table queries (e.g. a topic's terms/example) don't
    need a separate probe.

    Args:
        table: The DB table name (``"topics"`` / ``"concepts"`` / ``"problems"``).
        id_col: The primary id column name (``"topic_id"`` / ``"term_id"`` /
            ``"problem_id"``).
        item_id: The id value to look up.
        language: The initially requested language code.

    Returns:
        The :class:`sqlite3.Row`, or ``None`` when the item does not exist in
        any language.
    """
    conn = _db.get_connection()
    # nosec B608 — table and id_col are internal constants, never user input
    row = conn.execute(  # noqa: S608
        f"SELECT * FROM {table} WHERE {id_col}=? AND language=?",
        (item_id, language),
    ).fetchone()
    if row is None and language != DEFAULT_LANGUAGE:
        row = conn.execute(  # noqa: S608
            f"SELECT * FROM {table} WHERE {id_col}=? AND language=?",
            (item_id, DEFAULT_LANGUAGE),
        ).fetchone()
    return row


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def load_concept(term_id: str, language: str = DEFAULT_LANGUAGE) -> Concept | None:
    """Load one glossary term, falling back to English, or ``None`` if unknown.

    Args:
        term_id: The stable glossary term id.
        language: The preferred language code (default ``"en"``).

    Returns:
        A :class:`Concept` for the requested (or English fallback) language, or
        ``None`` if *term_id* does not exist in the database at all.
    """
    row = _fetch_localized("concepts", "term_id", term_id, language)
    if row is None:
        return None
    return Concept(
        term_id=term_id,
        # Fall back to the id when a row carries no title, matching the prior
        # file loader (``data.get("title", term_id)``).
        title=row["title"] or term_id,
        short=row["short"],
        full=row["full"],
        formulas=tuple(json.loads(row["formulas_json"])),
        see_also=tuple(json.loads(row["see_also_json"])),
    )


@lru_cache(maxsize=None)
def load_topic(topic_id: str, language: str = DEFAULT_LANGUAGE) -> Topic | None:
    """Load one topic bundle, falling back to English, or ``None`` if none exists.

    The topic is assembled from three tables:

    * ``topics`` — summary, formula list, method steps, course codes.
    * ``topic_terms`` — ordered list of glossary term ids for this topic.
    * ``topic_examples`` — the optional single worked example.

    All three tables are queried with the *effective* language (the requested
    language if a row exists, otherwise ``"en"``).

    Args:
        topic_id: The stable topic id (a formula key or ``"cas_<op>"``).
        language: The preferred language code (default ``"en"``).

    Returns:
        A :class:`Topic` for the requested (or English fallback) language, or
        ``None`` if *topic_id* does not exist in the database at all.
    """
    row = _fetch_localized("topics", "topic_id", topic_id, language)
    if row is None:
        return None
    # The related-table queries must use the language that actually resolved
    # (the requested one, or the English fallback), read off the topic row.
    effective = row["language"]

    conn = _db.get_connection()
    term_rows = conn.execute(
        "SELECT term_id FROM topic_terms"
        " WHERE topic_id=? AND language=? ORDER BY position",
        (topic_id, effective),
    ).fetchall()

    example_row = conn.execute(
        "SELECT * FROM topic_examples WHERE topic_id=? AND language=?",
        (topic_id, effective),
    ).fetchone()

    return Topic(
        topic_id=topic_id,
        summary=row["summary"],
        terms=tuple(r["term_id"] for r in term_rows),
        formulas=tuple(json.loads(row["formulas_json"])),
        method=tuple(json.loads(row["method_json"])),
        example=_as_example_from_row(example_row),
        courses=tuple(json.loads(row["courses_json"])),
    )


def available_topic_ids(language: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Sorted ids of every topic present for *language* in the database.

    Args:
        language: The language code to query (default ``"en"``).

    Returns:
        A sorted tuple of topic id strings, empty if no topics exist for
        *language*.
    """
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT topic_id FROM topics WHERE language=? ORDER BY topic_id",
        (language,),
    ).fetchall()
    return tuple(r["topic_id"] for r in rows)


@lru_cache(maxsize=None)
def load_problem(problem_id: str, language: str = DEFAULT_LANGUAGE) -> Problem | None:
    """Load one practice problem, falling back to English, or ``None`` if unknown.

    The ``problems`` table uses ``problem_id`` as its sole primary key (the
    ``language`` column is present for future translations; all current rows
    are ``"en"``).  The fallback strategy tries:

    1. ``WHERE problem_id=? AND language=<requested>``
    2. ``WHERE problem_id=? AND language='en'`` (if requested language differs)
    3. Returns ``None`` if the problem_id does not exist at all.

    Args:
        problem_id: The stable problem id.
        language: The preferred language code (default ``"en"``).

    Returns:
        A :class:`Problem` for the requested (or English fallback) language, or
        ``None`` if *problem_id* does not exist in the database.
    """
    row = _fetch_localized("problems", "problem_id", problem_id, language)
    if row is None:
        return None

    example = WorkedExample(
        title=row["title"],
        given=tuple(json.loads(row["given_json"])),
        find=row["find"],
        steps=tuple(json.loads(row["steps_json"])),
        answer=row["answer"],
    )
    return Problem(
        problem_id=problem_id,
        subject=row["subject"],
        example=example,
        video_url=row["video_url"],
        topic_id=row["topic_id"],
        courses=tuple(json.loads(row["courses_json"])),
        difficulty=row["difficulty"],
    )


def available_problem_ids(language: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Sorted ids of every problem in the database (English is the canonical set).

    The *language* argument is accepted for API symmetry but the problems table
    currently holds one row per problem (all ``"en"``), so the returned set is
    language-independent.

    Args:
        language: Accepted for API symmetry; currently unused in the query.

    Returns:
        A sorted tuple of all problem id strings.
    """
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT problem_id FROM problems ORDER BY problem_id",
    ).fetchall()
    return tuple(r["problem_id"] for r in rows)


def problems_for_subject(
    subject: str, language: str = DEFAULT_LANGUAGE
) -> tuple[Problem, ...]:
    """Every problem tagged with *subject*, in id order, for the Problems helper.

    Args:
        subject: The navigation subject id (e.g. ``"physics"``, ``"chemistry"``).
        language: The preferred language code (default ``"en"``).

    Returns:
        A tuple of :class:`Problem` instances whose ``subject`` matches, in
        alphabetical id order.
    """
    problems = (load_problem(pid, language) for pid in available_problem_ids(language))
    return tuple(p for p in problems if p is not None and p.subject == subject)
