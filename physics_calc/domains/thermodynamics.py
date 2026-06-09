"""Формулы термодинамики."""

from __future__ import annotations

from physics_calc.core.formula import Formula, Variable

# Универсальная газовая постоянная, Дж/(моль·К).
R = 8.314462618

FORMULAS: list[Formula] = [
    Formula(
        key="heat",
        name="Количество теплоты",
        expression="Q = c · m · ΔT",
        variables=(
            Variable("Q", "Количество теплоты", "Дж"),
            Variable("c", "Удельная теплоёмкость", "Дж/(кг·К)"),
            Variable("m", "Масса", "кг"),
            Variable("dT", "Изменение температуры", "К"),
        ),
        solvers={
            "Q": lambda v: v["c"] * v["m"] * v["dT"],
            "c": lambda v: v["Q"] / (v["m"] * v["dT"]),
            "m": lambda v: v["Q"] / (v["c"] * v["dT"]),
            "dT": lambda v: v["Q"] / (v["c"] * v["m"]),
        },
    ),
    Formula(
        key="ideal_gas",
        name="Уравнение состояния идеального газа",
        expression="P · V = n · R · T",
        variables=(
            Variable("P", "Давление", "Па"),
            Variable("V", "Объём", "м³"),
            Variable("n", "Количество вещества", "моль"),
            Variable("T", "Температура", "К"),
        ),
        solvers={
            "P": lambda v: v["n"] * R * v["T"] / v["V"],
            "V": lambda v: v["n"] * R * v["T"] / v["P"],
            "n": lambda v: v["P"] * v["V"] / (R * v["T"]),
            "T": lambda v: v["P"] * v["V"] / (v["n"] * R),
        },
    ),
    Formula(
        key="carnot_efficiency",
        name="КПД цикла Карно",
        expression="η = 1 − T_х / T_г",
        variables=(
            Variable("eta", "КПД", "доля"),
            Variable("Tc", "Температура холодильника", "К"),
            Variable("Th", "Температура нагревателя", "К"),
        ),
        solvers={
            "eta": lambda v: 1.0 - v["Tc"] / v["Th"],
            "Tc": lambda v: v["Th"] * (1.0 - v["eta"]),
            "Th": lambda v: v["Tc"] / (1.0 - v["eta"]),
        },
    ),
    Formula(
        key="linear_expansion",
        name="Линейное тепловое расширение",
        expression="ΔL = α · L₀ · ΔT",
        variables=(
            Variable("dL", "Изменение длины", "м"),
            Variable("alpha", "Коэффициент расширения", "1/К"),
            Variable("L0", "Начальная длина", "м"),
            Variable("dT", "Изменение температуры", "К"),
        ),
        solvers={
            "dL": lambda v: v["alpha"] * v["L0"] * v["dT"],
            "alpha": lambda v: v["dL"] / (v["L0"] * v["dT"]),
            "L0": lambda v: v["dL"] / (v["alpha"] * v["dT"]),
            "dT": lambda v: v["dL"] / (v["alpha"] * v["L0"]),
        },
    ),
]
