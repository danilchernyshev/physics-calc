"""Core: the formula model and the unit converter."""

from physics_calc.core.formula import Formula, Variable, SolveError
from physics_calc.core.units import convert, categories, units_of, ConversionError

__all__ = [
    "Formula",
    "Variable",
    "SolveError",
    "convert",
    "categories",
    "units_of",
    "ConversionError",
]
