"""Tkinter desktop window for the physics calculator.

The UI is a set of tabs: one per physics section plus a unit-converter tab.
Inside a section the user picks a formula, fills every variable but one, and
clicks "Compute" — the empty field is filled with the result. That "solve for
any variable" behaviour comes from :class:`~physics_calc.core.formula.Formula`.

All user-facing text comes from :mod:`physics_calc.i18n`. A language selector at
the top switches the catalog at runtime; the window is then rebuilt so every
label, tab and combobox is re-rendered in the new language.
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from physics_calc.core.formula import Formula, SolveError
from physics_calc.core.units import categories, convert, units_of, ConversionError
from physics_calc.domains import SECTIONS
from physics_calc.i18n import i18n, t

_OK_COLOR = "#0a6"
_ERROR_COLOR = "#c33"
_HINT_COLOR = "#666"


def _format_number(value: float) -> str:
    """Format a result: whole numbers without a tail, otherwise 6 significant digits.

    ``math.isfinite`` is checked first so ``int(value)`` is never evaluated on
    ``inf``/``NaN`` (which would raise); those render as ``"inf"``/``"nan"``.
    """
    if math.isfinite(value) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


def _solve_error_message(formula: Formula, exc: SolveError) -> str:
    """Build a localized message for a :class:`SolveError`.

    A ``var`` parameter holds a variable *symbol*; translate it to the variable's
    display name before formatting.
    """
    params = dict(exc.params)
    symbol = params.get("var")
    if symbol is not None:
        try:
            params["var"] = t(formula.variable(symbol).name_key)
        except KeyError:
            params["var"] = symbol
    return t(f"error.{exc.code}", **params)


class FormulaPanel(ttk.Frame):
    """One section tab: a formula picker and its variable input fields."""

    def __init__(self, master: tk.Misc, formulas: list[Formula]) -> None:
        super().__init__(master, padding=12)
        self._formulas = formulas
        self._entries: dict[str, ttk.Entry] = {}
        self._current: Formula | None = None

        # --- Top row: formula picker. ---
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text=t("ui.formula")).pack(side="left")
        self._combo = ttk.Combobox(
            top, state="readonly", values=[t(f.name_key) for f in formulas], width=44
        )
        self._combo.pack(side="left", padx=(6, 0))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._build_fields())

        # The formula expression, shown larger.
        self._expr = ttk.Label(self, font=("TkDefaultFont", 13, "bold"))
        self._expr.pack(anchor="w", pady=(10, 0))

        ttk.Label(self, text=t("ui.hint"), foreground=_HINT_COLOR).pack(
            anchor="w", pady=(2, 8)
        )

        # --- Container for the dynamic fields. ---
        self._fields = ttk.Frame(self)
        self._fields.pack(fill="x")

        # --- Buttons and result. ---
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=t("ui.compute"), command=self._compute).pack(side="left")
        ttk.Button(buttons, text=t("ui.clear"), command=self._clear).pack(side="left", padx=6)

        self._result = ttk.Label(self, font=("TkDefaultFont", 12, "bold"), foreground=_OK_COLOR)
        self._result.pack(anchor="w", pady=(12, 0))

        self._combo.current(0)
        self._build_fields()

    def _build_fields(self) -> None:
        """Rebuild the input fields for the selected formula."""
        for child in self._fields.winfo_children():
            child.destroy()
        self._entries.clear()

        formula = self._formulas[self._combo.current()]
        self._current = formula
        self._expr.config(text=formula.expression)
        self._result.config(text="")

        for row, var in enumerate(formula.variables):
            ttk.Label(
                self._fields, text=i18n.variable_label(var) + ":", width=38, anchor="w"
            ).grid(row=row, column=0, sticky="w", pady=3)
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
                    t("error.not_a_number", value=text,
                      field=t(formula.variable(symbol).name_key))
                )
                return

        if len(empty) == 0:
            self._show_error(t("error.no_empty_field"))
            return
        if len(empty) > 1:
            names = ", ".join(t(formula.variable(s).name_key) for s in empty)
            self._show_error(t("error.too_many_empty", fields=names))
            return

        target = empty[0]
        try:
            value = formula.solve(target, known)
        except SolveError as exc:
            self._show_error(_solve_error_message(formula, exc))
            return

        var = formula.variable(target)
        unit = f" {t(var.unit_key)}" if var.unit_key else ""
        self._result.config(
            text=f"{var.symbol} = {_format_number(value)}{unit}", foreground=_OK_COLOR
        )

    def _show_error(self, message: str) -> None:
        self._result.config(text="⚠ " + message, foreground=_ERROR_COLOR)


class ConverterPanel(ttk.Frame):
    """Unit-converter tab."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        self._category_ids = categories()
        self._unit_ids: list[str] = []

        ttk.Label(self, text=t("ui.category")).grid(row=0, column=0, sticky="w", pady=4)
        self._category = ttk.Combobox(
            self, state="readonly", width=20,
            values=[t(f"category.{cid}") for cid in self._category_ids],
        )
        self._category.grid(row=0, column=1, sticky="w", pady=4)
        self._category.bind("<<ComboboxSelected>>", lambda _e: self._refresh_units())

        ttk.Label(self, text=t("ui.value")).grid(row=1, column=0, sticky="w", pady=4)
        self._value = ttk.Entry(self, width=22)
        self._value.grid(row=1, column=1, sticky="w", pady=4)
        self._value.bind("<Return>", lambda _e: self._convert())

        ttk.Label(self, text=t("ui.from")).grid(row=2, column=0, sticky="w", pady=4)
        self._from = ttk.Combobox(self, state="readonly", width=18)
        self._from.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(self, text=t("ui.to")).grid(row=3, column=0, sticky="w", pady=4)
        self._to = ttk.Combobox(self, state="readonly", width=18)
        self._to.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Button(self, text=t("ui.convert"), command=self._convert).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        self._result = ttk.Label(self, font=("TkDefaultFont", 12, "bold"), foreground=_OK_COLOR)
        self._result.grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self._category.current(0)
        self._refresh_units()

    def _refresh_units(self) -> None:
        category = self._category_ids[self._category.current()]
        self._unit_ids = units_of(category)
        labels = [t(f"unit.{uid}") for uid in self._unit_ids]
        self._from.config(values=labels)
        self._to.config(values=labels)
        self._from.current(0)
        self._to.current(min(1, len(labels) - 1))
        self._result.config(text="")

    def _show_error(self, message: str) -> None:
        self._result.config(text="⚠ " + message, foreground=_ERROR_COLOR)

    def _convert(self) -> None:
        text = self._value.get().strip().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            self._show_error(t("error.not_a_number", value=text, field=t("ui.value")))
            return

        category = self._category_ids[self._category.current()]
        from_id = self._unit_ids[self._from.current()]
        to_id = self._unit_ids[self._to.current()]
        try:
            result = convert(value, from_id, to_id, category)
        except ConversionError as exc:
            self._show_error(t(f"error.{exc.code}", **exc.params))
            return
        if not math.isfinite(result):  # overflow on an extreme conversion
            self._show_error(t("error.not_finite"))
            return

        self._result.config(
            text=f"{_format_number(value)} {t(f'unit.{from_id}')}  =  "
            f"{_format_number(result)} {t(f'unit.{to_id}')}",
            foreground=_OK_COLOR,
        )


class App:
    """Main window owner. Rebuilds its widgets when the language changes."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.minsize(620, 470)
        # (code, native_name) pairs for the language picker.
        self._languages = i18n.available_languages()
        self._build()

    def _build(self) -> None:
        self.root.title(t("app.title"))

        # --- Top bar: language selector, right-aligned. ---
        top = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        ttk.Label(top, text=t("language.label")).pack(side="left")
        self._lang_combo = ttk.Combobox(
            top, state="readonly", width=12,
            values=[native for _code, native in self._languages],
        )
        self._lang_combo.pack(side="left", padx=(6, 0))
        codes = [code for code, _native in self._languages]
        self._lang_combo.current(codes.index(i18n.language))
        self._lang_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_language_change())

        # --- Tabs. ---
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=8, pady=8)
        for section_id, formulas in SECTIONS.items():
            self._notebook.add(FormulaPanel(self._notebook, formulas), text=t(f"section.{section_id}"))
        self._notebook.add(ConverterPanel(self._notebook), text=t("tab.converter"))

    def _on_language_change(self) -> None:
        """Switch language and rebuild the UI, keeping the selected tab."""
        code = self._languages[self._lang_combo.current()][0]
        if code == i18n.language:
            return
        selected_tab = self._notebook.index(self._notebook.select())
        i18n.set_language(code)
        for child in self.root.winfo_children():
            child.destroy()
        self._build()
        self._notebook.select(selected_tab)

    def run(self) -> None:
        self.root.mainloop()


def build_app() -> App:
    """Build the application (without starting the event loop)."""
    return App()


def run() -> None:
    """Entry point: launch the graphical interface."""
    build_app().run()
