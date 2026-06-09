"""Модель физической формулы с решением относительно любой переменной.

Идея интерфейса калькулятора: пользователь заполняет все переменные формулы,
кроме одной, а недостающую программа вычисляет. Чтобы это работало для любой
переменной, каждая формула хранит словарь «решателей» — по одной функции на
каждую переменную, которую можно выразить через остальные.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping


class SolveError(ValueError):
    """Невозможно вычислить значение (нет решателя, деление на ноль и т.п.)."""


@dataclass(frozen=True)
class Variable:
    """Одна переменная формулы: обозначение, человекочитаемое имя и единица."""

    symbol: str
    name: str
    unit: str

    @property
    def label(self) -> str:
        unit = f", {self.unit}" if self.unit else ""
        return f"{self.name} ({self.symbol}{unit})"


# Решатель принимает значения остальных переменных и возвращает искомое.
Solver = Callable[[Mapping[str, float]], float]


@dataclass(frozen=True)
class Formula:
    """Формула с возможностью выразить любую известную переменную.

    :param solvers: отображение «символ переменной → функция расчёта». Если для
        переменной решателя нет, относительно неё формулу решить нельзя.
    """

    key: str
    name: str
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
        """Переменные, которые формула умеет вычислять."""
        return tuple(v.symbol for v in self.variables if v.symbol in self.solvers)

    def solve(self, target: str, known: Mapping[str, float]) -> float:
        """Вычислить ``target`` по известным значениям ``known``.

        :raises SolveError: если решателя нет, не хватает данных или возникает
            математическая ошибка (например, деление на ноль).
        """
        solver = self.solvers.get(target)
        if solver is None:
            raise SolveError(
                f"Формула «{self.name}» не умеет вычислять переменную «{target}»."
            )
        try:
            return float(solver(known))
        except KeyError as exc:  # не передали нужную переменную
            raise SolveError(f"Не задано значение переменной {exc}.") from exc
        except ZeroDivisionError as exc:
            raise SolveError("Деление на ноль при расчёте.") from exc
        except (ValueError, OverflowError) as exc:
            raise SolveError(f"Математическая ошибка: {exc}") from exc
