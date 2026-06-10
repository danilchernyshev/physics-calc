"""Chemistry formulas (SCH4U) — solved with the shared :class:`Formula` model.

These reuse the same "fill every variable but one" engine as the physics
sections, so the GUI renders them with the identical calculator panel. They are
grouped into two sections (solutions / acids & bases) and surfaced under the
Chemistry subject in :mod:`study_calc.navigation`.
"""

from __future__ import annotations

import math

from study_calc.core.formula import Formula, Variable

_SOLUTIONS: list[Formula] = [
    Formula(
        key="molarity",
        name_key="formula.molarity",
        expression="c = n / V",
        variables=(
            Variable("c", "var.concentration", "unit.mol_per_litre"),
            Variable("n", "var.amount_of_substance", "unit.mol"),
            Variable("V", "var.volume", "unit.litre"),
        ),
        solvers={
            "c": lambda v: v["n"] / v["V"],
            "n": lambda v: v["c"] * v["V"],
            "V": lambda v: v["n"] / v["c"],
        },
    ),
    Formula(
        key="dilution",
        name_key="formula.dilution",
        expression="c₁ · V₁ = c₂ · V₂",
        variables=(
            Variable("c1", "var.concentration", "unit.mol_per_litre"),
            Variable("V1", "var.volume", "unit.litre"),
            Variable("c2", "var.concentration", "unit.mol_per_litre"),
            Variable("V2", "var.volume", "unit.litre"),
        ),
        solvers={
            "c1": lambda v: v["c2"] * v["V2"] / v["V1"],
            "V1": lambda v: v["c2"] * v["V2"] / v["c1"],
            "c2": lambda v: v["c1"] * v["V1"] / v["V2"],
            "V2": lambda v: v["c1"] * v["V1"] / v["c2"],
        },
    ),
    Formula(
        key="moles",
        name_key="formula.moles",
        expression="n = m / M",
        variables=(
            Variable("n", "var.amount_of_substance", "unit.mol"),
            Variable("m", "var.mass", "unit.gram"),
            Variable("M", "var.molar_mass", "unit.gram_per_mol"),
        ),
        solvers={
            "n": lambda v: v["m"] / v["M"],
            "m": lambda v: v["n"] * v["M"],
            "M": lambda v: v["m"] / v["n"],
        },
    ),
]

_ACID_BASE: list[Formula] = [
    Formula(
        key="ph",
        name_key="formula.ph",
        expression="pH = −log₁₀[H⁺]",
        variables=(
            Variable("pH", "var.ph"),
            Variable("H", "var.hydrogen_ion", "unit.mol_per_litre"),
        ),
        solvers={
            "pH": lambda v: -math.log10(v["H"]),
            "H": lambda v: 10 ** (-v["pH"]),
        },
    ),
]

SECTIONS = {
    "chem_solutions": _SOLUTIONS,
    "chem_acid_base": _ACID_BASE,
}
