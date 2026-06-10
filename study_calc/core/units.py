"""Unit converter.

Categories and units are identified by stable, language-neutral ids
(``"length"``, ``"meter"``, ``"celsius"``, ...). Display names are resolved by
:mod:`study_calc.i18n` via the ``category.<id>`` and ``unit.<id>`` keys; this
module deals only with the physics.

Most quantities convert through a common SI base unit with a linear factor.
Temperature is special (the zero point is offset), so it has explicit
to/from-kelvin functions instead.
"""

from __future__ import annotations

import math
from typing import Callable, Dict


class ConversionError(ValueError):
    """Unknown category or unit. Carries a ``code`` and ``params`` for i18n."""

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


# Linear categories: unit id -> factor to the SI base unit of the category.
_LINEAR: Dict[str, Dict[str, float]] = {
    "length": {
        "meter": 1.0,
        "kilometer": 1000.0,
        "centimeter": 0.01,
        "millimeter": 0.001,
        "mile": 1609.344,
        "foot": 0.3048,
        "inch": 0.0254,
    },
    "mass": {
        "kilogram": 1.0,
        "gram": 0.001,
        "milligram": 1e-6,
        "tonne": 1000.0,
        "pound": 0.45359237,
        "ounce": 0.028349523125,
    },
    "time": {
        "second": 1.0,
        "millisecond": 0.001,
        "minute": 60.0,
        "hour": 3600.0,
        "day": 86400.0,
    },
    "speed": {
        "meter_per_second": 1.0,
        "km_per_hour": 1000.0 / 3600.0,
        "mph": 1609.344 / 3600.0,
        "knot": 1852.0 / 3600.0,
    },
    "energy": {
        "joule": 1.0,
        "kilojoule": 1000.0,
        "calorie": 4.184,
        "kilocalorie": 4184.0,
        "kwh": 3.6e6,
        "ev": 1.602176634e-19,
    },
    "pressure": {
        "pascal": 1.0,
        "kilopascal": 1000.0,
        "bar": 1e5,
        "atm": 101325.0,
        "mmhg": 133.322387415,
    },
    "force": {
        "newton": 1.0,
        "kilonewton": 1000.0,
        "dyne": 1e-5,
        "kgf": 9.80665,
    },
    # Angle (MHF4U: radian measure). Base unit is the radian; a full turn is
    # 2π rad = 360° = 400 gradians.
    "angle": {
        "radian": 1.0,
        "degree": math.pi / 180.0,
        "gradian": math.pi / 200.0,
    },
}

# Temperature: unit id -> (to kelvin, from kelvin).
_TEMPERATURE: Dict[str, tuple[Callable[[float], float], Callable[[float], float]]] = {
    "celsius": (lambda c: c + 273.15, lambda k: k - 273.15),
    "kelvin": (lambda k: k, lambda k: k),
    "fahrenheit": (lambda f: (f - 32.0) * 5.0 / 9.0 + 273.15,
                   lambda k: (k - 273.15) * 9.0 / 5.0 + 32.0),
}


def categories() -> list[str]:
    """Ids of all available quantity categories."""
    return list(_LINEAR.keys()) + ["temperature"]


def units_of(category: str) -> list[str]:
    """Unit ids within a category."""
    if category == "temperature":
        return list(_TEMPERATURE.keys())
    if category not in _LINEAR:
        raise ConversionError("unknown_category", category=category)
    return list(_LINEAR[category].keys())


def convert(value: float, from_unit: str, to_unit: str, category: str) -> float:
    """Convert ``value`` from ``from_unit`` to ``to_unit`` within ``category``."""
    if category == "temperature":
        return _convert_temperature(value, from_unit, to_unit)

    table = _LINEAR.get(category)
    if table is None:
        raise ConversionError("unknown_category", category=category)
    if from_unit not in table or to_unit not in table:
        raise ConversionError("unknown_unit", from_unit=from_unit, to_unit=to_unit)
    base = value * table[from_unit]      # into the SI base unit
    return base / table[to_unit]         # from the base unit into the target


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in _TEMPERATURE or to_unit not in _TEMPERATURE:
        raise ConversionError("unknown_unit", from_unit=from_unit, to_unit=to_unit)
    to_kelvin, _ = _TEMPERATURE[from_unit]
    _, from_kelvin = _TEMPERATURE[to_unit]
    return from_kelvin(to_kelvin(value))
