"""Формулы электромагнетизма."""

from __future__ import annotations

from physics_calc.core.formula import Formula, Variable

# Постоянная Кулона, Н·м²/Кл².
K_COULOMB = 8.9875517873681764e9

FORMULAS: list[Formula] = [
    Formula(
        key="ohm",
        name="Закон Ома",
        expression="U = I · R",
        variables=(
            Variable("U", "Напряжение", "В"),
            Variable("I", "Сила тока", "А"),
            Variable("R", "Сопротивление", "Ом"),
        ),
        solvers={
            "U": lambda v: v["I"] * v["R"],
            "I": lambda v: v["U"] / v["R"],
            "R": lambda v: v["U"] / v["I"],
        },
    ),
    Formula(
        key="electric_power",
        name="Электрическая мощность",
        expression="P = U · I",
        variables=(
            Variable("P", "Мощность", "Вт"),
            Variable("U", "Напряжение", "В"),
            Variable("I", "Сила тока", "А"),
        ),
        solvers={
            "P": lambda v: v["U"] * v["I"],
            "U": lambda v: v["P"] / v["I"],
            "I": lambda v: v["P"] / v["U"],
        },
    ),
    Formula(
        key="coulomb",
        name="Закон Кулона",
        expression="F = k · q₁ · q₂ / r²",
        variables=(
            Variable("F", "Сила взаимодействия", "Н"),
            Variable("q1", "Первый заряд", "Кл"),
            Variable("q2", "Второй заряд", "Кл"),
            Variable("r", "Расстояние", "м"),
        ),
        solvers={
            "F": lambda v: K_COULOMB * v["q1"] * v["q2"] / v["r"] ** 2,
            "q1": lambda v: v["F"] * v["r"] ** 2 / (K_COULOMB * v["q2"]),
            "q2": lambda v: v["F"] * v["r"] ** 2 / (K_COULOMB * v["q1"]),
            "r": lambda v: (K_COULOMB * v["q1"] * v["q2"] / v["F"]) ** 0.5,
        },
    ),
    Formula(
        key="capacitor_charge",
        name="Заряд конденсатора",
        expression="Q = C · U",
        variables=(
            Variable("Q", "Заряд", "Кл"),
            Variable("C", "Ёмкость", "Ф"),
            Variable("U", "Напряжение", "В"),
        ),
        solvers={
            "Q": lambda v: v["C"] * v["U"],
            "C": lambda v: v["Q"] / v["U"],
            "U": lambda v: v["Q"] / v["C"],
        },
    ),
    Formula(
        key="capacitor_energy",
        name="Энергия конденсатора",
        expression="W = ½ · C · U²",
        variables=(
            Variable("W", "Энергия", "Дж"),
            Variable("C", "Ёмкость", "Ф"),
            Variable("U", "Напряжение", "В"),
        ),
        solvers={
            "W": lambda v: 0.5 * v["C"] * v["U"] ** 2,
            "C": lambda v: 2.0 * v["W"] / v["U"] ** 2,
            "U": lambda v: (2.0 * v["W"] / v["C"]) ** 0.5,
        },
    ),
    Formula(
        key="resistance_series",
        name="Сопротивление проводника",
        expression="R = ρ · L / S",
        variables=(
            Variable("R", "Сопротивление", "Ом"),
            Variable("rho", "Удельное сопротивление", "Ом·м"),
            Variable("L", "Длина", "м"),
            Variable("S", "Площадь сечения", "м²"),
        ),
        solvers={
            "R": lambda v: v["rho"] * v["L"] / v["S"],
            "rho": lambda v: v["R"] * v["S"] / v["L"],
            "L": lambda v: v["R"] * v["S"] / v["rho"],
            "S": lambda v: v["rho"] * v["L"] / v["R"],
        },
    ),
]
