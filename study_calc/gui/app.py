"""Tkinter desktop window for the study calculator.

The UI is an outer notebook of *subjects* (Physics, Math, Tools, Chemistry — see
:data:`study_calc.navigation.SUBJECTS`); each groups its sections and tool panels in
an inner notebook. Inside a physics section the user picks a formula, fills every
variable but one, and clicks "Compute" — the empty field is filled with the result.
That "solve for any variable" behaviour comes from
:class:`~study_calc.core.formula.Formula`.

All user-facing text comes from :mod:`study_calc.i18n`. The Language menu switches
the catalog at runtime; the window is then rebuilt so every label, tab and combobox
is re-rendered in the new language. A Help menu offers a "How to use" guide and an
About box.
"""

from __future__ import annotations

import math
import tkinter as tk
import webbrowser
from tkinter import ttk

from study_calc import __version__
from study_calc.core.explain import Explanation
from study_calc.core.formula import Formula, SolveError
from study_calc.core.learning import (
    CURRICULUM_GRADES,
    Concept,
    Problem,
    Topic,
    load_concept,
    load_topic,
    problems_for_subject,
)
from study_calc.core.units import categories, convert, units_of, ConversionError
from study_calc.domains import SECTIONS
from study_calc.domains.references import explanation_for
from study_calc.i18n import i18n, t
from study_calc import navigation

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
        self.tag_configure("badge", foreground="#0a6", background="#eef7f0",
                           font=("TkDefaultFont", 10, "bold"), spacing1=2, spacing3=6)
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
        text.write("2023 – 2027\n", "body")
        text.write("Peel District School Board\n", "body")
        text.write("Mississauga, Ontario, Canada\n", "body")
        text.end()


class GuideWindow(tk.Toplevel):
    """A 'How to use' help window: what the tool offers and how to work each part."""

    # (heading key, body key) pairs, rendered in order. Keep the list in i18n so the
    # whole guide follows the active language.
    _SECTIONS = (
        ("guide.physics.head", "guide.physics.body"),
        ("guide.math.head", "guide.math.body"),
        ("guide.tools.head", "guide.tools.body"),
        ("guide.problems.head", "guide.problems.body"),
        ("guide.learning.head", "guide.learning.body"),
        ("guide.language.head", "guide.language.body"),
    )

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title(t("menu.guide"))
        self.minsize(540, 480)
        text = _RichText(self, width=64, height=24)
        scroll = ttk.Scrollbar(self, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)

        text.begin()
        text.heading(t("guide.title"))
        text.write(t("guide.intro") + "\n", "body")
        for head_key, body_key in self._SECTIONS:
            text.heading(t(head_key))
            text.write(t(body_key) + "\n", "body")
        text.end()


class GraphWindow(tk.Toplevel):
    """A pop-up that plots the current CAS expression with matplotlib.

    Embeds a Matplotlib figure in a Tk canvas. Vertical asymptotes are drawn as
    dashed red guide lines, and the axes are marked. The sampling (and all SymPy
    use) lives in :func:`study_calc.core.cas.sample`; this class only draws.
    """

    def __init__(self, master: tk.Misc, cas, expression: str, variable: str) -> None:
        super().__init__(master)
        self.title(t("graph.title"))
        self.minsize(560, 460)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        try:
            xs, ys, asymptotes = cas.sample(expression, variable)
        except cas.CasError as exc:
            ttk.Label(self, text="⚠ " + t(f"error.{exc.code}", **exc.params),
                      foreground=_ERROR_COLOR, wraplength=520, padding=18).pack()
            return

        figure = Figure(figsize=(6, 4.6), dpi=100)
        axes = figure.add_subplot(111)
        axes.axhline(0, color="#888", linewidth=0.8)
        axes.axvline(0, color="#888", linewidth=0.8)
        axes.plot(xs, ys, color=_LINK_COLOR, linewidth=1.8)
        for position in asymptotes:
            axes.axvline(position, color=_ERROR_COLOR, linestyle="--", linewidth=0.9)
        axes.set_title(expression)
        axes.set_xlabel(variable or "x")
        axes.set_ylabel("y")
        axes.grid(True, alpha=0.3)
        figure.tight_layout()

        canvas = FigureCanvasTkAgg(figure, master=self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


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
        if topic is not None:
            self._curriculum(topic.courses)
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
        self._curriculum(topic.courses)
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

    def show_problem(
        self, problem: Problem, reveal_steps: bool = False, reveal_answer: bool = False
    ) -> None:
        """Render a practice problem with a reveal-the-solution flow.

        The statement (given + find) always shows; the solution steps and the final
        answer appear only once the student asks for them. A video-solution link and
        a "learn the theory" link (which swaps the panel to the related topic) render
        below when the problem provides them.
        """
        ex = problem.example
        text = self._text
        text.begin()
        text.heading(ex.title or t("ui.problem_statement"))
        self._curriculum(problem.courses)
        if ex.given:
            text.write(t("ui.given") + ":\n", "label")
            for item in ex.given:
                text.write(f"   • {item}\n", "step")
        if ex.find:
            text.write(t("ui.find") + ": ", "label")
            text.write(ex.find + "\n", "body")
        if reveal_steps and ex.steps:
            text.write(t("ui.solution") + ":\n", "label")
            for index, step in enumerate(ex.steps, start=1):
                text.write(f"   {index}. {step}\n", "step")
        if reveal_answer and ex.answer:
            text.write(t("ui.answer") + ": ", "label")
            text.write(ex.answer + "\n", "answer")
        if problem.video_url:
            text.link(t("ui.video_solution"), problem.video_url)
        topic = load_topic(problem.topic_id, i18n.language) if problem.topic_id else None
        if topic is not None:
            text.link(t("ui.related_topic"),
                      lambda tp=topic: self.show_topic("ui.related_topic", tp))
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

    def _curriculum(self, courses: tuple[str, ...]) -> None:
        """Render a curriculum badge, e.g. 'Curriculum: MHF4U (Grade 12)'."""
        if not courses:
            return
        parts = []
        for code in courses:
            grade = CURRICULUM_GRADES.get(code)
            parts.append(f"{code} ({t('ui.grade', n=grade)})" if grade else code)
        self._text.write(f" {t('ui.curriculum')} " + ", ".join(parts) + " \n", "badge")

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

        # Extra per-operation inputs (e.g. interval endpoints for "rate", the
        # second function for "combine"), rebuilt by _on_op_change from OP_FIELDS.
        self._extra = ttk.Frame(left)
        self._extra.pack(fill="x")
        self._extra_entries: dict[str, ttk.Entry] = {}

        # --- Buttons. ---
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=t("ui.compute"), command=self._compute).pack(side="left")
        ttk.Button(buttons, text=t("ui.plot"), command=self._plot).pack(side="left", padx=6)
        ttk.Button(buttons, text=t("ui.clear"), command=self._clear).pack(side="left")

        self._combo.current(0)
        self._on_op_change()

    # Step keys whose line is the actual answer (highlighted), vs. reasoning.
    # Every "analyze"/"function"/"combine" card line counts as an answer too
    # (see ``_is_answer``).
    _ANSWER_KEYS = {
        "cas.step.result", "cas.step.solve_root", "cas.step.inequality_solution",
        "cas.step.identity_true", "cas.step.identity_false",
    }

    @classmethod
    def _is_answer(cls, key: str) -> bool:
        return key in cls._ANSWER_KEYS or key.startswith("cas.step.card.")

    def _on_op_change(self) -> None:
        """Enable the variable field, and build any extra inputs, for the op."""
        op = self._op_ids[self._combo.current()]
        needs_var = op in self._cas.USES_VARIABLE
        state = "normal" if needs_var else "disabled"
        self._var.config(state=state)
        self._var_label.config(foreground="" if needs_var else _HINT_COLOR)
        self._build_extra_fields(op)
        self._show_topic_or_hint(op)

    def _build_extra_fields(self, op: str) -> None:
        """Rebuild the per-operation extra input rows from ``cas.OP_FIELDS``."""
        for child in self._extra.winfo_children():
            child.destroy()
        self._extra_entries.clear()
        for row, field_id in enumerate(self._cas.OP_FIELDS.get(op, ())):
            ttk.Label(self._extra, text=t(f"cas.field.{field_id}"), width=24,
                      anchor="w").grid(row=row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(self._extra, width=20)
            entry.grid(row=row, column=1, sticky="w", pady=3)
            entry.bind("<Return>", lambda _e: self._compute())
            self._extra_entries[field_id] = entry

    def _clear(self) -> None:
        self._expr.delete(0, "end")
        self._var.delete(0, "end")
        for entry in self._extra_entries.values():
            entry.delete(0, "end")
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
        extra = {fid: entry.get().strip() for fid, entry in self._extra_entries.items()}
        try:
            result = self._cas.run(op, expression, variable, **extra)
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

    def _plot(self) -> None:
        """Open a graph of the current expression (matplotlib, lazily imported)."""
        try:
            import matplotlib  # noqa: F401  (presence check only)
        except ImportError:
            self._explain.show_hint("graph.title", "graph.unavailable")
            return
        expression = self._expr.get().strip()
        if not expression:
            self._explain.show_error(t("error.cas_empty"))
            return
        GraphWindow(self, self._cas, expression, self._var.get().strip())


class VectorPanel(ttk.Frame):
    """Vectors tab (MCV4U0): pick an operation and type 2-D or 3-D vectors.

    Backed by :mod:`study_calc.core.vectors` (standard library only, so unlike
    the CAS tab it is always available). Mirrors :class:`CasPanel`: an operation
    picker on the left, a worked step-by-step solution in the learning area on
    the right, and the operation's learning material shown before computing.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        from study_calc.core import vectors

        self._vectors = vectors
        self._op_ids = vectors.OPERATIONS

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        self._explain = ExplanationPanel(paned)
        paned.add(left, weight=3)
        paned.add(self._explain, weight=2)

        top = ttk.Frame(left)
        top.pack(fill="x")
        ttk.Label(top, text=t("vector.operation")).pack(side="left")
        self._combo = ttk.Combobox(
            top, state="readonly", width=26,
            values=[t(f"vector.op.{oid}") for oid in self._op_ids],
        )
        self._combo.pack(side="left", padx=(6, 0))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._on_op_change())

        ttk.Label(left, text=t("vector.hint"), foreground=_HINT_COLOR, wraplength=420,
                  justify="left").pack(anchor="w", pady=(10, 8))

        fields = ttk.Frame(left)
        fields.pack(fill="x")
        ttk.Label(fields, text=t("vector.u"), width=14, anchor="w").grid(
            row=0, column=0, sticky="w", pady=3)
        self._u = ttk.Entry(fields, width=30)
        self._u.grid(row=0, column=1, sticky="w", pady=3)
        self._u.bind("<Return>", lambda _e: self._compute())

        self._v_label = ttk.Label(fields, text=t("vector.v"), width=14, anchor="w")
        self._v_label.grid(row=1, column=0, sticky="w", pady=3)
        self._v = ttk.Entry(fields, width=30)
        self._v.grid(row=1, column=1, sticky="w", pady=3)
        self._v.bind("<Return>", lambda _e: self._compute())

        self._k_label = ttk.Label(fields, text=t("vector.scalar"), width=14, anchor="w")
        self._k_label.grid(row=2, column=0, sticky="w", pady=3)
        self._k = ttk.Entry(fields, width=12)
        self._k.grid(row=2, column=1, sticky="w", pady=3)
        self._k.bind("<Return>", lambda _e: self._compute())

        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=t("ui.compute"), command=self._compute).pack(side="left")
        ttk.Button(buttons, text=t("ui.clear"), command=self._clear).pack(side="left", padx=6)

        self._combo.current(0)
        self._on_op_change()

    # Step keys whose line is the actual answer (highlighted), vs. reasoning.
    _ANSWER_KEYS = {"vector.step.result", "vector.step.angle_result", "vector.step.proj_vector"}

    def _on_op_change(self) -> None:
        """Enable the v / scalar fields only for operations that use them."""
        op = self._op_ids[self._combo.current()]
        needs_v = op in self._vectors.NEEDS_SECOND
        needs_k = op in self._vectors.NEEDS_SCALAR
        self._v.config(state="normal" if needs_v else "disabled")
        self._v_label.config(foreground="" if needs_v else _HINT_COLOR)
        self._k.config(state="normal" if needs_k else "disabled")
        self._k_label.config(foreground="" if needs_k else _HINT_COLOR)
        self._show_topic_or_hint(op)

    def _show_topic_or_hint(self, op: str) -> None:
        topic = load_topic(f"vec_{op}", i18n.language)
        if topic is not None:
            self._explain.show_topic(f"vector.op.{op}", topic)
        else:
            self._explain.show_hint("vector.steps_title", "vector.steps_placeholder")

    def _clear(self) -> None:
        for entry in (self._u, self._v, self._k):
            entry.delete(0, "end")
        self._show_topic_or_hint(self._op_ids[self._combo.current()])

    def _compute(self) -> None:
        op = self._op_ids[self._combo.current()]
        try:
            result = self._vectors.run(
                op, self._u.get().strip(), self._v.get().strip(), self._k.get().strip()
            )
        except self._vectors.VectorError as exc:
            self._explain.show_error(t(f"error.{exc.code}", **exc.params))
            return
        segments = [
            (t(step.key, **step.params) + "\n",
             "answer" if step.key in self._ANSWER_KEYS else "step")
            for step in result.steps
        ]
        self._explain.show_steps("vector.steps_title", segments)


class PeriodicTablePanel(ttk.Frame):
    """Chemistry tools: the periodic table plus a molar-mass and equation balancer.

    Backed by :mod:`study_calc.core.periodic` (standard library only). Clicking an
    element shows its data; the two entry boxes compute the molar mass of a formula
    and balance a chemical equation, rendering :class:`ChemError` codes through i18n.
    """

    # Element series → cell colour (CPK-ish families; unknown/synthetic are grey).
    _COLORS = {
        "alkali metal": "#ff8a80", "alkaline earth metal": "#ffd180",
        "transition metal": "#ffe0b2", "post-transition metal": "#c5e1a5",
        "metalloid": "#80cbc4", "diatomic nonmetal": "#a5d6a7",
        "polyatomic nonmetal": "#a5d6a7", "noble gas": "#b39ddb",
        "lanthanide": "#f48fb1", "actinide": "#ce93d8",
    }
    _DEFAULT_COLOR = "#e0e0e0"

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=12)
        from study_calc.core import periodic

        self._periodic = periodic

        # --- Calculators (top) ---------------------------------------------
        tools = ttk.Frame(self)
        tools.pack(fill="x", pady=(0, 10))

        ttk.Label(tools, text=t("ui.molar_mass") + ":", width=14, anchor="w").grid(
            row=0, column=0, sticky="w", pady=3)
        self._mm_entry = ttk.Entry(tools, width=24)
        self._mm_entry.grid(row=0, column=1, sticky="w", pady=3)
        self._mm_entry.bind("<Return>", lambda _e: self._molar_mass())
        ttk.Button(tools, text=t("ui.compute"), command=self._molar_mass).grid(
            row=0, column=2, padx=6)
        self._mm_result = ttk.Label(tools, text="", foreground=_HINT_COLOR)
        self._mm_result.grid(row=0, column=3, sticky="w", padx=(8, 0))

        ttk.Label(tools, text=t("ui.equation"), width=14, anchor="w").grid(
            row=1, column=0, sticky="w", pady=3)
        self._eq_entry = ttk.Entry(tools, width=24)
        self._eq_entry.grid(row=1, column=1, sticky="w", pady=3)
        self._eq_entry.bind("<Return>", lambda _e: self._balance())
        ttk.Button(tools, text=t("ui.balance"), command=self._balance).grid(
            row=1, column=2, padx=6)
        self._eq_result = ttk.Label(tools, text="", foreground=_HINT_COLOR)
        self._eq_result.grid(row=1, column=3, sticky="w", padx=(8, 0))

        # --- Periodic table grid -------------------------------------------
        grid = ttk.Frame(self)
        grid.pack()
        for el in periodic.elements():
            color = self._COLORS.get(el.category, self._DEFAULT_COLOR)
            cell = tk.Button(
                grid, text=f"{el.number}\n{el.symbol}", width=4, height=2,
                font=("TkDefaultFont", 7), bg=color, relief="ridge", bd=1,
                padx=0, pady=0, command=lambda e=el: self._select(e),
            )
            cell.grid(row=el.ypos, column=el.xpos, padx=1, pady=1)

        # --- Selected-element detail ---------------------------------------
        self._detail = ttk.Label(self, text="", anchor="w", justify="left")
        self._detail.pack(fill="x", pady=(10, 0))
        self._select(periodic.element("H"))

    def _select(self, el) -> None:
        self._detail.config(
            text=(f"{el.name}  ·  {t('ui.atomic_number')} {el.number}  ·  "
                  f"{t('ui.atomic_mass')} {el.mass:g} g/mol  ·  "
                  f"{t('ui.group')} {el.group if el.group else '—'}, "
                  f"{t('ui.period')} {el.period}  ·  {el.category}"),
        )

    def _molar_mass(self) -> None:
        formula = self._mm_entry.get().strip()
        try:
            mass = self._periodic.molar_mass(formula)
        except self._periodic.ChemError as exc:
            self._mm_result.config(
                foreground=_ERROR_COLOR, text=t(f"error.{exc.code}", **exc.params))
            return
        comp = self._periodic.composition(formula)
        breakdown = ", ".join(f"{sym}:{n}" for sym, n in comp.items())
        self._mm_result.config(
            foreground="",
            text=f"{formula} = {mass:.3f} {t('unit.gram_per_mol')}  ({breakdown})")

    def _balance(self) -> None:
        equation = self._eq_entry.get().strip()
        try:
            balanced = self._periodic.balance(equation)
        except self._periodic.ChemError as exc:
            self._eq_result.config(
                foreground=_ERROR_COLOR, text=t(f"error.{exc.code}", **exc.params))
            return
        self._eq_result.config(foreground="", text=balanced)


class ProblemsPanel(ttk.Frame):
    """The practice-problems surface for one subject (the "problems helper").

    Mirrors the other panels' left/right split: a list of the subject's problems on
    the left with *Reveal steps* / *Reveal answer* buttons, and the selected
    problem's statement — then its solution, on request — in the learning area on the
    right (see :meth:`ExplanationPanel.show_problem`). Problems come from
    :func:`study_calc.core.learning.problems_for_subject`; an empty subject shows a
    quiet hint instead of an empty list.
    """

    def __init__(self, master: tk.Misc, subject: str) -> None:
        super().__init__(master, padding=12)
        self._subject = subject
        self._problems = problems_for_subject(subject, i18n.language)
        self._reveal_steps = False
        self._reveal_answer = False

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned)
        self._explain = ExplanationPanel(paned)
        paned.add(left, weight=3)
        paned.add(self._explain, weight=2)

        ttk.Label(left, text=t("ui.choose_problem")).pack(anchor="w")
        self._list = tk.Listbox(left, height=12, exportselection=False, activestyle="none")
        for problem in self._problems:
            self._list.insert("end", problem.example.title or problem.problem_id)
        self._list.pack(fill="both", expand=True, pady=(4, 8))
        self._list.bind("<<ListboxSelect>>", lambda _e: self._on_select())

        buttons = ttk.Frame(left)
        buttons.pack(fill="x")
        self._steps_btn = ttk.Button(buttons, text=t("ui.reveal_steps"),
                                     command=self._on_reveal_steps)
        self._steps_btn.pack(side="left")
        self._answer_btn = ttk.Button(buttons, text=t("ui.reveal_answer"),
                                      command=self._on_reveal_answer)
        self._answer_btn.pack(side="left", padx=6)

        if self._problems:
            self._list.selection_set(0)
            self._on_select()
        else:
            for button in (self._steps_btn, self._answer_btn):
                button.config(state="disabled")
            self._explain.show_hint("tab.problems", "problems.empty")

    def _current(self) -> Problem | None:
        selection = self._list.curselection()
        return self._problems[selection[0]] if selection else None

    def _render(self) -> None:
        problem = self._current()
        if problem is not None:
            self._explain.show_problem(problem, self._reveal_steps, self._reveal_answer)

    def _on_select(self) -> None:
        # A fresh problem starts hidden — the student reveals the solution on demand.
        self._reveal_steps = False
        self._reveal_answer = False
        self._render()

    def _on_reveal_steps(self) -> None:
        self._reveal_steps = True
        self._render()

    def _on_reveal_answer(self) -> None:
        self._reveal_answer = True
        self._render()


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

        # --- Menu bar: Language, and Help -> How to use / About. Rebuilt here so
        # every label follows the active language. ---
        menubar = tk.Menu(self.root)

        # Language menu: a radio entry per locale, a checkmark on the active one.
        language_menu = tk.Menu(menubar, tearoff=0)
        self._lang_var = tk.StringVar(value=i18n.language)
        for code, native in self._languages:
            language_menu.add_radiobutton(
                label=native, value=code, variable=self._lang_var,
                command=lambda c=code: self._on_language_change(c),
            )
        menubar.add_cascade(label=t("menu.language"), menu=language_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=t("menu.guide"), command=self._show_guide)
        help_menu.add_separator()
        help_menu.add_command(label=t("menu.about"), command=self._show_about)
        menubar.add_cascade(label=t("menu.help"), menu=help_menu)

        self.root.config(menu=menubar)

        # --- Tabs: an outer notebook of subjects, each grouping its sections/tools
        # (see study_calc.navigation.SUBJECTS). A subject with a single item shows
        # that panel directly; one with several gets its own inner notebook. ---
        self._notebook = ttk.Notebook(self.root)
        self._notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self._inner_notebooks: dict[int, ttk.Notebook] = {}
        for index, (subject_id, items) in enumerate(navigation.SUBJECTS):
            subject = self._build_subject(self._notebook, items)
            self._notebook.add(subject, text=t(f"subject.{subject_id}"))
            if isinstance(subject, ttk.Notebook):
                self._inner_notebooks[index] = subject

    def _build_subject(self, master: tk.Misc, items: tuple) -> tk.Widget:
        """Build a subject's content: a lone panel, or an inner notebook of items."""
        if len(items) == 1:
            widget, _label = self._make_item(master, items[0])
            return widget
        inner = ttk.Notebook(master)
        for item in items:
            widget, label = self._make_item(inner, item)
            inner.add(widget, text=label)
        return inner

    def _make_item(self, master: tk.Misc, item) -> tuple[tk.Widget, str]:
        """Map one navigation item to its (widget, tab label)."""
        if isinstance(item, navigation.Section):
            panel = FormulaPanel(master, SECTIONS[item.section_id])
            return panel, t(f"section.{item.section_id}")
        if isinstance(item, navigation.Tool):
            if item.name == "converter":
                return ConverterPanel(master), t("tab.converter")
            if item.name == "vectors":
                return VectorPanel(master), t("tab.vectors")
            if item.name == "periodic_table":
                return PeriodicTablePanel(master), t("tab.periodic_table")
            if item.name == "cas":
                try:
                    return CasPanel(master), t("tab.cas")
                except ImportError:
                    return self._notice(master, "cas.unavailable"), t("tab.cas")
            raise ValueError(f"unknown tool {item.name!r}")
        if isinstance(item, navigation.Problems):
            return ProblemsPanel(master, item.subject_id), t("tab.problems")
        if isinstance(item, navigation.Placeholder):
            return self._notice(master, item.message_key), ""
        raise TypeError(f"unknown navigation item {item!r}")

    def _notice(self, master: tk.Misc, message_key: str) -> ttk.Frame:
        """A padded, muted notice frame (CAS-missing fallback, 'coming soon', ...)."""
        frame = ttk.Frame(master, padding=18)
        ttk.Label(frame, text=t(message_key), foreground=_HINT_COLOR,
                  wraplength=560, justify="left").pack(anchor="w")
        return frame

    def _on_language_change(self, code: str) -> None:
        """Switch language and rebuild the UI, keeping the selected subject/tab."""
        if code == i18n.language:
            return
        selection = self._current_selection()
        i18n.set_language(code)
        for child in self.root.winfo_children():
            child.destroy()
        self._build()
        self._restore_selection(selection)

    def _current_selection(self) -> tuple[int, int]:
        """The selected (outer subject index, inner tab index) before a rebuild."""
        try:
            outer = self._notebook.index(self._notebook.select())
        except tk.TclError:
            return (0, 0)
        inner_nb = self._inner_notebooks.get(outer)
        inner = 0
        if inner_nb is not None:
            try:
                inner = inner_nb.index(inner_nb.select())
            except tk.TclError:
                inner = 0
        return (outer, inner)

    def _restore_selection(self, selection: tuple[int, int]) -> None:
        outer, inner = selection
        try:
            self._notebook.select(outer)
        except tk.TclError:
            return
        inner_nb = self._inner_notebooks.get(outer)
        if inner_nb is not None:
            try:
                inner_nb.select(inner)
            except tk.TclError:
                pass

    def _show_guide(self) -> None:
        GuideWindow(self.root)

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
