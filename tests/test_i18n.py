"""Tests for the localization engine and catalog completeness."""

import pytest

from study_calc.core.units import categories, units_of
from study_calc.domains import SECTIONS
from study_calc.i18n import I18n, _LOCALES_DIR


@pytest.fixture
def tr() -> I18n:
    """A fresh I18n instance so tests never mutate the shared singleton."""
    return I18n()


def test_translates_active_language(tr):
    assert tr.t("ui.compute") == "Compute"
    tr.set_language("ru")
    assert tr.t("ui.compute") == "Вычислить"
    tr.set_language("fr")
    assert tr.t("ui.compute") == "Calculer"


def test_formats_parameters(tr):
    assert tr.t("error.missing_value", var="Force") == 'Value for "Force" is not set.'


def test_unknown_key_falls_back_to_key(tr):
    assert tr.t("does.not.exist") == "does.not.exist"


def test_missing_translation_falls_back_to_default(tr, tmp_path):
    # A catalog with only the native name should fall back to English elsewhere.
    (tmp_path / "en.json").write_text('{"ui.compute": "Compute"}', encoding="utf-8")
    (tmp_path / "xx.json").write_text('{"language.native": "X"}', encoding="utf-8")
    custom = I18n(locales_dir=tmp_path, default="en")
    custom.set_language("xx")
    assert custom.t("ui.compute") == "Compute"  # fell back to English


def test_set_unknown_language_raises(tr):
    with pytest.raises(ValueError):
        tr.set_language("zz")


def test_available_languages(tr):
    codes = {code for code, _native in tr.available_languages()}
    assert {"en", "es", "fr", "ru", "uk"} <= codes
    natives = dict(tr.available_languages())
    assert natives["ru"] == "Русский"
    assert natives["fr"] == "Français"
    assert natives["es"] == "Español"
    assert natives["uk"] == "Українська"


def test_variable_label_with_and_without_unit(tr):
    force = SECTIONS["mechanics"][0].variable("F")
    assert tr.variable_label(force) == "Force (F, N)"
    n1 = SECTIONS["waves"][-1].variable("n1")
    assert tr.variable_label(n1) == "Refractive index of medium 1 (n1)"


def _all_required_keys() -> set[str]:
    """Every i18n key the domain layer and converter reference."""
    keys: set[str] = set()
    for section_id, formulas in SECTIONS.items():
        keys.add(f"section.{section_id}")
        for formula in formulas:
            keys.add(formula.name_key)
            for var in formula.variables:
                keys.add(var.name_key)
                if var.unit_key:
                    keys.add(var.unit_key)
    for category in categories():
        keys.add(f"category.{category}")
        for unit in units_of(category):
            keys.add(f"unit.{unit}")
    return keys


@pytest.mark.parametrize("code", ["en", "es", "fr", "ru", "uk"])
def test_every_catalog_has_all_domain_keys(code, tr):
    catalog_keys = set(tr._catalogs[code])
    missing = _all_required_keys() - catalog_keys
    assert not missing, f"{code}.json is missing keys: {sorted(missing)}"


def test_locales_directory_exists():
    assert _LOCALES_DIR.is_dir()
    assert (_LOCALES_DIR / "en.json").exists()


_ERROR_KEYS = [
    "error.no_solver", "error.missing_value", "error.zero_division",
    "error.no_real_solution", "error.not_finite", "error.math_error",
    "error.total_internal_reflection", "error.not_a_number",
    "error.no_empty_field", "error.too_many_empty",
    "error.unknown_category", "error.unknown_unit",
    "error.cas_empty", "error.cas_parse", "error.cas_needs_variable",
    "error.cas_bad_variable", "error.cas_no_solution",
    "error.cas_unknown_operation", "error.cas_failed",
    "error.cas_ambiguous_variable", "error.cas_not_inequality",
    "error.cas_needs_point", "error.cas_needs_second_function",
    "error.vec_empty", "error.vec_parse", "error.vec_dim_mismatch",
    "error.vec_cross_dim", "error.vec_zero", "error.vec_bad_scalar",
    "error.vec_unknown_operation",
]


@pytest.mark.parametrize("code", ["en", "es", "fr", "ru", "uk"])
def test_every_catalog_has_all_error_keys(code, tr):
    missing = set(_ERROR_KEYS) - set(tr._catalogs[code])
    assert not missing, f"{code}.json is missing error keys: {sorted(missing)}"
