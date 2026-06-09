"""Формулы волн и оптики."""

from __future__ import annotations

import math

from physics_calc.core.formula import Formula, Variable

# Постоянная Планка (Дж·с) и скорость света в вакууме (м/с).
PLANCK = 6.62607015e-34
LIGHT_SPEED = 299_792_458.0


# --- Закон Снеллиуса: тригонометрия удобнее в отдельных функциях. ---

def _snell_n1(v):
    return v["n2"] * math.sin(math.radians(v["theta2"])) / math.sin(math.radians(v["theta1"]))


def _snell_n2(v):
    return v["n1"] * math.sin(math.radians(v["theta1"])) / math.sin(math.radians(v["theta2"]))


def _snell_theta1(v):
    ratio = v["n2"] * math.sin(math.radians(v["theta2"])) / v["n1"]
    if not -1.0 <= ratio <= 1.0:
        raise ValueError("полное внутреннее отражение — угол не существует")
    return math.degrees(math.asin(ratio))


def _snell_theta2(v):
    ratio = v["n1"] * math.sin(math.radians(v["theta1"])) / v["n2"]
    if not -1.0 <= ratio <= 1.0:
        raise ValueError("полное внутреннее отражение — угол не существует")
    return math.degrees(math.asin(ratio))


FORMULAS: list[Formula] = [
    Formula(
        key="wave_speed",
        name="Скорость волны",
        expression="v = λ · f",
        variables=(
            Variable("v", "Скорость волны", "м/с"),
            Variable("lam", "Длина волны", "м"),
            Variable("f", "Частота", "Гц"),
        ),
        solvers={
            "v": lambda v: v["lam"] * v["f"],
            "lam": lambda v: v["v"] / v["f"],
            "f": lambda v: v["v"] / v["lam"],
        },
    ),
    Formula(
        key="period_frequency",
        name="Период и частота",
        expression="T = 1 / f",
        variables=(
            Variable("T", "Период", "с"),
            Variable("f", "Частота", "Гц"),
        ),
        solvers={
            "T": lambda v: 1.0 / v["f"],
            "f": lambda v: 1.0 / v["T"],
        },
    ),
    Formula(
        key="photon_energy",
        name="Энергия фотона",
        expression="E = h · f",
        variables=(
            Variable("E", "Энергия фотона", "Дж"),
            Variable("f", "Частота", "Гц"),
        ),
        solvers={
            "E": lambda v: PLANCK * v["f"],
            "f": lambda v: v["E"] / PLANCK,
        },
    ),
    Formula(
        key="wavelength_light",
        name="Длина волны света",
        expression="λ = c / f",
        variables=(
            Variable("lam", "Длина волны", "м"),
            Variable("f", "Частота", "Гц"),
        ),
        solvers={
            "lam": lambda v: LIGHT_SPEED / v["f"],
            "f": lambda v: LIGHT_SPEED / v["lam"],
        },
    ),
    Formula(
        key="snell",
        name="Закон Снеллиуса (показатель преломления)",
        expression="n₁ · sin θ₁ = n₂ · sin θ₂",
        variables=(
            Variable("n1", "Показатель преломления среды 1", ""),
            Variable("theta1", "Угол падения", "°"),
            Variable("n2", "Показатель преломления среды 2", ""),
            Variable("theta2", "Угол преломления", "°"),
        ),
        solvers={
            "n1": _snell_n1,
            "n2": _snell_n2,
            "theta1": _snell_theta1,
            "theta2": _snell_theta2,
        },
    ),
]
