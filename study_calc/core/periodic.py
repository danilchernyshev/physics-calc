"""Periodic-table data and chemical-formula computations (SCH4U Chemistry).

This is the chemistry counterpart to :mod:`study_calc.core.vectors`: a
UI- and language-neutral engine built on nothing but the standard library. It
loads the periodic table from the separate ``study_calc/data/elements.json``
data file and offers three things:

- :func:`molar_mass` — parse a chemical formula (``"Ca(OH)2"``, ``"H2O"``,
  nested parentheses) and sum the standard atomic weights.
- :func:`composition` — the element → atom-count breakdown of a formula.
- :func:`balance` — balance a chemical equation by finding the integer null
  vector of its element-count matrix (exact, via :class:`~fractions.Fraction`).

Like the rest of :mod:`study_calc.core`, failures raise a :class:`ChemError`
carrying a stable machine ``code`` plus params, so the GUI can render a
localized message. No SymPy, no NumPy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import gcd

from study_calc.resources import resource_path

_DATA_DIR = resource_path("data")


class ChemError(ValueError):
    """A chemistry computation could not be carried out.

    Carries a stable ``code`` (e.g. ``"chem_unknown_element"``) and optional
    ``params`` so the presentation layer can build a localized message.
    """

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


@dataclass(frozen=True)
class Element:
    """One periodic-table entry (see ``study_calc/data/elements.json``)."""

    number: int
    symbol: str
    name: str
    mass: float
    group: int | None
    period: int
    category: str
    xpos: int
    ypos: int


@lru_cache(maxsize=1)
def _elements() -> tuple[Element, ...]:
    raw = json.loads((_DATA_DIR / "elements.json").read_text(encoding="utf-8"))
    return tuple(
        Element(
            number=e["number"],
            symbol=e["symbol"],
            name=e["name"],
            mass=float(e["mass"]),
            group=e.get("group"),
            period=e["period"],
            category=e["category"],
            xpos=e["xpos"],
            ypos=e["ypos"],
        )
        for e in raw
    )


@lru_cache(maxsize=1)
def _by_symbol() -> dict[str, Element]:
    return {e.symbol: e for e in _elements()}


def elements() -> tuple[Element, ...]:
    """All 118 elements, in atomic-number order."""
    return _elements()


def element(symbol: str) -> Element:
    """Look up one element by symbol, or raise :class:`ChemError`."""
    el = _by_symbol().get(symbol)
    if el is None:
        raise ChemError("chem_unknown_element", element=symbol)
    return el


# A formula token: an element symbol (uppercase + optional lowercase letters)
# followed by an optional integer count, or a parenthesis.
_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)|(\()|(\)(\d*))")


def composition(formula: str) -> dict[str, int]:
    """Element → total atom count for ``formula`` (handles nested parentheses).

    Raises :class:`ChemError` with code ``chem_empty`` (blank), ``chem_parse``
    (malformed / unbalanced parentheses) or ``chem_unknown_element``.
    """
    text = formula.replace(" ", "")
    if not text:
        raise ChemError("chem_empty")

    # Stack of partial counts; the last frame is the current parenthesis group.
    stack: list[dict[str, int]] = [{}]
    pos = 0
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None or match.end() == pos:
            raise ChemError("chem_parse", text=formula)
        symbol, count, open_paren, close_paren, close_count = match.groups()
        if open_paren:
            stack.append({})
        elif close_paren is not None:
            if len(stack) == 1:
                raise ChemError("chem_parse", text=formula)
            group = stack.pop()
            multiplier = int(close_count) if close_count else 1
            for sym, n in group.items():
                stack[-1][sym] = stack[-1].get(sym, 0) + n * multiplier
        else:
            element(symbol)  # validate; raises on unknown
            n = int(count) if count else 1
            stack[-1][symbol] = stack[-1].get(symbol, 0) + n
        pos = match.end()

    if len(stack) != 1:
        raise ChemError("chem_parse", text=formula)
    return dict(stack[0])


def molar_mass(formula: str) -> float:
    """Molar mass of ``formula`` in g/mol (sum of standard atomic weights)."""
    return sum(element(sym).mass * n for sym, n in composition(formula).items())


# --- Equation balancing ----------------------------------------------------

_ARROW = re.compile(r"->|=>|=|→|←|⇌|↔")


def _species(side: str) -> list[str]:
    parts = [p.strip() for p in side.split("+")]
    species = [p for p in parts if p]
    if not species:
        raise ChemError("chem_parse", text=side)
    return species


def balance(equation: str) -> str:
    """Balance a chemical equation, returning it with integer coefficients.

    Accepts ``+`` between species and any of ``->``, ``=>``, ``=`` or an arrow
    glyph between the two sides (e.g. ``"CH4 + O2 -> CO2 + H2O"``). Raises
    :class:`ChemError`: ``chem_no_arrow`` (no reactant/product split),
    ``chem_parse``, ``chem_unknown_element`` or ``chem_unbalanceable`` (no
    unique positive-integer solution).
    """
    sides = _ARROW.split(equation)
    if len(sides) != 2:
        raise ChemError("chem_no_arrow")
    reactants, products = _species(sides[0]), _species(sides[1])
    species = reactants + products
    if len(species) < 2:
        raise ChemError("chem_unbalanceable")

    # Composition of every species; product atoms enter the matrix negated so a
    # null vector means "reactant atoms = product atoms" for each element.
    comps = [composition(s) for s in species]
    elems = sorted({e for c in comps for e in c})
    matrix = [
        [
            Fraction(comps[j].get(el, 0)) * (1 if j < len(reactants) else -1)
            for j in range(len(species))
        ]
        for el in elems
    ]

    null = _null_vector(matrix, len(species))
    if null is None:
        raise ChemError("chem_unbalanceable")

    # Scale the rational null vector to the smallest positive integers.
    denominators = [c.denominator for c in null]
    lcm = 1
    for d in denominators:
        lcm = lcm * d // gcd(lcm, d)
    integers = [int(c * lcm) for c in null]
    if integers and integers[0] < 0:
        integers = [-c for c in integers]
    common = 0
    for c in integers:
        common = gcd(common, abs(c))
    if common == 0 or any(c <= 0 for c in integers):
        raise ChemError("chem_unbalanceable")
    coeffs = [c // common for c in integers]

    def _render(items: list[str], offset: int) -> str:
        out = []
        for i, sp in enumerate(items):
            k = coeffs[offset + i]
            out.append(sp if k == 1 else f"{k}{sp}")
        return " + ".join(out)

    return f"{_render(reactants, 0)} -> {_render(products, len(reactants))}"


def _null_vector(matrix: list[list[Fraction]], width: int) -> list[Fraction] | None:
    """Exact one-dimensional null space of ``matrix`` (rows = elements).

    Returns a rational basis vector, or ``None`` if the null space is not exactly
    one-dimensional (no solution, or an under-determined equation).
    """
    rows = [row[:] for row in matrix]
    pivots: list[int] = []
    r = 0
    for col in range(width):
        pivot = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        inv = rows[r][col]
        rows[r] = [v / inv for v in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                factor = rows[i][col]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[r])]
        pivots.append(col)
        r += 1

    free = [c for c in range(width) if c not in pivots]
    if len(free) != 1:
        return None  # unique up to scale only when exactly one free variable

    free_col = free[0]
    vector = [Fraction(0)] * width
    vector[free_col] = Fraction(1)
    for row_index, pivot_col in enumerate(pivots):
        vector[pivot_col] = -rows[row_index][free_col]
    return vector
