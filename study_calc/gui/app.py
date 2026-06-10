"""Tkinter desktop window for the study calculator.

The UI is a set of tabs: one per physics section plus a unit-converter tab.
Inside a section the user picks a formula, fills every variable but one, and
clicks "Compute" — the empty field is filled with the result. That "solve for
any variable" behaviour comes from :class:`~study_calc.core.formula.Formula`.

All user-facing text comes from :mod:`study_calc.i18n`. A language selector at
the top switches the catalog at runtime; the window is then rebuilt so every
label, tab and combobox is re-rendered in the new language.
"""

from __future__ import annotations

import math
import tkinter as tk
import webbrowser
from tkinter import ttk

from study_calc import __version__
from study_calc.core.explain import Explanation
from study_calc.core.formula import Formula, SolveError
from study_calc.core.learning import Concept, Topic, load_concept, load_topic
from study_calc.core.units import categories, convert, units_of, ConversionError
from study_calc.domains import SECTIONS
from study_calc.domains.references import explanation_for
from study_calc.i18n import i18n, t

_OK_COLOR = "#0a6"
_ERROR_COLOR = "#c33"
_HINT_COLOR = "#666"
_HEADING_COLOR = "#2a4d8f"
_LINK_COLOR = "#1a5fb4"


class ResultArea(ttk.Frame):
    """A read-only, scrollable, selectable text area for showing results.

    Shared by every tab so answers look and behave the same everywhere: the
    answer in green, errors in red, explanatory lines in quiet grey — and all of
    it selectable for copy/paste (the widget is kept ``disabled`` for editing but
    still allows selection).
    """

    def __init__(self, master: tk.Misc, height: int = 12) -> None:
        super().__init__(master)
        self._text = tk.Text(
            self, height=height, wrap="word", relief="solid", borderwidth=1,
            font=("TkDefaultFont", 11), padx=8, pady=6,
            background="#fcfcfc", state="disabled", cursor="arrow",
        )
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)
        self._text.tag_configure("answer", foreground=_OK_COLOR, font=("TkDefaultFont", 11, "bold"))
        self._text.tag_configure("step", foreground="#222")
        self._text.tag_configure("error", foreground=_ERROR_COLOR)

    def show(self, segments: list[tuple[str, str]]) -> None:
        """Replace the contents with ``(text, tag)`` segments."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        for text, tag in segments:
            self._text.insert("end", text, tag)
        self._text.config(state="disabled")
        self._text.see("1.0")

    def show_answer(self, text: str) -> None:
        self.show([(text, "answer")])

    def show_error(self, message: str) -> None:
        self.show([("⚠ " + message, "error")])

    def clear(self) -> None:
        self.show([])


class _RichText(tk.Text):
    """A read-only, selectable text widget with shared heading/body/link styling.

    The building block for both the right-hand :class:`ExplanationPanel` and the
    pop-up :class:`ConceptWindow`, so links, headings and formulas look identical
    everywhere. Content is written between :meth:`begin` and :meth:`end` (the widget
    is briefly made editable, then locked back to ``disabled`` so it stays read-only
    but still allows text selection for copy/paste).

    A "link" may open a URL in the browser *or* run a Python callback (used to open
    a concept window), so the same styling drives both kinds of click.
    """

    def __init__(self, master: tk.Misc, **kwargs: object) -> None:
        options: dict[str, object] = dict(
            wrap="word", relief="solid", borderwidth=1,
            font=("TkDefaultFont", 11), padx=10, pady=8,
            background="#f7f9fc", state="disabled", cursor="arrow",
        )
        options.update(kwargs)
        super().__init__(master, **options)
        self.tag_configure(
            "heading", foreground=_HEADING_COLOR, font=("TkDefaultFont", 11, "bold"),
            spacing1=8, spacing3=3,
        )
        self.tag_configure("body", foreground="#222", spacing3=4)
        self.tag_configure("step", foreground="#222", lmargin1=4, lmargin2=18, spacing3=3)
        self.tag_configure("formula", foreground="#1b3a6b", font=("TkFixedFont", 11),
                           lmargin1=8, spacing3=2)
        self.tag_configure("label", foreground="#222", font=("TkDefaultFont", 11, "bold"))
        self.tag_configure("answer", foreground=_OK_COLOR, font=("TkDefaultFont", 11, "bold"))
        self.tag_configure("error", foreground=_ERROR_COLOR)
        self.tag_configure("hint", foreground=_HINT_COLOR, spacing3=4)
        self._link_count = 0

    def begin(self) -> None:
        self.config(state="normal")
        self.delete("1.0", "end")
        self._link_count = 0

    def end(self) -> None:
        self.config(state="disabled")
        self.see("1.0")

    def heading(self, text: str) -> None:
        # A leading blank line before every heading but the first keeps sections apart.
        prefix = "" if self.index("end-1c") == "1.0" else "\n"
        self.insert("end", prefix + text + "\n", "heading")

    def write(self, text: str, tag: str = "body") -> None:
        self.insert("end", text, tag)

    def link(self, label: str, target) -> None:
        """Insert one clickable line.

        ``target`` is either a URL string (opened in the browser) or a zero-arg
        callable (invoked on click — used to open a concept window).
        """
        tag = f"link-{self._link_count}"
        self._link_count += 1
        self.tag_configure(tag, foreground=_LINK_COLOR, underline=True, spacing3=3)

        def on_click(_event, target=target):
            webbrowser.open(target) if isinstance(target, str) else target()

        self.tag_bind(tag, "<Button-1>", on_click)
        self.tag_bind(tag, "<Enter>", lambda _e: self.config(cursor="hand2"))
        self.tag_bind(tag, "<Leave>", lambda _e: self.config(cursor="arrow"))
        self.insert("end", label + "\n", tag)


class ConceptWindow(tk.Toplevel):
    """A pop-up explaining one glossary term: its full definition, related
    formulas, and links to related terms (which open further concept windows)."""

    def __init__(self, master: tk.Misc, concept: Concept) -> None:
        super().__init__(master)
        self.title(concept.title)
        self.minsize(440, 340)
        text = _RichText(self, width=56)
        scroll = ttk.Scrollbar(self, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        text.begin()
        text.heading(concept.title)
        for paragraph in concept.full.split("\n\n"):
            text.write(paragraph.strip() + "\n", "body")
        if concept.formulas:
            text.heading(t("ui.related_formulas"))
            for formula in concept.formulas:
                text.write(formula + "\n", "formula")
        if concept.see_also:
            text.heading(t("ui.see_also"))
            for term_id in concept.see_also:
                other = load_concept(term_id, i18n.language)
                if other is not None:
                    text.link(other.title, lambda c=other: ConceptWindow(self, c))
        text.end()


class AboutWindow(tk.Toplevel):
    """A small 'About' pop-up: the app name, version and author credit."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title(t("menu.about"))
        self.minsize(380, 240)
        self.resizable(False, False)
        text = _RichText(self, width=46, height=10)
        text.pack(fill="both", expand=True)

        text.begin()
        text.heading(t("app.title"))
        text.write(f'{t("about.version")} {__version__}\n', "body")
        text.write("\n", "body")
        text.write(t("about.created_by") + "\n", "label")
        text.write("Mark Chernyshev\n", "body")
        text.write(t("about.role") + "\n", "body")
        text.write("Applewood Heights Secondary School\n", "body")
        text.write("2024 – 2027\n", "body")
        text.write("Peel District School Board\n", "body")
        text.end()


class ExplanationPanel(ttk.Frame):
    """The learning area on the right of a tab: theory, formulas, terms, an
    example, worked steps, and study links.

    A read-only, scrollable :class:`_RichText` driven by language-neutral content
    (i18n keys, learning-folder data, URLs), so the same widget serves two cases:

    - :meth:`show` renders a static :class:`~study_calc.core.explain.Explanation`
      plus the rich :class:`~study_calc.core.learning.Topic` (useful formulas, key
      terms with pop-up explanations, a worked example) for a physics formula.
    - :meth:`show_steps` renders a dynamic worked solution — used by the CAS tab for
      SymPy's step-by-step, and reusable for Math later.

    References and term explanations render as clickable links (browser / pop-up).
    """

    def __init__(self, master: tk.Misc, width: int = 40) -> None:
        super().__init__(master)
        self._text = _RichText(self, width=width)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

    def show(self, explanation: Explanation, topic: Topic | None = None) -> None:
        """Render the static ``explanation`` and, when present, the rich ``topic``."""
        text = self._text
        text.begin()
        text.heading(t("ui.theory"))
        text.write(t(explanation.theory_key) + "\n")

        if topic is not None and topic.formulas:
            text.heading(t("ui.useful_formulas"))
            for formula in topic.formulas:
                text.write(formula + "\n", "formula")

        self._how_to_solve(explanation, topic)

        if topic is not None and topic.terms:
            self._key_terms(topic.terms)

        if topic is not None and topic.example is not None:
            self._worked_example(topic.example)

        self._references(explanation.references)
        text.end()

    def show_steps(
        self, title_key: str, segments: list[tuple[str, str]], references: tuple = ()
    ) -> None:
        """Render a dynamic worked solution under ``title_key``.

        ``segments`` are pre-rendered ``(text, tag)`` pairs (tag in
        ``"answer"``/``"step"``); each ``text`` already carries its own newline.
        """
        self._text.begin()
        self._text.heading(t(title_key))
        for segment, tag in segments:
            self._text.write(segment, tag)
        self._references(references)
        self._text.end()

    def show_topic(self, title_key: str, topic: Topic) -> None:
        """Render a topic's learning material on its own, under ``title_key``.

        Unlike :meth:`show`, this needs no :class:`Explanation` — it is used by the
        CAS/Math tab to teach the selected operation (summary, useful formulas,
        method, key terms, worked example) before a result has been computed.
        """
        text = self._text
        text.begin()
        text.heading(t(title_key))
        if topic.summary:
            text.write(topic.summary + "\n")
        if topic.formulas:
            text.heading(t("ui.useful_formulas"))
            for formula in topic.formulas:
                text.write(formula + "\n", "formula")
        if topic.method:
            text.heading(t("ui.how_to_solve"))
            for index, step in enumerate(topic.method, start=1):
                text.write(f"{index}. {step}\n", "step")
        if topic.terms:
            self._key_terms(topic.terms)
        if topic.example is not None:
            self._worked_example(topic.example)
        text.end()

    def show_hint(self, title_key: str, hint_key: str) -> None:
        """Show a quiet placeholder (e.g. before the CAS tab has been run)."""
        self._text.begin()
        self._text.heading(t(title_key))
        self._text.write(t(hint_key) + "\n", "hint")
        self._text.end()

    def show_error(self, message: str) -> None:
        self._text.begin()
        self._text.write("⚠ " + message, "error")
        self._text.end()

    def clear(self) -> None:
        self._text.begin()
        self._text.end()

    # --- section builders ---

    def _how_to_solve(self, explanation: Explanation, topic: Topic | None) -> None:
        # Prefer the topic's specific method; fall back to the generic solve steps.
        if topic is not None and topic.method:
            self._text.heading(t("ui.how_to_solve"))
            for index, step in enumerate(topic.method, start=1):
                self._text.write(f"{index}. {step}\n", "step")
        elif explanation.steps_keys:
            self._text.heading(t("ui.how_to_solve"))
            for index, key in enumerate(explanation.steps_keys, start=1):
                self._text.write(f"{index}. {t(key)}\n", "step")

    def _key_terms(self, term_ids: tuple[str, ...]) -> None:
        self._text.heading(t("ui.key_terms"))
        for term_id in term_ids:
            concept = load_concept(term_id, i18n.language)
            if concept is None:
                continue
            self._text.write(f"• {concept.title} — ", "label")
            self._text.write(concept.short + "\n", "body")
            self._text.link(t("ui.open_full"), lambda c=concept: ConceptWindow(self, c))

    def _worked_example(self, example) -> None:
        self._text.heading(t("ui.worked_example"))
        if example.title:
            self._text.write(example.title + "\n", "body")
        if example.given:
            self._text.write(t("ui.given") + ":\n", "label")
            for item in example.given:
                self._text.write(f"   • {item}\n", "step")
        if example.find:
            self._text.write(t("ui.find") + ": ", "label")
            self._text.write(example.find + "\n", "body")
        if example.steps:
            self._text.write(t("ui.solution") + ":\n", "label")
            for index, step in enumerate(example.steps, start=1):
                self._text.write(f"   {index}. {step}\n", "step")
        if example.answer:
            self._text.write(t("ui.answer") + ": ", "label")
            self._text.write(example.answer + "\n", "answer")

    def _references(self, references: tuple) -> None:
        if not references:
            return
        self._text.heading(t("ui.learn_more"))
        for ref in references:
            self._text.link(t(ref.label_key), ref.url)


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

        # Two resizable columns: inputs/result on the left, the learning area
        # (theory, how to solve, study links) on the right.
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        self._explain = ExplanationPanel(paned)
        paned.add(left, weight=3)
        paned.add(self._explain, weight=2)

        # --- Top row: formula picker. ---
        top = ttk.Frame(left)
        top.pack(fill="x")
        ttk.Label(top, text=t("ui.formula")).pack(side="left")
        self._combo = ttk.Combobox(
            top, state="readonly", values=[t(f.name_key) for f in formulas], width=44
        )
        self._combo.pack(side="left", padx=(6, 0))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._build_fields())

        # The formula expression, shown larger.
        self._expr = ttk.Label(left, font=("TkDefaultFont", 13, "bold"))
        self._expr.pack(anchor="w", pady=(10, 0))

        ttk.Label(left, text=t("ui.hint"), foreground=_HINT_COLOR).pack(
            anchor="w", pady=(2, 8)
        )

        # --- Container for the dynamic fields. ---
        self._fields = ttk.Frame(left)
        self._fields.pack(fill="x")

        # --- Buttons and result. ---
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=t("ui.compute"), command=self._compute).pack(side="left")
        ttk.Button(buttons, text=t("ui.clear"), command=self._clear).pack(side="left", padx=6)

        self._result = ResultArea(left)
        self._result.pack(fill="both", expand=True, pady=(12, 0))

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
        self._result.clear()
        self._explain.show(
            explanation_for(formula.key), load_topic(formula.key, i18n.language)
        )

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
        self._result.clear()

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
        self._result.show_answer(f"{var.symbol} = {_format_number(value)}{unit}")

    def _show_error(self, message: str) -> None:
        self._result.show_error(message)


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

        self._result = ResultArea(self, height=8)
        self._result.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        self.grid_rowconfigure(5, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

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
        self._result.clear()

    def _show_error(self, message: str) -> None:
        self._result.show_error(message)

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

        self._result.show_answer(
            f"{_format_number(value)} {t(f'unit.{from_id}')}  =  "
            f"{_format_number(result)} {t(f'unit.{to_id}')}"
        )


class CasPanel(ttk.Frame):
    """Symbolic math (CAS) tab: type an expression and pick a transformation.

    Backed by :mod:`study_calc.core.cas` (SymPy). SymPy is imported lazily so
    a missing install degrades to a friendly notice instead of crashing the app;
    :func:`_build_cas_tab` only adds this panel when the import succeeds.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        from study_calc.core import cas  # local import: only reached when sympy is present

        self._cas = cas
        self._op_ids = cas.OPERATIONS

        # Two resizable columns, mirroring the formula tabs: the input form on the
        # left, the worked step-by-step solution in the learning area on the right.
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        self._explain = ExplanationPanel(paned)
        paned.add(left, weight=3)
        paned.add(self._explain, weight=2)

        # --- Operation picker. ---
        top = ttk.Frame(left)
        top.pack(fill="x")
        ttk.Label(top, text=t("cas.operation")).pack(side="left")
        self._combo = ttk.Combobox(
            top, state="readonly", width=24,
            values=[t(f"cas.op.{oid}") for oid in self._op_ids],
        )
        self._combo.pack(side="left", padx=(6, 0))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._on_op_change())

        ttk.Label(left, text=t("cas.hint"), foreground=_HINT_COLOR, wraplength=420,
                  justify="left").pack(anchor="w", pady=(10, 8))

        # --- Expression + variable inputs. ---
        fields = ttk.Frame(left)
        fields.pack(fill="x")
        ttk.Label(fields, text=t("cas.expression"), width=14, anchor="w").grid(
            row=0, column=0, sticky="w", pady=3
        )
        self._expr = ttk.Entry(fields, width=44)
        self._expr.grid(row=0, column=1, sticky="w", pady=3)
        self._expr.bind("<Return>", lambda _e: self._compute())

        self._var_label = ttk.Label(fields, text=t("cas.variable"), width=14, anchor="w")
        self._var_label.grid(row=1, column=0, sticky="w", pady=3)
        self._var = ttk.Entry(fields, width=12)
        self._var.grid(row=1, column=1, sticky="w", pady=3)
        self._var.bind("<Return>", lambda _e: self._compute())

        # --- Buttons. ---
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=t("ui.compute"), command=self._compute).pack(side="left")
        ttk.Button(buttons, text=t("ui.clear"), command=self._clear).pack(side="left", padx=6)

        self._combo.current(0)
        self._on_op_change()

    # Step keys whose line is the actual answer (highlighted), vs. reasoning.
    # Every "analyze" card line counts as an answer (see ``_is_answer``).
    _ANSWER_KEYS = {"cas.step.result", "cas.step.solve_root"}

    @classmethod
    def _is_answer(cls, key: str) -> bool:
        return key in cls._ANSWER_KEYS or key.startswith("cas.step.card.")

    def _on_op_change(self) -> None:
        """Enable the variable field only for operations that need one."""
        op = self._op_ids[self._combo.current()]
        needs_var = op in self._cas.USES_VARIABLE
        state = "normal" if needs_var else "disabled"
        self._var.config(state=state)
        self._var_label.config(foreground="" if needs_var else _HINT_COLOR)
        self._show_topic_or_hint(op)

    def _clear(self) -> None:
        self._expr.delete(0, "end")
        self._var.delete(0, "end")
        self._show_topic_or_hint(self._op_ids[self._combo.current()])

    def _show_topic_or_hint(self, op: str) -> None:
        """Teach the selected operation, or fall back to a quiet placeholder.

        Before a result is computed the right panel shows the Math learning
        material for the chosen operation (under ``cas_<op>``); operations without
        content yet degrade to the original placeholder.
        """
        topic = load_topic(f"cas_{op}", i18n.language)
        if topic is not None:
            self._explain.show_topic(f"cas.op.{op}", topic)
        else:
            self._explain.show_hint("cas.steps_title", "cas.steps_placeholder")

    def _compute(self) -> None:
        op = self._op_ids[self._combo.current()]
        expression = self._expr.get().strip()
        variable = self._var.get().strip()
        try:
            result = self._cas.run(op, expression, variable)
        except self._cas.CasError as exc:
            self._explain.show_error(t(f"error.{exc.code}", **exc.params))
            return
        # Show powers as the user typed them (``x^2``), not SymPy's ``x**2``.
        segments = [
            (t(step.key, **step.params).replace("**", "^") + "\n",
             "answer" if self._is_answer(step.key) else "step")
            for step in result.steps
        ]
        if not segments:  # defensive: an op without steps still shows an answer
            segments = [(f"{result.input_text}  →  {result.output_text}\n", "answer")]
        self._explain.show_steps("cas.steps_title", segments)


def _build_cas_tab(notebook: ttk.Notebook) -> None:
    """Add the CAS tab, or a notice tab if SymPy is not installed."""
    try:
        notebook.add(CasPanel(notebook), text=t("tab.cas"))
    except ImportError:
        notice = ttk.Frame(notebook, padding=18)
        ttk.Label(notice, text=t("cas.unavailable"), foreground=_HINT_COLOR,
                  wraplength=560, justify="left").pack(anchor="w")
        notebook.add(notice, text=t("tab.cas"))


class App:
    """Main window owner. Rebuilds its widgets when the language changes."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.minsize(940, 500)
        # (code, native_name) pairs for the language picker.
        self._languages = i18n.available_languages()
        self._build()

    def _build(self) -> None:
        self.root.title(t("app.title"))

        # --- Menu bar: Help -> About. Rebuilt here so it follows the language. ---
        menubar = tk.Menu(self.root)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=t("menu.about"), command=self._show_about)
        menubar.add_cascade(label=t("menu.help"), menu=help_menu)
        self.root.config(menu=menubar)

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
        _build_cas_tab(self._notebook)

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

    def _show_about(self) -> None:
        AboutWindow(self.root)

    def run(self) -> None:
        self.root.mainloop()


def build_app() -> App:
    """Build the application (without starting the event loop)."""
    return App()


def run() -> None:
    """Entry point: launch the graphical interface."""
    build_app().run()
