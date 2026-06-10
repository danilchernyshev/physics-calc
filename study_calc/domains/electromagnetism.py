"""Electromagnetism formulas."""

from __future__ import annotations

from study_calc.core.formula import Formula, Variable

# Coulomb constant, N·m²/C².
K_COULOMB = 8.9875517873681764e9

FORMULAS: list[Formula] = [
    Formula(
        key="ohm",
        name_key="formula.ohm",
        expression="U = I · R",
        variables=(
            Variable("U", "var.voltage", "unit.volt"),
            Variable("I", "var.current", "unit.ampere"),
            Variable("R", "var.resistance", "unit.ohm"),
        ),
        solvers={
            "U": lambda v: v["I"] * v["R"],
            "I": lambda v: v["U"] / v["R"],
            "R": lambda v: v["U"] / v["I"],
        },
    ),
    Formula(
        key="electric_power",
        name_key="formula.electric_power",
        expression="P = U · I",
        variables=(
            Variable("P", "var.power", "unit.watt"),
            Variable("U", "var.voltage", "unit.volt"),
            Variable("I", "var.current", "unit.ampere"),
        ),
        solvers={
            "P": lambda v: v["U"] * v["I"],
            "U": lambda v: v["P"] / v["I"],
            "I": lambda v: v["P"] / v["U"],
        },
    ),
    Formula(
        key="coulomb",
        name_key="formula.coulomb",
        expression="F = k · q₁ · q₂ / r²",
        variables=(
            Variable("F", "var.interaction_force", "unit.newton"),
            Variable("q1", "var.charge_q1", "unit.coulomb"),
            Variable("q2", "var.charge_q2", "unit.coulomb"),
            Variable("r", "var.distance", "unit.meter"),
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
        name_key="formula.capacitor_charge",
        expression="Q = C · U",
        variables=(
            Variable("Q", "var.charge", "unit.coulomb"),
            Variable("C", "var.capacitance", "unit.farad"),
            Variable("U", "var.voltage", "unit.volt"),
        ),
        solvers={
            "Q": lambda v: v["C"] * v["U"],
            "C": lambda v: v["Q"] / v["U"],
            "U": lambda v: v["Q"] / v["C"],
        },
    ),
    Formula(
        key="capacitor_energy",
        name_key="formula.capacitor_energy",
        expression="W = ½ · C · U²",
        variables=(
            Variable("W", "var.energy", "unit.joule"),
            Variable("C", "var.capacitance", "unit.farad"),
            Variable("U", "var.voltage", "unit.volt"),
        ),
        solvers={
            "W": lambda v: 0.5 * v["C"] * v["U"] ** 2,
            "C": lambda v: 2.0 * v["W"] / v["U"] ** 2,
            "U": lambda v: (2.0 * v["W"] / v["C"]) ** 0.5,
        },
    ),
    Formula(
        key="resistance_series",
        name_key="formula.resistance_series",
        expression="R = ρ · L / S",
        variables=(
            Variable("R", "var.resistance", "unit.ohm"),
            Variable("rho", "var.resistivity", "unit.ohm_m"),
            Variable("L", "var.length", "unit.meter"),
            Variable("S", "var.cross_section", "unit.m2"),
        ),
        solvers={
            "R": lambda v: v["rho"] * v["L"] / v["S"],
            "rho": lambda v: v["R"] * v["S"] / v["L"],
            "L": lambda v: v["R"] * v["S"] / v["rho"],
            "S": lambda v: v["rho"] * v["L"] / v["R"],
        },
    ),
]
