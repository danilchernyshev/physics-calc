"""Тесты движка формул и наборов по разделам."""

import math

import pytest

from physics_calc.core.formula import Formula, Variable, SolveError
from physics_calc.domains import SECTIONS


def _find(section: str, key: str) -> Formula:
    for formula in SECTIONS[section]:
        if formula.key == key:
            return formula
    raise AssertionError(f"формула {key} не найдена в разделе {section}")


def test_newton_solves_each_variable():
    f = _find("Механика", "newton_2")
    assert f.solve("F", {"m": 10, "a": 2}) == pytest.approx(20)
    assert f.solve("m", {"F": 20, "a": 2}) == pytest.approx(10)
    assert f.solve("a", {"F": 20, "m": 10}) == pytest.approx(2)


def test_kinetic_energy_roundtrip():
    f = _find("Механика", "kinetic_energy")
    e = f.solve("E", {"m": 4, "v": 3})
    assert e == pytest.approx(18)
    assert f.solve("v", {"E": e, "m": 4}) == pytest.approx(3)


def test_ideal_gas():
    f = _find("Термодинамика", "ideal_gas")
    # 1 моль при 273.15 К и 101325 Па занимает ~0.022414 м³ (22.414 л).
    v = f.solve("V", {"P": 101325, "n": 1, "T": 273.15})
    assert v == pytest.approx(0.022414, rel=1e-3)


def test_ohm_law():
    f = _find("Электромагнетизм", "ohm")
    assert f.solve("U", {"I": 2, "R": 5}) == pytest.approx(10)
    assert f.solve("R", {"U": 10, "I": 2}) == pytest.approx(5)


def test_wave_speed():
    f = _find("Волны и оптика", "wave_speed")
    assert f.solve("v", {"lam": 2, "f": 50}) == pytest.approx(100)


def test_snell_law():
    f = _find("Волны и оптика", "snell")
    # из воздуха (n=1) в стекло (n=1.5), угол падения 30°.
    theta2 = f.solve("theta2", {"n1": 1.0, "theta1": 30.0, "n2": 1.5})
    assert math.sin(math.radians(30)) == pytest.approx(1.5 * math.sin(math.radians(theta2)))


def test_solve_missing_variable_raises():
    f = _find("Механика", "newton_2")
    with pytest.raises(SolveError):
        f.solve("F", {"m": 10})  # нет «a»


def test_solve_division_by_zero_raises():
    f = _find("Механика", "newton_2")
    with pytest.raises(SolveError):
        f.solve("a", {"F": 20, "m": 0})


def test_solvable_symbols_listed():
    f = _find("Волны и оптика", "photon_energy")
    assert set(f.solvable_symbols) == {"E", "f"}


def test_variable_label_with_and_without_unit():
    assert Variable("F", "Сила", "Н").label == "Сила (F, Н)"
    assert Variable("n1", "Показатель", "").label == "Показатель (n1)"
