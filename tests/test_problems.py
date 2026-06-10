"""Tests for the practice-problem bank behind the Problems helper.

Validate that every problem file loads into a complete :class:`Problem`, is tagged
with a known subject, links only to topics/videos that exist, and that the
subject filter and English fallback behave.
"""

import pytest

from study_calc.core.learning import (
    Problem,
    available_problem_ids,
    load_problem,
    load_topic,
    problems_for_subject,
)

KNOWN_SUBJECTS = {"physics", "math", "tools", "chemistry"}


def _ids():
    return available_problem_ids("en")


def test_there_is_at_least_some_problem():
    assert _ids(), "no problem files found under learning/en/problems"


def test_every_problem_loads_and_is_complete():
    for pid in _ids():
        problem = load_problem(pid, "en")
        assert isinstance(problem, Problem)
        assert problem.subject, f"{pid}: missing subject"
        example = problem.example
        assert example.find.strip(), f"{pid}: example has no 'find'"
        assert example.answer.strip(), f"{pid}: example has no 'answer'"
        assert example.steps, f"{pid}: example has no steps"


def test_problem_subjects_are_known():
    for pid in _ids():
        assert load_problem(pid, "en").subject in KNOWN_SUBJECTS


def test_problem_topic_links_resolve():
    for pid in _ids():
        problem = load_problem(pid, "en")
        if problem.topic_id:
            assert load_topic(problem.topic_id, "en") is not None, (
                f"{pid} links to missing topic '{problem.topic_id}'"
            )


def test_problem_video_urls_are_https():
    for pid in _ids():
        problem = load_problem(pid, "en")
        if problem.video_url:
            assert problem.video_url.startswith("https://"), problem.video_url


def test_problems_for_subject_filters_and_empty_subject_is_empty():
    physics = problems_for_subject("physics", "en")
    assert physics and all(p.subject == "physics" for p in physics)
    assert problems_for_subject("chemistry", "en") == ()


def test_unknown_problem_returns_none():
    assert load_problem("does_not_exist", "en") is None


def test_loader_falls_back_to_english_for_unknown_language():
    english = load_problem("phys_ohm_current", "en")
    other = load_problem("phys_ohm_current", "zz")  # no 'zz' catalog exists
    assert other is not None
    assert other.example.answer == english.example.answer
