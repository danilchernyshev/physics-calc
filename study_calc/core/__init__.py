"""Core: the formula model and the unit converter."""

from study_calc.core.formula import Formula, Variable, SolveError
from study_calc.core.units import convert, categories, units_of, ConversionError

__all__ = [
    "Formula",
    "Variable",
    "SolveError",
    "convert",
    "categories",
    "units_of",
    "ConversionError",
]
