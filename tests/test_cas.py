"""Tests for the SymPy-backed symbolic math (CAS) engine and its i18n keys."""

import pytest

from physics_calc.core import cas
from physics_calc.i18n import I18n


def test_simplify_cancels_common_factor():
    result = cas.run("simplify", "(x^2 - 1)/(x - 1)")
    assert result.output_text == "x + 1"


def test_expand_binomial():
    result = cas.run("expand", "(x + 1)^2")
    assert result.output_text == "x**2 + 2*x + 1"


def test_factor_difference_of_squares():
    result = cas.run("factor", "x^2 - 1")
    assert result.output_text == "(x - 1)*(x + 1)"


def test_derivative():
    result = cas.run("derivative", "x^3", "x")
    assert result.output_text == "3*x**2"


def test_integral_is_indefinite():
    result = cas.run("integral", "2*x", "x")
    assert result.output_text == "x**2"


def test_solve_quadratic_returns_both_roots():
    result = cas.run("solve", "x^2 - 4", "x")
    assert set(result.output_text.split(", ")) == {"x = -2", "x = 2"}


def test_solve_accepts_an_equation_with_equals_sign():
    result = cas.run("solve", "2*x = 6", "x")
    assert result.output_text == "x = 3"
    assert result.input_text == "2*x = 6"


def test_evaluate_is_numeric():
    result = cas.run("evaluate", "sqrt(2)")
    assert float(result.output_text) == pytest.approx(1.4142135, rel=1e-6)


def test_implicit_multiplication_and_caret_power():
    # "2x" -> 2*x and "x^2" -> x**2, so input reads like ordinary math notation.
    assert cas.run("expand", "2x").input_text == "2*x"
    assert cas.run("simplify", "x^2").output_text == "x**2"


def test_series_expands_around_zero():
    result = cas.run("series", "exp(x)", "x")
    assert result.output_text == "x**5/120 + x**4/24 + x**3/6 + x**2/2 + x + 1"


def test_variable_is_auto_detected_when_unique():
    # No variable given, but the expression has a single unknown -> use it.
    assert cas.run("derivative", "x^3").output_text == "3*x**2"
    assert cas.run("solve", "x^2 - 4").output_text == "x = -2, x = 2"


def test_ambiguous_variable_is_reported():
    with pytest.raises(cas.CasError) as info:
        cas.run("derivative", "a*x^2")  # two unknowns, none specified
    assert info.value.code == "cas_ambiguous_variable"
    assert info.value.params["vars"] == "a, x"


def test_analyze_overview_collects_multiple_views():
    keys = [s.key for s in cas.run("analyze", "x^2 - 4").steps]
    assert keys[0] == "cas.step.do.analyze"
    for expected in ("cas.step.card.simplified", "cas.step.card.factored",
                     "cas.step.card.derivative", "cas.step.card.integral",
                     "cas.step.card.roots"):
        assert expected in keys


def test_analyze_of_constant_shows_decimal():
    steps = cas.run("analyze", "sqrt(2) + pi").steps
    simplified = next(s for s in steps if s.key == "cas.step.card.simplified")
    assert "≈" in simplified.params["value"]


def test_analyze_includes_series_for_transcendental():
    keys = [s.key for s in cas.run("analyze", "sin(x)").steps]
    assert "cas.step.card.series" in keys


def test_result_carries_explanation_steps():
    result = cas.run("factor", "x^2 - 1")
    keys = [s.key for s in result.steps]
    assert keys[0] == "cas.step.input"
    assert "cas.step.do.factor" in keys
    assert keys[-1] == "cas.step.result"
    assert result.steps[-1].params["result"] == "(x - 1)*(x + 1)"


def test_integral_explanation_includes_verification_step():
    result = cas.run("integral", "2*x", "x")
    keys = [s.key for s in result.steps]
    assert "cas.step.integral_check" in keys
    check = next(s for s in result.steps if s.key == "cas.step.integral_check")
    assert check.params["back"] == "2*x"  # differentiating x**2 returns the integrand


def test_solve_explanation_lists_each_root():
    result = cas.run("solve", "x^2 - 4", "x")
    roots = [s for s in result.steps if s.key == "cas.step.solve_root"]
    assert len(roots) == 2
    assert any(s.key == "cas.step.solve_count" and s.params["n"] == 2 for s in result.steps)


def test_constant_result_also_shows_decimal_value():
    # simplify can't reduce sin(30) symbolically, but it's a constant — so the
    # user still gets a number instead of their input echoed back unchanged.
    out = cas.run("simplify", "sin(30)").output_text
    assert out.startswith("sin(30)") and "≈" in out
    assert float(out.split("≈")[1]) == pytest.approx(-0.988032, rel=1e-4)


def test_irrational_constant_shows_decimal():
    out = cas.run("simplify", "sqrt(2) + pi").output_text
    assert "≈" in out and float(out.split("≈")[1]) == pytest.approx(4.55581, rel=1e-4)


def test_plain_number_is_not_decorated_with_decimal():
    assert cas.run("simplify", "2 + 2").output_text == "4"  # already a number


def test_expression_with_unknown_is_not_decorated():
    assert cas.run("simplify", "x + 1").output_text == "x + 1"  # not a constant


def test_solve_decorates_irrational_roots_with_decimals():
    out = cas.run("solve", "x^2 - 2", "x").output_text
    assert out.count("≈") == 2  # both ±sqrt(2) roots get a decimal


def test_empty_expression_raises():
    with pytest.raises(cas.CasError) as info:
        cas.run("simplify", "   ")
    assert info.value.code == "cas_empty"


def test_unparseable_expression_raises_with_detail():
    with pytest.raises(cas.CasError) as info:
        cas.run("simplify", ")(")
    assert info.value.code == "cas_parse"
    assert "detail" in info.value.params


def test_operation_needing_variable_raises_when_none_to_detect():
    # No variable given and the expression is constant -> nothing to auto-detect.
    with pytest.raises(cas.CasError) as info:
        cas.run("derivative", "5", "")
    assert info.value.code == "cas_needs_variable"


def test_non_symbol_variable_raises():
    with pytest.raises(cas.CasError) as info:
        cas.run("integral", "x^2", "2")
    assert info.value.code == "cas_bad_variable"
    assert info.value.params["value"] == "2"


def test_unknown_operation_raises():
    with pytest.raises(cas.CasError) as info:
        cas.run("nonsense", "x")
    assert info.value.code == "cas_unknown_operation"


def test_solve_with_no_real_or_symbolic_solution_raises():
    # 1 = 0 is never true, so SymPy returns no solutions.
    with pytest.raises(cas.CasError) as info:
        cas.run("solve", "1 = 0", "x")
    assert info.value.code == "cas_no_solution"


def test_user_input_is_not_evaluated_as_python():
    # A would-be Python builtin must stay an inert symbol, never get called.
    result = cas.run("simplify", "__import__")
    assert result.output_text == "__import__"


# --- i18n completeness for the CAS-specific keys (not covered by SECTIONS walk). ---

_CAS_STEP_KEYS = [
    "cas.step.input", "cas.step.result",
    "cas.step.do.simplify", "cas.step.do.expand", "cas.step.do.factor",
    "cas.step.do.derivative", "cas.step.do.integral", "cas.step.do.solve",
    "cas.step.do.evaluate", "cas.step.do.analyze", "cas.step.do.series",
    "cas.step.simplify_unchanged",
    "cas.step.integral_check", "cas.step.solve_standard",
    "cas.step.solve_factored", "cas.step.solve_count", "cas.step.solve_root",
    "cas.step.card.simplified", "cas.step.card.factored", "cas.step.card.expanded",
    "cas.step.card.derivative", "cas.step.card.integral", "cas.step.card.roots",
    "cas.step.card.series",
]

_CAS_KEYS = [
    "tab.cas", "cas.operation", "cas.expression", "cas.variable",
    "cas.hint", "cas.unavailable",
] + [f"cas.op.{oid}" for oid in cas.OPERATIONS] + _CAS_STEP_KEYS


@pytest.mark.parametrize("code", ["en", "es", "fr", "ru", "uk"])
def test_every_catalog_has_all_cas_keys(code):
    catalog = I18n()._catalogs[code]
    missing = set(_CAS_KEYS) - set(catalog)
    assert not missing, f"{code}.json is missing CAS keys: {sorted(missing)}"
