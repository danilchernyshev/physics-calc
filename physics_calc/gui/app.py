"""Десктопное окно физического калькулятора на Tkinter.

Интерфейс собран из вкладок: по одной на каждый раздел физики плюс вкладка
конвертера единиц. Внутри раздела пользователь выбирает формулу, заполняет все
переменные, кроме одной, и нажимает «Вычислить» — пустое поле заполняется
результатом. Такой подход (решение относительно любой переменной) опирается на
:class:`~physics_calc.core.formula.Formula`.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from physics_calc.core.formula import Formula, SolveError
from physics_calc.core.units import categories, convert, units_of, ConversionError
from physics_calc.domains import SECTIONS


def _format_number(value: float) -> str:
    """Аккуратно отформатировать результат: целые без хвоста, иначе — 6 значащих."""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


class FormulaPanel(ttk.Frame):
    """Вкладка одного раздела: выбор формулы и поля ввода переменных."""

    def __init__(self, master: tk.Misc, formulas: list[Formula]) -> None:
        super().__init__(master, padding=12)
        self._formulas = formulas
        self._by_name = {f.name: f for f in formulas}
        self._entries: dict[str, ttk.Entry] = {}
        self._current: Formula | None = None

        # --- Верхняя строка: выбор формулы. ---
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Формула:").pack(side="left")
        self._combo = ttk.Combobox(
            top, state="readonly", values=[f.name for f in formulas], width=42
        )
        self._combo.pack(side="left", padx=(6, 0))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._build_fields())

        # Запись формулы крупным шрифтом.
        self._expr = ttk.Label(self, font=("TkDefaultFont", 13, "bold"))
        self._expr.pack(anchor="w", pady=(10, 0))

        ttk.Label(
            self,
            text="Заполните все поля, кроме одного — пустое будет вычислено.",
            foreground="#666",
        ).pack(anchor="w", pady=(2, 8))

        # --- Контейнер для динамических полей. ---
        self._fields = ttk.Frame(self)
        self._fields.pack(fill="x")

        # --- Кнопки и результат. ---
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Вычислить", command=self._compute).pack(side="left")
        ttk.Button(buttons, text="Очистить", command=self._clear).pack(side="left", padx=6)

        self._result = ttk.Label(self, font=("TkDefaultFont", 12, "bold"), foreground="#0a6")
        self._result.pack(anchor="w", pady=(12, 0))

        self._combo.current(0)
        self._build_fields()

    def _build_fields(self) -> None:
        """Перестроить поля ввода под выбранную формулу."""
        for child in self._fields.winfo_children():
            child.destroy()
        self._entries.clear()

        formula = self._by_name[self._combo.get()]
        self._current = formula
        self._expr.config(text=formula.expression)
        self._result.config(text="")

        for row, var in enumerate(formula.variables):
            ttk.Label(self._fields, text=var.label + ":", width=34, anchor="w").grid(
                row=row, column=0, sticky="w", pady=3
            )
            entry = ttk.Entry(self._fields, width=18)
            entry.grid(row=row, column=1, sticky="w", pady=3)
            entry.bind("<Return>", lambda _e: self._compute())
            self._entries[var.symbol] = entry

    def _clear(self) -> None:
        for entry in self._entries.values():
            entry.delete(0, "end")
        self._result.config(text="")

    def _compute(self) -> None:
        assert self._current is not None
        formula = self._current

        known: dict[str, float] = {}
        empty: list[str] = []
        for symbol, entry in self._entries.items():
            text = entry.get().strip().replace(",", ".")
            if not text:
                empty.append(symbol)
                continue
            try:
                known[symbol] = float(text)
            except ValueError:
                self._show_error(
                    f"«{formula.variable(symbol).name}»: «{text}» — не число."
                )
                return

        if len(empty) == 0:
            self._show_error("Оставьте ровно одно поле пустым — его и вычислю.")
            return
        if len(empty) > 1:
            names = ", ".join(formula.variable(s).name for s in empty)
            self._show_error(f"Пустых полей несколько ({names}). Оставьте одно.")
            return

        target = empty[0]
        try:
            value = formula.solve(target, known)
        except SolveError as exc:
            self._show_error(str(exc))
            return

        var = formula.variable(target)
        unit = f" {var.unit}" if var.unit else ""
        self._result.config(
            text=f"{var.symbol} = {_format_number(value)}{unit}", foreground="#0a6"
        )

    def _show_error(self, message: str) -> None:
        self._result.config(text="⚠ " + message, foreground="#c33")


class ConverterPanel(ttk.Frame):
    """Вкладка конвертера единиц измерения."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)

        ttk.Label(self, text="Категория:").grid(row=0, column=0, sticky="w", pady=4)
        self._category = ttk.Combobox(
            self, state="readonly", values=categories(), width=20
        )
        self._category.grid(row=0, column=1, sticky="w", pady=4)
        self._category.bind("<<ComboboxSelected>>", lambda _e: self._refresh_units())

        ttk.Label(self, text="Значение:").grid(row=1, column=0, sticky="w", pady=4)
        self._value = ttk.Entry(self, width=22)
        self._value.grid(row=1, column=1, sticky="w", pady=4)
        self._value.bind("<Return>", lambda _e: self._convert())

        ttk.Label(self, text="Из:").grid(row=2, column=0, sticky="w", pady=4)
        self._from = ttk.Combobox(self, state="readonly", width=18)
        self._from.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(self, text="В:").grid(row=3, column=0, sticky="w", pady=4)
        self._to = ttk.Combobox(self, state="readonly", width=18)
        self._to.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Button(self, text="Перевести", command=self._convert).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        self._result = ttk.Label(
            self, font=("TkDefaultFont", 12, "bold"), foreground="#0a6"
        )
        self._result.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self._category.current(0)
        self._refresh_units()

    def _refresh_units(self) -> None:
        units = units_of(self._category.get())
        self._from.config(values=units)
        self._to.config(values=units)
        self._from.current(0)
        self._to.current(min(1, len(units) - 1))
        self._result.config(text="")

    def _convert(self) -> None:
        text = self._value.get().strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            self._result.config(text=f"⚠ «{text}» — не число.", foreground="#c33")
            return
        try:
            result = convert(value, self._from.get(), self._to.get(), self._category.get())
        except ConversionError as exc:
            self._result.config(text="⚠ " + str(exc), foreground="#c33")
            return
        self._result.config(
            text=f"{_format_number(value)} {self._from.get()}  =  "
            f"{_format_number(result)} {self._to.get()}",
            foreground="#0a6",
        )


def build_app() -> tk.Tk:
    """Собрать главное окно со всеми вкладками."""
    root = tk.Tk()
    root.title("Физический калькулятор")
    root.minsize(560, 420)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=8, pady=8)

    for name, formulas in SECTIONS.items():
        notebook.add(FormulaPanel(notebook, formulas), text=name)
    notebook.add(ConverterPanel(notebook), text="Конвертер единиц")

    return root


def run() -> None:
    """Точка входа: запустить графический интерфейс."""
    build_app().mainloop()
