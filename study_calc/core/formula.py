"""Physics formula model with solving for any variable.

Calculator UX idea: the user fills every variable of a formula except one, and
the program computes the missing one. To make that work for *any* variable,
each formula carries a dict of "solvers" — one function per variable that can be
expressed through the others.

Domain objects stay UI-agnostic: they hold message *keys* (resolved later by
:mod:`study_calc.i18n`), and errors carry a machine code plus parameters so
the GUI can render a localized message.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Mapping


class SolveError(ValueError):
    """A value could not be computed.

    Carries a stable ``code`` (e.g. ``"zero_division"``) and optional ``params``
    so the presentation layer can build a localized message.
    """

    def __init__(self, code: str, **params: object) -> None:
        self.code = code
        self.params = params
        super().__init__(code)


@dataclass(frozen=True)
class Variable:
    """One variable of a formula.

    :param symbol: the math symbol shown to the user (e.g. ``"F"``); also the
        key used in the ``known``/``solvers`` mappings.
    :param name_key: i18n key for the human-readable name (e.g. ``"var.force"``).
    :param unit_key: i18n key for the unit (e.g. ``"unit.newton"``); empty for
        dimensionless quantities.
    """

    symbol: str
    name_key: str
    unit_key: str = ""


# A solver takes the values of the other variables and returns the wanted one.
Solver = Callable[[Mapping[str, float]], float]


@dataclass(frozen=True)
class Formula:
    """A formula that can express any of its known variables.

    :param solvers: mapping ``variable symbol -> compute function``. If a
        variable has no solver, the formula cannot be solved for it.
    """

    key: str
    name_key: str
    expression: str
    variables: tuple[Variable, ...]
    solvers: Mapping[str, Solver] = field(default_factory=dict)

    def variable(self, symbol: str) -> Variable:
        for var in self.variables:
            if var.symbol == symbol:
                return var
        raise KeyError(symbol)

    @property
    def solvable_symbols(self) -> tuple[str, ...]:
        """Variables the formula is able to compute."""
        return tuple(v.symbol for v in self.variables if v.symbol in self.solvers)

    def solve(self, target: str, known: Mapping[str, float]) -> float:
        """Compute ``target`` from the ``known`` values.

        :raises SolveError: if there is no solver, a value is missing, or a math
            error occurs (e.g. division by zero).
        """
        solver = self.solvers.get(target)
        if solver is None:
            raise SolveError("no_solver", var=target)
        try:
            result = solver(known)
        except SolveError:
            raise  # a solver signalled a domain-specific condition; keep its code
        except KeyError as exc:  # a required variable was not provided
            raise SolveError("missing_value", var=exc.args[0]) from exc
        except ZeroDivisionError as exc:
            raise SolveError("zero_division") from exc
        except (ValueError, OverflowError) as exc:
            raise SolveError("math_error", detail=str(exc)) from exc
        if isinstance(result, complex):
            # e.g. ``(-x) ** 0.5`` — the square root of a negative quantity has
            # no real value, so there is nothing meaningful to display.
            raise SolveError("no_real_solution")
        result = float(result)
        if not math.isfinite(result):
            # overflow to ±inf or an undefined operation (NaN).
            raise SolveError("not_finite")
        return result
