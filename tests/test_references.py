"""Tests for the formula learning content: explanations, steps, and references."""

import re

import pytest

from study_calc.core.explain import DEFAULT_SOLVE_STEPS, Explanation
from study_calc.domains import SECTIONS
from study_calc.domains.references import explanation_for, references_for
from study_calc.i18n import I18n


@pytest.fixture
def tr() -> I18n:
    return I18n()


def _all_formulas():
    for formulas in SECTIONS.values():
        yield from formulas


def test_every_formula_has_two_verified_references():
    for formula in _all_formulas():
        refs = references_for(formula.key)
        assert len(refs) == 2, f"{formula.key} should map to OpenStax + CollegePhysicsAnswers"
        labels = {r.label_key for r in refs}
        assert labels == {"ref.openstax", "ref.cpanswers"}
        for ref in refs:
            assert ref.url.startswith("https://"), ref.url


def test_explanation_uses_conventional_theory_key_and_default_steps():
    exp = explanation_for("newton_2")
    assert isinstance(exp, Explanation)
    assert exp.theory_key == "theory.newton_2"
    assert exp.steps_keys == DEFAULT_SOLVE_STEPS


def test_english_catalog_has_theory_for_every_formula(tr):
    """English is the fallback locale, so it must carry every theory paragraph."""
    catalog = tr._catalogs["en"]
    for formula in _all_formulas():
        key = f"theory.{formula.key}"
        assert key in catalog, f"en.json is missing {key}"
        assert catalog[key].strip(), f"{key} is empty"


@pytest.mark.parametrize("key", ["ui.theory", "ui.how_to_solve", "ui.learn_more",
                                 "ref.openstax", "ref.cpanswers", *DEFAULT_SOLVE_STEPS])
def test_panel_labels_present_in_english(tr, key):
    assert key in tr._catalogs["en"]


def test_unknown_formula_key_has_no_references():
    assert references_for("does_not_exist") == ()


def test_openstax_slugs_have_no_obvious_typos():
    """Cheap guard: section slugs should look like '<chapter>-<section>-<words>'."""
    for formula in _all_formulas():
        openstax = references_for(formula.key)[0]
        slug = openstax.url.rsplit("/", 1)[-1]
        assert re.match(r"^\d+-", slug), slug
