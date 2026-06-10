"""Tests for the rich learning materials under ``study_calc/learning/``.

These validate the content folder's integrity (every referenced glossary term
resolves, schema fields are present), the English fallback in the loader, and the
presence of the new panel labels. They do not require *every* formula to have a
topic yet — content is filled in section by section — but every topic that exists
must be internally consistent.
"""

import pytest

from study_calc.core import learning
from study_calc.core.learning import Concept, Topic, load_concept, load_topic
from study_calc.domains import SECTIONS
from study_calc.i18n import I18n

_UI_LABELS = [
    "ui.useful_formulas", "ui.key_terms", "ui.open_full", "ui.worked_example",
    "ui.given", "ui.find", "ui.solution", "ui.answer", "ui.see_also",
    "ui.related_formulas",
]


@pytest.fixture
def tr() -> I18n:
    return I18n()


def _all_formula_keys():
    for formulas in SECTIONS.values():
        for formula in formulas:
            yield formula.key


def _present_topic_ids():
    return learning.available_topic_ids("en")


def test_there_is_at_least_some_content():
    """A guard so an empty learning folder fails loudly rather than silently."""
    assert _present_topic_ids(), "no topic files found under learning/en/topics"


def test_every_present_topic_loads_and_has_a_summary():
    for topic_id in _present_topic_ids():
        topic = load_topic(topic_id, "en")
        assert isinstance(topic, Topic)
        assert topic.summary.strip(), f"{topic_id}: empty summary"


def test_every_topic_term_resolves_to_a_glossary_concept():
    for topic_id in _present_topic_ids():
        topic = load_topic(topic_id, "en")
        for term_id in topic.terms:
            concept = load_concept(term_id, "en")
            assert concept is not None, f"{topic_id} references missing term '{term_id}'"
            assert concept.short.strip(), f"term '{term_id}': empty short definition"
            assert concept.full.strip(), f"term '{term_id}': empty full explanation"


def test_topic_worked_examples_are_complete():
    for topic_id in _present_topic_ids():
        topic = load_topic(topic_id, "en")
        example = topic.example
        if example is None:
            continue
        assert example.find.strip(), f"{topic_id}: example has no 'find'"
        assert example.answer.strip(), f"{topic_id}: example has no 'answer'"
        assert example.steps, f"{topic_id}: example has no steps"


def test_glossary_see_also_links_resolve():
    """No dangling cross-references between glossary terms."""
    for topic_id in _present_topic_ids():
        topic = load_topic(topic_id, "en")
        for term_id in topic.terms:
            concept = load_concept(term_id, "en")
            assert concept is not None
            for other_id in concept.see_also:
                assert load_concept(other_id, "en") is not None, (
                    f"term '{term_id}' links to missing term '{other_id}'"
                )


def test_loader_falls_back_to_english_for_unknown_language():
    """A topic with no localized file is served from English, not lost."""
    english = load_topic("newton_2", "en")
    other = load_topic("newton_2", "zz")  # no 'zz' catalog exists
    assert other is not None
    assert other.summary == english.summary


def test_unknown_topic_and_term_return_none():
    assert load_topic("does_not_exist", "en") is None
    assert load_concept("does_not_exist", "en") is None


def test_every_physics_formula_has_a_topic():
    """Every formula in every section carries a learning topic."""
    for key in _all_formula_keys():
        assert load_topic(key, "en") is not None, (
            f"formula '{key}' has no learning topic under learning/en/topics"
        )


def test_every_cas_operation_has_a_topic():
    """Each Math/CAS operation has a 'cas_<op>' learning topic."""
    from study_calc.core import cas

    for op in cas.OPERATIONS:
        assert load_topic(f"cas_{op}", "en") is not None, (
            f"CAS operation '{op}' has no learning topic 'cas_{op}'"
        )


def test_curriculum_codes_are_known():
    """Every course code tagged on a topic is a known Ontario course code."""
    for topic_id in learning.available_topic_ids("en"):
        topic = load_topic(topic_id, "en")
        for code in topic.courses:
            assert code in learning.CURRICULUM_GRADES, (
                f"topic '{topic_id}' has unknown course code '{code}'"
            )


def test_expected_topics_carry_their_course_code():
    """Spot-check the curriculum badges on representative topics."""
    assert load_topic("cas_factor", "en").courses == ("MCR3U",)
    assert load_topic("cas_logarithm", "en").courses == ("MHF4U",)
    assert load_topic("cas_rate", "en").courses == ("MHF4U", "MCV4U")
    assert load_topic("vec_dot", "en").courses == ("MCV4U",)


@pytest.mark.parametrize("key", _UI_LABELS)
def test_new_panel_labels_present_in_english(tr, key):
    assert key in tr._catalogs["en"], f"en.json is missing {key}"
