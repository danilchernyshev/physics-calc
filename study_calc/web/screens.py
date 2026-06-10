"""Per-screen model builders for the redesign frontend (issue #6 onward).

Where :mod:`study_calc.web.bridge` builds the *shell* model (subjects/items +
chrome), this module builds the model for the **content area** of a screen — the
cards the frontend renders for a given navigation item. The first surface is the
physics **formula screen** (``section`` items): an input card (solve-for-any
variable), a solution card (result / error), and the learning card.

Like the bridge, this is **pure Python with no PyWebView import**, so it is unit
-tested headlessly. It deliberately re-implements the solve flow, number
formatting and explanation layout of :class:`study_calc.gui.app.FormulaPanel` /
``ExplanationPanel`` rather than importing them, because ``gui.app`` imports
Tkinter (unavailable / undesirable on the headless web path). The two must stay
in sync; the shared ground truth is :mod:`study_calc.core` + the i18n keys.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Mapping

from ..core.explain import Explanation
from ..core.formula import Formula, SolveError
from ..core.learning import (
    CURRICULUM_GRADES,
    Concept,
    WorkedExample,
    load_concept,
    load_topic,
)
from ..domains import SECTIONS
from ..domains.references import explanation_for
from ..i18n import i18n, t


@lru_cache(maxsize=1)
def _formula_index() -> dict[str, Formula]:
    """Map every formula ``key`` to its :class:`Formula`, across all sections.

    Cached: ``SECTIONS`` is built once at import, and this is hit once per formula
    while assembling a screen, so we scan the whole catalog only on first use.
    Callers must treat the returned dict as read-only.
    """
    return {f.key: f for formulas in SECTIONS.values() for f in formulas}


def _format_number(value: float) -> str:
    """Mirror ``gui.app._format_number``: whole numbers bare, else 6 sig digits."""
    if math.isfinite(value) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.6g}"


def _solve_error_message(formula: Formula, exc: SolveError) -> str:
    """Mirror ``gui.app._solve_error_message``: localize a :class:`SolveError`."""
    params = dict(exc.params)
    symbol = params.get("var")
    if symbol is not None:
        try:
            params["var"] = t(formula.variable(symbol).name_key)
        except KeyError:
            params["var"] = symbol
    return t(f"error.{exc.code}", **params)


# --- learning-card blocks (mirror of ExplanationPanel.show) ---


def _curriculum_text(courses: tuple[str, ...]) -> str:
    """Mirror ``ExplanationPanel._curriculum``: 'Curriculum: MHF4U (Grade 12)'."""
    if not courses:
        return ""
    parts = []
    for code in courses:
        grade = CURRICULUM_GRADES.get(code)
        parts.append(f"{code} ({t('ui.grade', n=grade)})" if grade else code)
    return f"{t('ui.curriculum')} " + ", ".join(parts)


def _concept_model(concept: Concept, with_see_also: bool = True) -> dict:
    """A glossary term as a JSON-able model for the key-terms pop-up.

    ``see_also`` is resolved one level deep (each related term carries its own
    ``full`` text) so the frontend modal is self-contained — no extra round-trip
    and it works in the static browser preview too.
    """
    model = {
        "id": concept.term_id,
        "title": concept.title,
        "short": concept.short,
        "full": concept.full,
        "formulas": list(concept.formulas),
        "seeAlso": [],
    }
    if with_see_also:
        for term_id in concept.see_also:
            related = load_concept(term_id, i18n.language)
            if related is not None:
                model["seeAlso"].append(_concept_model(related, with_see_also=False))
    return model


def _example_block(example: WorkedExample) -> dict:
    """A worked example with its section labels resolved (i18n stays in Python)."""
    return {
        "type": "example",
        "title": example.title,
        "givenLabel": t("ui.given"),
        "given": list(example.given),
        "findLabel": t("ui.find"),
        "find": example.find,
        "solutionLabel": t("ui.solution"),
        "steps": list(example.steps),
        "answerLabel": t("ui.answer"),
        "answer": example.answer,
    }


def _learning_blocks(explanation: Explanation, topic) -> list[dict]:
    """Build the ordered learning blocks for a formula (mirror of ``.show``)."""
    blocks: list[dict] = []
    if topic is not None:
        badge = _curriculum_text(topic.courses)
        if badge:
            blocks.append({"type": "badge", "text": badge})

    blocks.append({"type": "heading", "text": t("ui.theory")})
    blocks.append({"type": "body", "text": t(explanation.theory_key)})

    if topic is not None and topic.formulas:
        blocks.append({"type": "heading", "text": t("ui.useful_formulas")})
        for formula in topic.formulas:
            blocks.append({"type": "formula", "text": formula})

    # How to solve: the topic's specific method, else the generic solve steps.
    if topic is not None and topic.method:
        blocks.append({"type": "heading", "text": t("ui.how_to_solve")})
        blocks.append({"type": "steps", "items": list(topic.method)})
    elif explanation.steps_keys:
        blocks.append({"type": "heading", "text": t("ui.how_to_solve")})
        blocks.append({"type": "steps", "items": [t(k) for k in explanation.steps_keys]})

    if topic is not None and topic.terms:
        terms = []
        for term_id in topic.terms:
            concept = load_concept(term_id, i18n.language)
            if concept is not None:
                terms.append(_concept_model(concept))
        if terms:
            blocks.append({"type": "heading", "text": t("ui.key_terms")})
            blocks.append({"type": "terms", "items": terms})

    if topic is not None and topic.example is not None:
        blocks.append({"type": "heading", "text": t("ui.worked_example")})
        blocks.append(_example_block(topic.example))

    if explanation.references:
        blocks.append({"type": "heading", "text": t("ui.learn_more")})
        blocks.append({
            "type": "links",
            "items": [
                {"text": t(ref.label_key), "href": ref.url}
                for ref in explanation.references
            ],
        })
    return blocks


def formula_learning(formula_key: str) -> list[dict]:
    """The learning-card blocks for one formula, or an empty list if unknown."""
    formula = _formula_index().get(formula_key)
    if formula is None:
        return []
    return _learning_blocks(
        explanation_for(formula.key), load_topic(formula.key, i18n.language)
    )


# --- formula screen ---


def _formula_model(formula: Formula) -> dict:
    return {
        "key": formula.key,
        "name": t(formula.name_key),
        "expression": formula.expression,
        "variables": [
            {"symbol": var.symbol, "label": i18n.variable_label(var)}
            for var in formula.variables
        ],
        "learning": formula_learning(formula.key),
    }


def formula_screen(section_id: str) -> dict:
    """The full model for a physics formula section: labels + every formula.

    ``section_id`` may be the bare id (``"mechanics"``) or the navigation item id
    (``"section:mechanics"``). Each formula carries its variables and its embedded
    learning blocks, so the whole screen renders from one call.
    """
    section_id = section_id.split(":", 1)[-1]
    formulas = SECTIONS.get(section_id, [])
    return {
        "sectionId": section_id,
        "labels": {
            "formula": t("ui.formula"),
            "hint": t("ui.hint"),
            "compute": t("ui.compute"),
            "clear": t("ui.clear"),
            "result": t("ui.result"),
            "answer": t("ui.answer"),
            "openFull": t("ui.open_full"),
            "relatedFormulas": t("ui.related_formulas"),
            "seeAlso": t("ui.see_also"),
            "close": t("ui.close"),
        },
        "formulas": [_formula_model(f) for f in formulas],
    }


def all_formula_screens() -> dict[str, dict]:
    """Every section's formula screen, keyed by bare section id.

    Used by the static browser/screenshot preview to bake all section screens in,
    so the same frontend renders them without a live bridge.
    """
    return {section_id: formula_screen(section_id) for section_id in SECTIONS}


# --- CAS (symbolic math) screen ---
#
# SymPy lives behind ``core.cas`` and is an optional dependency; importing it
# eagerly here would break the whole web package (and the formula screen) when it
# is absent. So, exactly like the Tk ``CasPanel``, ``cas`` is imported *lazily*
# inside the functions below — a missing SymPy degrades to the notice instead.

# Step keys whose line is the actual answer (rendered green), mirroring
# ``gui.app.CasPanel._is_answer`` / ``_ANSWER_KEYS``.
_CAS_ANSWER_KEYS = {
    "cas.step.result",
    "cas.step.solve_root",
    "cas.step.inequality_solution",
    "cas.step.identity_true",
    "cas.step.identity_false",
}


def _is_cas_answer(step_key: str) -> bool:
    return step_key in _CAS_ANSWER_KEYS or step_key.startswith("cas.step.card.")


def _topic_blocks(title_text: str, topic) -> list[dict]:
    """Learning blocks for a CAS operation (mirror of ``ExplanationPanel.show_topic``)."""
    blocks: list[dict] = [{"type": "heading", "text": title_text}]
    badge = _curriculum_text(topic.courses)
    if badge:
        blocks.append({"type": "badge", "text": badge})
    if topic.summary:
        blocks.append({"type": "body", "text": topic.summary})
    if topic.formulas:
        blocks.append({"type": "heading", "text": t("ui.useful_formulas")})
        for formula in topic.formulas:
            blocks.append({"type": "formula", "text": formula})
    if topic.method:
        blocks.append({"type": "heading", "text": t("ui.how_to_solve")})
        blocks.append({"type": "steps", "items": list(topic.method)})
    if topic.terms:
        terms = []
        for term_id in topic.terms:
            concept = load_concept(term_id, i18n.language)
            if concept is not None:
                terms.append(_concept_model(concept))
        if terms:
            blocks.append({"type": "heading", "text": t("ui.key_terms")})
            blocks.append({"type": "terms", "items": terms})
    if topic.example is not None:
        blocks.append({"type": "heading", "text": t("ui.worked_example")})
        blocks.append(_example_block(topic.example))
    return blocks


def _operation_learning(topic_id: str, title_text: str, title_key: str, placeholder_key: str) -> list[dict]:
    """The before-a-result learning panel for an operation: its topic, else a hint.

    Shared by the CAS and vectors screens — both teach the selected operation
    before a result, falling back to a quiet placeholder (mirror of
    ``CasPanel`` / ``VectorPanel._show_topic_or_hint``).
    """
    topic = load_topic(topic_id, i18n.language)
    if topic is not None:
        return _topic_blocks(title_text, topic)
    return [
        {"type": "heading", "text": t(title_key)},
        {"type": "hint", "text": t(placeholder_key)},
    ]


# The CAS and vectors screens share one model shape (operations, each with an
# ordered ``fields`` list + learning blocks) and one frontend renderer
# (``Screens.operations``). The differences below stay in the two screen/run
# pairs: their field sets, the green-answer step keys, and (CAS only) the
# ``**``->``^`` rendering and the lazy SymPy import / absent-fallback.


def _render_steps(steps, answer_of, *, power_caret: bool = False, fallback: str | None = None) -> list[dict]:
    """Turn engine ``CasStep``/``VectorStep`` items into ``{text, answer}`` dicts."""
    rendered = []
    for step in steps:
        text = t(step.key, **step.params)
        if power_caret:
            text = text.replace("**", "^")  # show powers as x^2, not SymPy's x**2
        rendered.append({"text": text, "answer": answer_of(step.key)})
    if not rendered and fallback is not None:
        rendered = [{"text": fallback, "answer": True}]
    return rendered


def cas_screen() -> dict:
    """The CAS screen model: operations + labels, or a SymPy-absent notice.

    When SymPy is not installed the model is ``{"available": False, ...}`` and the
    frontend shows the notice (mirroring the Tk ``cas.unavailable`` fallback).
    """
    try:
        from ..core import cas
    except ImportError:
        return {"available": False, "title": t("tab.cas"), "notice": t("cas.unavailable")}

    operations = []
    for op in cas.OPERATIONS:
        # `persist` marks the main inputs the frontend keeps across op changes;
        # the op-specific extras below are cleared each time (see Screens.operations).
        fields = [{"id": "expression", "label": t("cas.expression"), "mono": True, "persist": True}]
        if op in cas.USES_VARIABLE:
            fields.append({"id": "variable", "label": t("cas.variable"), "mono": True, "persist": True})
        for fid in cas.OP_FIELDS.get(op, ()):
            fields.append({"id": fid, "label": t(f"cas.field.{fid}"), "mono": True})
        operations.append({
            "id": op,
            "label": t(f"cas.op.{op}"),
            "fields": fields,
            "learning": _operation_learning(
                f"cas_{op}", t(f"cas.op.{op}"), "cas.steps_title", "cas.steps_placeholder"
            ),
        })
    return {
        "available": True,
        "title": t("tab.cas"),
        "labels": _operation_labels("cas.operation", "cas.hint", "cas.steps_title"),
        "operations": operations,
    }


def cas_run(op: str, values: Mapping[str, str] | None = None) -> dict:
    """Run a CAS operation from the named field values; mirror of ``CasPanel._compute``.

    Returns ``{"ok": True, "title", "steps"}`` (each step ``{"text", "answer"}``,
    ``answer`` marking the green result line) or ``{"ok": False, "error"}`` — both
    localized. Powers are rendered ``x^2`` (not SymPy's ``x**2``), as in the GUI.
    """
    try:
        from ..core import cas
    except ImportError:
        return {"ok": False, "error": t("cas.unavailable")}

    values = values or {}
    expression = str(values.get("expression", "") or "").strip()
    variable = str(values.get("variable", "") or "").strip()
    extra = {fid: str(values.get(fid, "") or "").strip() for fid in cas.OP_FIELDS.get(op, ())}
    try:
        result = cas.run(op, expression, variable, **extra)
    except cas.CasError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}

    steps = _render_steps(
        result.steps, _is_cas_answer, power_caret=True,
        fallback=f"{result.input_text}  →  {result.output_text}",
    )
    return {"ok": True, "title": t("cas.steps_title"), "steps": steps}


# --- Vectors screen (shares the operations model/renderer with CAS) ---

# Step keys whose line is the actual answer, mirroring ``VectorPanel._ANSWER_KEYS``.
_VECTOR_ANSWER_KEYS = {
    "vector.step.result",
    "vector.step.angle_result",
    "vector.step.proj_vector",
}


def vector_screen() -> dict:
    """The vectors screen model: operations + labels.

    ``core.vectors`` is standard-library only (always importable), so — unlike the
    CAS tab — there is no absent-fallback; the model is always ``available``.
    """
    from ..core import vectors

    operations = []
    for op in vectors.OPERATIONS:
        # Every vector field is a persistent main input — the frontend keeps u/v/k
        # across op changes, mirroring the Tk VectorPanel (it only disables them).
        fields = [{"id": "u", "label": t("vector.u"), "mono": False, "persist": True}]
        if op in vectors.NEEDS_SECOND:
            fields.append({"id": "v", "label": t("vector.v"), "mono": False, "persist": True})
        if op in vectors.NEEDS_SCALAR:
            fields.append({"id": "k", "label": t("vector.scalar"), "mono": False, "persist": True})
        operations.append({
            "id": op,
            "label": t(f"vector.op.{op}"),
            "fields": fields,
            "learning": _operation_learning(
                f"vec_{op}", t(f"vector.op.{op}"), "vector.steps_title", "vector.steps_placeholder"
            ),
        })
    return {
        "available": True,
        "title": t("tab.vectors"),
        "labels": _operation_labels("vector.operation", "vector.hint", "vector.steps_title"),
        "operations": operations,
    }


def vector_run(op: str, values: Mapping[str, str] | None = None) -> dict:
    """Run a vector operation from the named field values; mirror of ``VectorPanel._compute``."""
    from ..core import vectors

    values = values or {}
    u_text = str(values.get("u", "") or "").strip()
    v_text = str(values.get("v", "") or "").strip()
    scalar = str(values.get("k", "") or "").strip()
    try:
        result = vectors.run(op, u_text, v_text, scalar)
    except vectors.VectorError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}

    steps = _render_steps(
        result.steps, lambda key: key in _VECTOR_ANSWER_KEYS, fallback=result.output_text,
    )
    return {"ok": True, "title": t("vector.steps_title"), "steps": steps}


def _operation_labels(operation_key: str, hint_key: str, steps_title_key: str) -> dict:
    """The chrome labels shared by every operations screen (CAS, vectors)."""
    return {
        "operation": t(operation_key),
        "hint": t(hint_key),
        "compute": t("ui.compute"),
        "clear": t("ui.clear"),
        "stepsTitle": t(steps_title_key),
        "openFull": t("ui.open_full"),
        "relatedFormulas": t("ui.related_formulas"),
        "seeAlso": t("ui.see_also"),
        "close": t("ui.close"),
    }


# --- Unit converter screen ---


def converter_screen() -> dict:
    """The unit-converter screen model: all categories with their unit lists.

    Unlike CAS/vectors the converter is always available (standard-library only).
    Every category's unit list is baked into the model so the frontend can swap
    the from/to selectors on a chip change without a round-trip — mirroring how
    the Tk ``ConverterPanel`` pre-populates unit lists per category.
    """
    from ..core.units import categories, units_of

    cats = [
        {
            "id": cat_id,
            "label": t(f"category.{cat_id}"),
            "units": [
                {"id": uid, "label": t(f"unit.{uid}")}
                for uid in units_of(cat_id)
            ],
        }
        for cat_id in categories()
    ]
    return {
        "available": True,
        "title": t("tab.converter"),
        "labels": {
            "category": t("ui.category"),
            "value": t("ui.value"),
            "from": t("ui.from"),
            "to": t("ui.to"),
            "convert": t("ui.convert"),
            "clear": t("ui.clear"),
            "result": t("ui.result"),
        },
        "categories": cats,
    }


def convert_run(category: str, value: str, from_unit: str, to_unit: str) -> dict:
    """Convert ``value`` between units; mirror of ``ConverterPanel._convert``.

    Returns ``{"ok": True, "result": <formatted>}`` or ``{"ok": False, "error":
    <localized>}``. The result string mirrors the Tk panel exactly:
    ``"{value} {from_unit_label}  =  {result} {to_unit_label}"``
    (whole numbers are rendered bare; otherwise 6 significant digits).

    Handles comma decimal separators and maps every ``ConversionError`` code to a
    localized message, the same way as the Tk panel.
    """
    from ..core.units import ConversionError
    from ..core.units import convert as _convert

    text = str(value or "").strip().replace(",", ".")
    try:
        num = float(text)
    except ValueError:
        return {"ok": False, "error": t("error.not_a_number", value=text, field=t("ui.value"))}

    try:
        result = _convert(num, from_unit, to_unit, category)
    except ConversionError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}

    if not math.isfinite(result):
        return {"ok": False, "error": t("error.not_finite")}

    from_label = t(f"unit.{from_unit}")
    to_label = t(f"unit.{to_unit}")
    return {
        "ok": True,
        "result": (
            f"{_format_number(num)} {from_label}"
            f"  =  "
            f"{_format_number(result)} {to_label}"
        ),
    }


# --- Periodic-table (chemistry tool) screen ---

# Category string (raw from elements.json) → CSS token slug for var(--series-<slug>).
# Unknown/synthetic categories (e.g. "unknown, probably metalloid") fall back to
# "default" (grey), mirroring the Tk PeriodicTablePanel._DEFAULT_COLOR.
_CATEGORY_SERIES: dict[str, str] = {
    "alkali metal":          "alkali-metal",
    "alkaline earth metal":  "alkaline-earth-metal",
    "transition metal":      "transition-metal",
    "post-transition metal": "post-transition-metal",
    "metalloid":             "metalloid",
    "diatomic nonmetal":     "diatomic-nonmetal",
    "polyatomic nonmetal":   "polyatomic-nonmetal",
    "noble gas":             "noble-gas",
    "lanthanide":            "lanthanide",
    "actinide":              "actinide",
}
_DEFAULT_SERIES = "default"


def periodic_screen() -> dict:
    """The periodic-table screen model: all elements pre-baked for the CSS grid.

    ``core.periodic`` is standard-library only (always importable), so this screen
    is always ``available`` — no absent-fallback branch (unlike the SymPy-gated CAS
    tab). Each element in ``elements`` carries its position (``xpos``/``ypos``), its
    raw English ``category``, and a ``series`` slug that maps directly to a
    ``var(--series-*)`` CSS token so the frontend can colour the grid cell without a
    round-trip. The detail annotation line is rendered client-side from the pre-baked
    element list, mirroring the converter's no-round-trip approach for unit selects.
    """
    from ..core.periodic import elements as _elements

    els = [
        {
            "number":   el.number,
            "symbol":   el.symbol,
            "name":     el.name,        # raw English string — shown verbatim (not localized)
            "mass":     el.mass,
            "group":    el.group,       # int | None (None for lanthanides / actinides)
            "period":   el.period,
            "category": el.category,    # raw English string — shown verbatim in the detail line
            "xpos":     el.xpos,
            "ypos":     el.ypos,
            "series":   _CATEGORY_SERIES.get(el.category, _DEFAULT_SERIES),
        }
        for el in _elements()
    ]
    return {
        "available": True,
        "title": t("tab.periodic_table"),
        "labels": {
            "molarMass":    t("ui.molar_mass"),
            "compute":      t("ui.compute"),
            "clear":        t("ui.clear"),
            "equation":     t("ui.equation"),
            "balance":      t("ui.balance"),
            "atomicNumber": t("ui.atomic_number"),
            "atomicMass":   t("ui.atomic_mass"),
            "group":        t("ui.group"),
            "period":       t("ui.period"),
            "gramPerMol":   t("unit.gram_per_mol"),
        },
        "elements": els,
    }


def molar_mass_run(formula: str) -> dict:
    """Compute the molar mass of ``formula``; mirror of ``PeriodicTablePanel._molar_mass``.

    Returns ``{"ok": True, "result": "<formula> = <mass> g/mol  (<breakdown>)"}``
    or ``{"ok": False, "error": <localized>}``. The result string mirrors the Tk
    panel exactly, including the element→count breakdown (e.g. ``H:2, O:1``).
    """
    from ..core.periodic import ChemError
    from ..core.periodic import composition as _composition
    from ..core.periodic import molar_mass as _molar_mass

    formula = str(formula or "").strip()
    try:
        mass = _molar_mass(formula)
        comp = _composition(formula)
    except ChemError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}
    breakdown = ", ".join(f"{sym}:{n}" for sym, n in comp.items())
    return {
        "ok": True,
        "result": f"{formula} = {mass:.3f} {t('unit.gram_per_mol')}  ({breakdown})",
    }


def balance_run(equation: str) -> dict:
    """Balance a chemical equation; mirror of ``PeriodicTablePanel._balance``.

    Returns ``{"ok": True, "result": <balanced string>}`` or
    ``{"ok": False, "error": <localized>}``.
    """
    from ..core.periodic import ChemError
    from ..core.periodic import balance as _balance

    equation = str(equation or "").strip()
    try:
        balanced = _balance(equation)
    except ChemError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}
    return {"ok": True, "result": balanced}


# --- Guide overlay screen ---


_GUIDE_SECTIONS = ("physics", "math", "tools", "problems", "learning", "language")


def guide_screen() -> dict:
    """The guide overlay model: title, intro, and six ordered sections.

    Every value is resolved from the ``guide.*`` i18n keys already present in
    all five locales — no English literals anywhere in the model.  The section
    order is fixed as per issue #40: physics, math, tools, problems, learning,
    language.
    """
    return {
        "title": t("guide.title"),
        "intro": t("guide.intro"),
        "close": t("ui.close"),
        "sections": [
            {"head": t(f"guide.{s}.head"), "body": t(f"guide.{s}.body")}
            for s in _GUIDE_SECTIONS
        ],
    }


def solve_formula(formula_key: str, values: Mapping[str, str]) -> dict:
    """Solve ``formula_key`` from string ``values`` (symbol -> text field).

    Replicates ``FormulaPanel._compute`` exactly: blank-but-one detection, the
    not-a-number / no-empty / too-many-empty guards and ``SolveError`` mapping.
    Returns ``{"ok": True, "target", "answer"}`` or ``{"ok": False, "error"}`` —
    both already localized.
    """
    formula = _formula_index().get(formula_key)
    if formula is None:
        return {"ok": False, "error": t("error.no_solver", var=formula_key)}

    known: dict[str, float] = {}
    empty: list[str] = []
    for var in formula.variables:
        text = str(values.get(var.symbol, "") or "").strip().replace(",", ".")
        if not text:
            empty.append(var.symbol)
            continue
        try:
            known[var.symbol] = float(text)
        except ValueError:
            return {
                "ok": False,
                "error": t("error.not_a_number", value=text, field=t(var.name_key)),
            }

    if len(empty) == 0:
        return {"ok": False, "error": t("error.no_empty_field")}
    if len(empty) > 1:
        names = ", ".join(t(formula.variable(s).name_key) for s in empty)
        return {"ok": False, "error": t("error.too_many_empty", fields=names)}

    target = empty[0]
    try:
        value = formula.solve(target, known)
    except SolveError as exc:
        return {"ok": False, "error": _solve_error_message(formula, exc)}

    var = formula.variable(target)
    unit = f" {t(var.unit_key)}" if var.unit_key else ""
    return {
        "ok": True,
        "target": target,
        "answer": f"{var.symbol} = {_format_number(value)}{unit}",
    }
