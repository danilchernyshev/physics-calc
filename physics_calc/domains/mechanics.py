"""Формулы механики."""

from __future__ import annotations

from physics_calc.core.formula import Formula, Variable

FORMULAS: list[Formula] = [
    Formula(
        key="newton_2",
        name="Второй закон Ньютона",
        expression="F = m · a",
        variables=(
            Variable("F", "Сила", "Н"),
            Variable("m", "Масса", "кг"),
            Variable("a", "Ускорение", "м/с²"),
        ),
        solvers={
            "F": lambda v: v["m"] * v["a"],
            "m": lambda v: v["F"] / v["a"],
            "a": lambda v: v["F"] / v["m"],
        },
    ),
    Formula(
        key="velocity",
        name="Скорость при равноускоренном движении",
        expression="v = v₀ + a · t",
        variables=(
            Variable("v", "Конечная скорость", "м/с"),
            Variable("v0", "Начальная скорость", "м/с"),
            Variable("a", "Ускорение", "м/с²"),
            Variable("t", "Время", "с"),
        ),
        solvers={
            "v": lambda v: v["v0"] + v["a"] * v["t"],
            "v0": lambda v: v["v"] - v["a"] * v["t"],
            "a": lambda v: (v["v"] - v["v0"]) / v["t"],
            "t": lambda v: (v["v"] - v["v0"]) / v["a"],
        },
    ),
    Formula(
        key="momentum",
        name="Импульс тела",
        expression="p = m · v",
        variables=(
            Variable("p", "Импульс", "кг·м/с"),
            Variable("m", "Масса", "кг"),
            Variable("v", "Скорость", "м/с"),
        ),
        solvers={
            "p": lambda v: v["m"] * v["v"],
            "m": lambda v: v["p"] / v["v"],
            "v": lambda v: v["p"] / v["m"],
        },
    ),
    Formula(
        key="kinetic_energy",
        name="Кинетическая энергия",
        expression="E = ½ · m · v²",
        variables=(
            Variable("E", "Кинетическая энергия", "Дж"),
            Variable("m", "Масса", "кг"),
            Variable("v", "Скорость", "м/с"),
        ),
        solvers={
            "E": lambda v: 0.5 * v["m"] * v["v"] ** 2,
            "m": lambda v: 2.0 * v["E"] / v["v"] ** 2,
            "v": lambda v: (2.0 * v["E"] / v["m"]) ** 0.5,
        },
    ),
    Formula(
        key="potential_energy",
        name="Потенциальная энергия в поле тяжести",
        expression="E = m · g · h",
        variables=(
            Variable("E", "Потенциальная энергия", "Дж"),
            Variable("m", "Масса", "кг"),
            Variable("g", "Ускорение свободного падения", "м/с²"),
            Variable("h", "Высота", "м"),
        ),
        solvers={
            "E": lambda v: v["m"] * v["g"] * v["h"],
            "m": lambda v: v["E"] / (v["g"] * v["h"]),
            "g": lambda v: v["E"] / (v["m"] * v["h"]),
            "h": lambda v: v["E"] / (v["m"] * v["g"]),
        },
    ),
    Formula(
        key="work",
        name="Механическая работа",
        expression="A = F · s",
        variables=(
            Variable("A", "Работа", "Дж"),
            Variable("F", "Сила", "Н"),
            Variable("s", "Перемещение", "м"),
        ),
        solvers={
            "A": lambda v: v["F"] * v["s"],
            "F": lambda v: v["A"] / v["s"],
            "s": lambda v: v["A"] / v["F"],
        },
    ),
    Formula(
        key="power",
        name="Механическая мощность",
        expression="P = A / t",
        variables=(
            Variable("P", "Мощность", "Вт"),
            Variable("A", "Работа", "Дж"),
            Variable("t", "Время", "с"),
        ),
        solvers={
            "P": lambda v: v["A"] / v["t"],
            "A": lambda v: v["P"] * v["t"],
            "t": lambda v: v["A"] / v["P"],
        },
    ),
]
