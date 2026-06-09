"""Tests for the formula engine and the per-section formula sets."""

import math

import pytest

from physics_calc.core.formula import Formula, Variable, SolveError
from physics_calc.domains import SECTIONS


def _find(section: str, key: str) -> Formula:
    for formula in SECTIONS[section]:
        if formula.key == key:
            return formula
    raise AssertionError(f"formula {key} not found in section {section}")


def test_newton_solves_each_variable():
    f = _find("mechanics", "newton_2")
    assert f.solve("F", {"m": 10, "a": 2}) == pytest.approx(20)
    assert f.solve("m", {"F": 20, "a": 2}) == pytest.approx(10)
    assert f.solve("a", {"F": 20, "m": 10}) == pytest.approx(2)


def test_kinetic_energy_roundtrip():
    f = _find("mechanics", "kinetic_energy")
    e = f.solve("E", {"m": 4, "v": 3})
    assert e == pytest.approx(18)
    assert f.solve("v", {"E": e, "m": 4}) == pytest.approx(3)


def test_ideal_gas():
    f = _find("thermodynamics", "ideal_gas")
    # 1 mol at 273.15 K and 101325 Pa occupies ~0.022414 m³ (22.414 L).
    v = f.solve("V", {"P": 101325, "n": 1, "T": 273.15})
    assert v == pytest.approx(0.022414, rel=1e-3)


def test_ohm_law():
    f = _find("electromagnetism", "ohm")
    assert f.solve("U", {"I": 2, "R": 5}) == pytest.approx(10)
    assert f.solve("R", {"U": 10, "I": 2}) == pytest.approx(5)


def test_wave_speed():
    f = _find("waves", "wave_speed")
    assert f.solve("v", {"lam": 2, "f": 50}) == pytest.approx(100)


def test_snell_law():
    f = _find("waves", "snell")
    # from air (n=1) into glass (n=1.5), angle of incidence 30°.
    theta2 = f.solve("theta2", {"n1": 1.0, "theta1": 30.0, "n2": 1.5})
    assert math.sin(math.radians(30)) == pytest.approx(1.5 * math.sin(math.radians(theta2)))


def test_snell_total_internal_reflection():
    f = _find("waves", "snell")
    with pytest.raises(SolveError) as info:
        # from glass into air at a steep angle -> no refracted ray.
        f.solve("theta2", {"n1": 1.5, "theta1": 80.0, "n2": 1.0})
    assert info.value.code == "total_internal_reflection"


def test_solve_missing_variable_raises_with_code():
    f = _find("mechanics", "newton_2")
    with pytest.raises(SolveError) as info:
        f.solve("F", {"m": 10})  # "a" is missing
    assert info.value.code == "missing_value"


def test_solve_division_by_zero_raises_with_code():
    f = _find("mechanics", "newton_2")
    with pytest.raises(SolveError) as info:
        f.solve("a", {"F": 20, "m": 0})
    assert info.value.code == "zero_division"


def test_solve_complex_result_raises_no_real_solution():
    # sqrt of a negative quantity -> Python returns a complex number.
    f = _find("mechanics", "kinetic_energy")
    with pytest.raises(SolveError) as info:
        f.solve("v", {"E": -1.0, "m": 1.0})
    assert info.value.code == "no_real_solution"


def test_solve_overflow_to_inf_raises_not_finite():
    # m * a overflows to +inf without raising; the result must be rejected.
    f = _find("mechanics", "newton_2")
    with pytest.raises(SolveError) as info:
        f.solve("F", {"m": 1e308, "a": 10.0})
    assert info.value.code == "not_finite"


def test_solve_no_solver_raises_with_code():
    f = Formula(key="x", name_key="formula.x", expression="y = x",
                variables=(Variable("y", "var.y"), Variable("x", "var.x")),
                solvers={"y": lambda v: v["x"]})
    with pytest.raises(SolveError) as info:
        f.solve("x", {"y": 1})  # no solver for x
    assert info.value.code == "no_solver"


def test_solvable_symbols_listed():
    f = _find("waves", "photon_energy")
    assert set(f.solvable_symbols) == {"E", "f"}


def test_variables_carry_keys_not_display_text():
    f = _find("mechanics", "newton_2")
    force = f.variable("F")
    assert force.name_key == "var.force"
    assert force.unit_key == "unit.newton"
    # a dimensionless variable has an empty unit key.
    n1 = _find("waves", "snell").variable("n1")
    assert n1.unit_key == ""
