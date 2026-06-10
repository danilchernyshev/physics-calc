"""Waves and optics formulas."""

from __future__ import annotations

import math

from study_calc.core.formula import Formula, SolveError, Variable

# Planck constant (J·s) and speed of light in vacuum (m/s).
PLANCK = 6.62607015e-34
LIGHT_SPEED = 299_792_458.0


# --- Snell's law: trigonometry reads better as named functions. ---

def _snell_n1(v):
    return v["n2"] * math.sin(math.radians(v["theta2"])) / math.sin(math.radians(v["theta1"]))


def _snell_n2(v):
    return v["n1"] * math.sin(math.radians(v["theta1"])) / math.sin(math.radians(v["theta2"]))


def _snell_theta1(v):
    ratio = v["n2"] * math.sin(math.radians(v["theta2"])) / v["n1"]
    if not -1.0 <= ratio <= 1.0:
        raise SolveError("total_internal_reflection")
    return math.degrees(math.asin(ratio))


def _snell_theta2(v):
    ratio = v["n1"] * math.sin(math.radians(v["theta1"])) / v["n2"]
    if not -1.0 <= ratio <= 1.0:
        raise SolveError("total_internal_reflection")
    return math.degrees(math.asin(ratio))


FORMULAS: list[Formula] = [
    Formula(
        key="wave_speed",
        name_key="formula.wave_speed",
        expression="v = λ · f",
        variables=(
            Variable("v", "var.wave_speed", "unit.meter_per_second"),
            Variable("lam", "var.wavelength", "unit.meter"),
            Variable("f", "var.frequency", "unit.hertz"),
        ),
        solvers={
            "v": lambda v: v["lam"] * v["f"],
            "lam": lambda v: v["v"] / v["f"],
            "f": lambda v: v["v"] / v["lam"],
        },
    ),
    Formula(
        key="period_frequency",
        name_key="formula.period_frequency",
        expression="T = 1 / f",
        variables=(
            Variable("T", "var.period", "unit.second"),
            Variable("f", "var.frequency", "unit.hertz"),
        ),
        solvers={
            "T": lambda v: 1.0 / v["f"],
            "f": lambda v: 1.0 / v["T"],
        },
    ),
    Formula(
        key="photon_energy",
        name_key="formula.photon_energy",
        expression="E = h · f",
        variables=(
            Variable("E", "var.photon_energy", "unit.joule"),
            Variable("f", "var.frequency", "unit.hertz"),
        ),
        solvers={
            "E": lambda v: PLANCK * v["f"],
            "f": lambda v: v["E"] / PLANCK,
        },
    ),
    Formula(
        key="wavelength_light",
        name_key="formula.wavelength_light",
        expression="λ = c / f",
        variables=(
            Variable("lam", "var.wavelength", "unit.meter"),
            Variable("f", "var.frequency", "unit.hertz"),
        ),
        solvers={
            "lam": lambda v: LIGHT_SPEED / v["f"],
            "f": lambda v: LIGHT_SPEED / v["lam"],
        },
    ),
    Formula(
        key="snell",
        name_key="formula.snell",
        expression="n₁ · sin θ₁ = n₂ · sin θ₂",
        variables=(
            Variable("n1", "var.refractive_index_1"),
            Variable("theta1", "var.angle_incidence", "unit.degree"),
            Variable("n2", "var.refractive_index_2"),
            Variable("theta2", "var.angle_refraction", "unit.degree"),
        ),
        solvers={
            "n1": _snell_n1,
            "n2": _snell_n2,
            "theta1": _snell_theta1,
            "theta2": _snell_theta2,
        },
    ),
]
