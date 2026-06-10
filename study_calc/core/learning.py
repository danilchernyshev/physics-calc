"""Loader for the rich learning materials kept under ``study_calc/learning/``.

This is the engine behind the right-hand learning area. Unlike
:mod:`study_calc.core.explain` (which stores i18n *keys* for the short, static
theory note and the study links), this module loads *prose* content authored in a
separate, format-flexible content folder so the depth and presentation can evolve
without touching code.

Layout of the content folder::

    study_calc/learning/
        en/
            glossary/<term_id>.json   reusable concept/term definitions
            topics/<topic_id>.json    one per problem type (a formula key or CAS op)
        ru/ ... (optional, additive)

English is the canonical language and the fallback: a file missing in the active
language is served from ``en`` (mirroring :mod:`study_calc.i18n`), so a partial
translation never leaves the panel blank.

A **topic** bundles everything shown for one kind of problem: a short summary, the
glossary terms needed to understand it, the useful formulas, a step-by-step solving
method, and one worked example. A **concept** is a single reusable term definition
(short inline blurb + full explanation), shared across topics.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_LEARNING_DIR = Path(__file__).parent.parent / "learning"
DEFAULT_LANGUAGE = "en"

# Ontario course code -> grade level, for the curriculum badge shown on a topic.
# MCR3U: Functions (Gr. 11); MHF4U: Advanced Functions (Gr. 12); MCV4U: Calculus
# and Vectors (Gr. 12). Codes not listed render without a grade.
CURRICULUM_GRADES: dict[str, int] = {
    "MCR3U": 11,
    "MHF4U": 12,
    "MCV4U": 12,
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
    """

    problem_id: str
    subject: str
    example: WorkedExample
    video_url: str = ""
    topic_id: str = ""


def _read_json(language: str, kind: str, item_id: str) -> dict | None:
    """Read ``learning/<language>/<kind>/<item_id>.json`` or ``None`` if absent."""
    path = _LEARNING_DIR / language / kind / f"{item_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _as_example(data: dict | None) -> WorkedExample | None:
    if not data:
        return None
    return WorkedExample(
        title=data.get("title", ""),
        given=tuple(data.get("given", ())),
        find=data.get("find", ""),
        steps=tuple(data.get("steps", ())),
        answer=data.get("answer", ""),
    )


@lru_cache(maxsize=None)
def load_concept(term_id: str, language: str = DEFAULT_LANGUAGE) -> Concept | None:
    """Load one glossary term, falling back to English, or ``None`` if unknown."""
    data = _read_json(language, "glossary", term_id)
    if data is None and language != DEFAULT_LANGUAGE:
        data = _read_json(DEFAULT_LANGUAGE, "glossary", term_id)
    if data is None:
        return None
    return Concept(
        term_id=term_id,
        title=data.get("title", term_id),
        short=data.get("short", ""),
        full=data.get("full", ""),
        formulas=tuple(data.get("formulas", ())),
        see_also=tuple(data.get("see_also", ())),
    )


@lru_cache(maxsize=None)
def load_topic(topic_id: str, language: str = DEFAULT_LANGUAGE) -> Topic | None:
    """Load one topic bundle, falling back to English, or ``None`` if none exists."""
    data = _read_json(language, "topics", topic_id)
    if data is None and language != DEFAULT_LANGUAGE:
        data = _read_json(DEFAULT_LANGUAGE, "topics", topic_id)
    if data is None:
        return None
    return Topic(
        topic_id=topic_id,
        summary=data.get("summary", ""),
        terms=tuple(data.get("terms", ())),
        formulas=tuple(data.get("formulas", ())),
        method=tuple(data.get("method", ())),
        example=_as_example(data.get("example")),
        courses=tuple(data.get("courses", ())),
    )


def available_topic_ids(language: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Sorted ids of every topic file present for ``language``."""
    directory = _LEARNING_DIR / language / "topics"
    if not directory.is_dir():
        return ()
    return tuple(sorted(p.stem for p in directory.glob("*.json")))


@lru_cache(maxsize=None)
def load_problem(problem_id: str, language: str = DEFAULT_LANGUAGE) -> Problem | None:
    """Load one practice problem, falling back to English, or ``None`` if unknown."""
    data = _read_json(language, "problems", problem_id)
    if data is None and language != DEFAULT_LANGUAGE:
        data = _read_json(DEFAULT_LANGUAGE, "problems", problem_id)
    if data is None:
        return None
    return Problem(
        problem_id=problem_id,
        subject=data.get("subject", ""),
        example=_as_example(data) or WorkedExample("", (), "", (), ""),
        video_url=data.get("video_url", ""),
        topic_id=data.get("topic", ""),
    )


def available_problem_ids(language: str = DEFAULT_LANGUAGE) -> tuple[str, ...]:
    """Sorted ids of every problem file present (English is the canonical set)."""
    directory = _LEARNING_DIR / DEFAULT_LANGUAGE / "problems"
    if not directory.is_dir():
        return ()
    return tuple(sorted(p.stem for p in directory.glob("*.json")))


def problems_for_subject(
    subject: str, language: str = DEFAULT_LANGUAGE
) -> tuple[Problem, ...]:
    """Every problem tagged with ``subject``, in id order, for the Problems helper."""
    problems = (load_problem(pid, language) for pid in available_problem_ids(language))
    return tuple(p for p in problems if p is not None and p.subject == subject)
