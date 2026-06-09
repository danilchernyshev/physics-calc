"""Thermodynamics formulas."""

from __future__ import annotations

from physics_calc.core.formula import Formula, Variable

# Universal gas constant, J/(mol·K).
R = 8.314462618

FORMULAS: list[Formula] = [
    Formula(
        key="heat",
        name_key="formula.heat",
        expression="Q = c · m · ΔT",
        variables=(
            Variable("Q", "var.heat", "unit.joule"),
            Variable("c", "var.specific_heat", "unit.j_kg_k"),
            Variable("m", "var.mass", "unit.kilogram"),
            Variable("dT", "var.temperature_change", "unit.kelvin"),
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
        name_key="formula.ideal_gas",
        expression="P · V = n · R · T",
        variables=(
            Variable("P", "var.pressure", "unit.pascal"),
            Variable("V", "var.volume", "unit.m3"),
            Variable("n", "var.amount_of_substance", "unit.mol"),
            Variable("T", "var.temperature", "unit.kelvin"),
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
        name_key="formula.carnot_efficiency",
        expression="η = 1 − T_c / T_h",
        variables=(
            Variable("eta", "var.efficiency", "unit.ratio"),
            Variable("Tc", "var.cold_temp", "unit.kelvin"),
            Variable("Th", "var.hot_temp", "unit.kelvin"),
        ),
        solvers={
            "eta": lambda v: 1.0 - v["Tc"] / v["Th"],
            "Tc": lambda v: v["Th"] * (1.0 - v["eta"]),
            "Th": lambda v: v["Tc"] / (1.0 - v["eta"]),
        },
    ),
    Formula(
        key="linear_expansion",
        name_key="formula.linear_expansion",
        expression="ΔL = α · L₀ · ΔT",
        variables=(
            Variable("dL", "var.length_change", "unit.meter"),
            Variable("alpha", "var.expansion_coefficient", "unit.per_k"),
            Variable("L0", "var.initial_length", "unit.meter"),
            Variable("dT", "var.temperature_change", "unit.kelvin"),
        ),
        solvers={
            "dL": lambda v: v["alpha"] * v["L0"] * v["dT"],
            "alpha": lambda v: v["dL"] / (v["L0"] * v["dT"]),
            "L0": lambda v: v["dL"] / (v["alpha"] * v["dT"]),
            "dT": lambda v: v["dL"] / (v["alpha"] * v["L0"]),
        },
    ),
]
