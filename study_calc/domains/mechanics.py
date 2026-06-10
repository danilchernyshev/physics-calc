"""Mechanics formulas."""

from __future__ import annotations

from study_calc.core.formula import Formula, Variable

FORMULAS: list[Formula] = [
    Formula(
        key="newton_2",
        name_key="formula.newton_2",
        expression="F = m · a",
        variables=(
            Variable("F", "var.force", "unit.newton"),
            Variable("m", "var.mass", "unit.kilogram"),
            Variable("a", "var.acceleration", "unit.m_s2"),
        ),
        solvers={
            "F": lambda v: v["m"] * v["a"],
            "m": lambda v: v["F"] / v["a"],
            "a": lambda v: v["F"] / v["m"],
        },
    ),
    Formula(
        key="velocity",
        name_key="formula.velocity",
        expression="v = v₀ + a · t",
        variables=(
            Variable("v", "var.final_velocity", "unit.meter_per_second"),
            Variable("v0", "var.initial_velocity", "unit.meter_per_second"),
            Variable("a", "var.acceleration", "unit.m_s2"),
            Variable("t", "var.time", "unit.second"),
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
        name_key="formula.momentum",
        expression="p = m · v",
        variables=(
            Variable("p", "var.momentum", "unit.kg_m_s"),
            Variable("m", "var.mass", "unit.kilogram"),
            Variable("v", "var.velocity", "unit.meter_per_second"),
        ),
        solvers={
            "p": lambda v: v["m"] * v["v"],
            "m": lambda v: v["p"] / v["v"],
            "v": lambda v: v["p"] / v["m"],
        },
    ),
    Formula(
        key="kinetic_energy",
        name_key="formula.kinetic_energy",
        expression="E = ½ · m · v²",
        variables=(
            Variable("E", "var.kinetic_energy", "unit.joule"),
            Variable("m", "var.mass", "unit.kilogram"),
            Variable("v", "var.velocity", "unit.meter_per_second"),
        ),
        solvers={
            "E": lambda v: 0.5 * v["m"] * v["v"] ** 2,
            "m": lambda v: 2.0 * v["E"] / v["v"] ** 2,
            "v": lambda v: (2.0 * v["E"] / v["m"]) ** 0.5,
        },
    ),
    Formula(
        key="potential_energy",
        name_key="formula.potential_energy",
        expression="E = m · g · h",
        variables=(
            Variable("E", "var.potential_energy", "unit.joule"),
            Variable("m", "var.mass", "unit.kilogram"),
            Variable("g", "var.gravity", "unit.m_s2"),
            Variable("h", "var.height", "unit.meter"),
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
        name_key="formula.work",
        expression="A = F · s",
        variables=(
            Variable("A", "var.work", "unit.joule"),
            Variable("F", "var.force", "unit.newton"),
            Variable("s", "var.displacement", "unit.meter"),
        ),
        solvers={
            "A": lambda v: v["F"] * v["s"],
            "F": lambda v: v["A"] / v["s"],
            "s": lambda v: v["A"] / v["F"],
        },
    ),
    Formula(
        key="power",
        name_key="formula.power",
        expression="P = A / t",
        variables=(
            Variable("P", "var.power", "unit.watt"),
            Variable("A", "var.work", "unit.joule"),
            Variable("t", "var.time", "unit.second"),
        ),
        solvers={
            "P": lambda v: v["A"] / v["t"],
            "A": lambda v: v["P"] * v["t"],
            "t": lambda v: v["A"] / v["P"],
        },
    ),
]
