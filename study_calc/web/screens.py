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


def _cas_operation_learning(op: str) -> list[dict]:
    """The before-a-result learning panel for an op: its topic, else a hint."""
    topic = load_topic(f"cas_{op}", i18n.language)
    if topic is not None:
        return _topic_blocks(t(f"cas.op.{op}"), topic)
    return [
        {"type": "heading", "text": t("cas.steps_title")},
        {"type": "hint", "text": t("cas.steps_placeholder")},
    ]


def cas_screen() -> dict:
    """The CAS screen model: operations + labels, or a SymPy-absent notice.

    When SymPy is not installed the model is ``{"available": False, ...}`` and the
    frontend shows the notice (mirroring the Tk ``cas.unavailable`` fallback).
    """
    try:
        from ..core import cas
    except ImportError:
        return {"available": False, "title": t("tab.cas"), "notice": t("cas.unavailable")}

    operations = [
        {
            "id": op,
            "label": t(f"cas.op.{op}"),
            "usesVariable": op in cas.USES_VARIABLE,
            "fields": [
                {"id": fid, "label": t(f"cas.field.{fid}")}
                for fid in cas.OP_FIELDS.get(op, ())
            ],
            "learning": _cas_operation_learning(op),
        }
        for op in cas.OPERATIONS
    ]
    return {
        "available": True,
        "title": t("tab.cas"),
        "labels": {
            "operation": t("cas.operation"),
            "expression": t("cas.expression"),
            "variable": t("cas.variable"),
            "hint": t("cas.hint"),
            "compute": t("ui.compute"),
            "clear": t("ui.clear"),
            "stepsTitle": t("cas.steps_title"),
            "openFull": t("ui.open_full"),
            "relatedFormulas": t("ui.related_formulas"),
            "seeAlso": t("ui.see_also"),
        },
        "operations": operations,
    }


def cas_run(op: str, expression: str, variable: str = "", fields: Mapping[str, str] | None = None) -> dict:
    """Run a CAS operation; mirror of ``CasPanel._compute``.

    Returns ``{"ok": True, "title", "steps"}`` (each step ``{"text", "answer"}``,
    ``answer`` marking the green result line) or ``{"ok": False, "error"}`` — both
    localized. Powers are rendered ``x^2`` (not SymPy's ``x**2``), as in the GUI.
    """
    try:
        from ..core import cas
    except ImportError:
        return {"ok": False, "error": t("cas.unavailable")}

    extra = {fid: str(value or "").strip() for fid, value in (fields or {}).items()}
    try:
        result = cas.run(op, (expression or "").strip(), (variable or "").strip(), **extra)
    except cas.CasError as exc:
        return {"ok": False, "error": t(f"error.{exc.code}", **exc.params)}

    steps = [
        {
            "text": t(step.key, **step.params).replace("**", "^"),
            "answer": _is_cas_answer(step.key),
        }
        for step in result.steps
    ]
    if not steps:  # defensive: an op without steps still shows an answer line
        steps = [{"text": f"{result.input_text}  →  {result.output_text}", "answer": True}]
    return {"ok": True, "title": t("cas.steps_title"), "steps": steps}


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
