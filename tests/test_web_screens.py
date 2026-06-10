"""Tests for the per-screen models and the formula-solve bridge (issue #6).

The screen builders are pure Python (no Tkinter / PyWebView), so the physics
formula screen — its model, the solve flow and the learning blocks — is verified
headlessly here, exactly as the shell model is in ``test_web_shell.py``. The
frontend itself is vanilla JS; we lint its wiring (asset order, the exposed
surface) the same way ``test_web_components.py`` does.
"""

from __future__ import annotations

from pathlib import Path

from study_calc.i18n import i18n, t
from study_calc.web import screens
from study_calc.web.bridge import Bridge

FRONTEND = Path(__file__).resolve().parent.parent / "study_calc" / "web" / "frontend"


# --- formula screen model ---


def test_formula_screen_lists_section_formulas_with_variables():
    screen = screens.formula_screen("mechanics")
    assert screen["sectionId"] == "mechanics"
    assert screen["formulas"], "mechanics should have formulas"
    first = screen["formulas"][0]
    assert {"key", "name", "expression", "variables", "learning"} <= first.keys()
    assert all("symbol" in v and "label" in v for v in first["variables"])
    # Labels are localized prose (e.g. 'Force (F, N)'), never raw keys.
    assert not first["name"].startswith("formula.")
    assert "var." not in first["variables"][0]["label"]


def test_formula_screen_accepts_bare_and_navigation_item_ids():
    bare = screens.formula_screen("mechanics")
    prefixed = screens.formula_screen("section:mechanics")
    assert bare == prefixed


def test_formula_screen_unknown_section_is_empty_not_an_error():
    screen = screens.formula_screen("does-not-exist")
    assert screen["formulas"] == []


def test_all_formula_screens_covers_every_section():
    from study_calc.domains import SECTIONS

    assert set(screens.all_formula_screens()) == set(SECTIONS)


# --- solve flow (mirrors FormulaPanel._compute) ---


def test_solve_formula_computes_the_single_empty_variable():
    # Newton's second law F = m·a, solving for F from m=2, a=3.
    res = screens.solve_formula("newton_2", {"F": "", "m": "2", "a": "3"})
    assert res["ok"] is True
    assert res["target"] == "F"
    assert res["answer"] == "F = 6 N"


def test_solve_formula_accepts_comma_decimal_separator():
    res = screens.solve_formula("newton_2", {"F": "", "m": "2,5", "a": "2"})
    assert res["ok"] is True
    assert res["answer"] == "F = 5 N"


def test_solve_formula_requires_exactly_one_empty_field():
    full = screens.solve_formula("newton_2", {"F": "1", "m": "2", "a": "3"})
    assert full == {"ok": False, "error": t("error.no_empty_field")}
    two_empty = screens.solve_formula("newton_2", {"F": "", "m": "", "a": "3"})
    assert two_empty["ok"] is False
    # The two empty fields are named (localized) in the message.
    assert "," in two_empty["error"]


def test_solve_formula_reports_a_non_numeric_value():
    res = screens.solve_formula("newton_2", {"F": "", "m": "abc", "a": "3"})
    assert res["ok"] is False
    # The field name is the localized variable name, not the symbol/key.
    assert "abc" in res["error"]


def test_solve_formula_maps_solve_errors_to_localized_messages():
    # Solving for m = F / a with a = 0 raises a zero-division SolveError.
    res = screens.solve_formula("newton_2", {"F": "4", "m": "", "a": "0"})
    assert res == {"ok": False, "error": t("error.zero_division")}


# --- learning blocks (mirror of ExplanationPanel.show) ---


def test_formula_learning_has_theory_steps_terms_and_links():
    blocks = screens.formula_learning("newton_2")
    kinds = [b["type"] for b in blocks]
    assert "heading" in kinds and "body" in kinds
    assert "steps" in kinds
    assert "links" in kinds
    # The theory body is localized prose, not a 'theory.*' key.
    body = next(b for b in blocks if b["type"] == "body")
    assert not body["text"].startswith("theory.")


def test_formula_learning_terms_carry_full_text_and_see_also():
    blocks = screens.formula_learning("newton_2")
    terms = [b for b in blocks if b["type"] == "terms"]
    if not terms:  # not every formula has glossary terms
        return
    item = terms[0]["items"][0]
    assert {"title", "short", "full", "formulas", "seeAlso"} <= item.keys()
    # see_also entries are resolved (have their own title), so the modal is self-contained.
    for rel in item["seeAlso"]:
        assert rel["title"]


def test_formula_learning_unknown_key_is_empty():
    assert screens.formula_learning("nope") == []


# --- CAS (symbolic math) screen ---


def test_cas_screen_lists_operations_with_fields_and_learning():
    from study_calc.core import cas

    screen = screens.cas_screen()
    assert screen["available"] is True
    assert [o["id"] for o in screen["operations"]] == list(cas.OPERATIONS)
    # The fields are the full, ordered input set: expression, then variable (only
    # for ops that use one), then the per-op extras (rate -> a, b).
    rate = next(o for o in screen["operations"] if o["id"] == "rate")
    assert [f["id"] for f in rate["fields"]] == ["expression", "variable", *cas.OP_FIELDS["rate"]]
    # 'evaluate' takes no variable, so its only field is the expression.
    evaluate = next(o for o in screen["operations"] if o["id"] == "evaluate")
    assert [f["id"] for f in evaluate["fields"]] == ["expression"]
    # Every operation carries its before-a-result learning panel.
    assert all(o["learning"] for o in screen["operations"])


def test_cas_run_returns_steps_with_a_green_answer():
    res = screens.cas_run("derivative", {"expression": "x^2", "variable": "x"})
    assert res["ok"] is True
    assert any(s["answer"] for s in res["steps"])
    # The result line is the answer; powers render with ^, not Python's **.
    answer = next(s for s in res["steps"] if s["answer"])
    assert "**" not in answer["text"]


def test_cas_run_maps_cas_errors_to_localized_messages():
    res = screens.cas_run("factor", {"expression": "(("})
    assert res["ok"] is False
    assert res["error"] and not res["error"].startswith("error.")


def test_cas_run_empty_expression_is_an_error():
    res = screens.cas_run("simplify", {})
    assert res["ok"] is False


def test_cas_screen_degrades_when_sympy_is_absent(monkeypatch):
    # Simulate `from ..core import cas` failing (SymPy not installed): drop the
    # cached submodule + the package attribute, and poison sys.modules so the
    # re-import raises ImportError — exactly the path the Tk fallback tab uses.
    import sys

    import study_calc.core

    monkeypatch.delattr(study_calc.core, "cas", raising=False)
    monkeypatch.setitem(sys.modules, "study_calc.core.cas", None)

    screen = screens.cas_screen()
    assert screen["available"] is False
    assert screen["notice"]
    # And cas_run degrades the same way, not crashes.
    assert screens.cas_run("simplify", {"expression": "x"})["ok"] is False


def test_cas_screen_is_localized_on_language_switch():
    try:
        en = Bridge().cas_screen()
        bridge = Bridge()
        bridge.set_language("ru")
        ru = bridge.cas_screen()
        assert en["labels"]["compute"] != ru["labels"]["compute"]
    finally:
        i18n.set_language("en")


# --- Vectors screen (shares the operations model with CAS) ---


def test_vector_screen_lists_operations_with_per_op_fields():
    from study_calc.core import vectors

    screen = screens.vector_screen()
    assert screen["available"] is True
    assert [o["id"] for o in screen["operations"]] == list(vectors.OPERATIONS)
    # magnitude needs only u; add needs u + v; scale needs u + k.
    fields_of = {o["id"]: [f["id"] for f in o["fields"]] for o in screen["operations"]}
    assert fields_of["magnitude"] == ["u"]
    assert fields_of["add"] == ["u", "v"]
    assert fields_of["scale"] == ["u", "k"]
    assert all(o["learning"] for o in screen["operations"])


def test_vector_run_returns_steps_with_a_green_answer():
    res = screens.vector_run("add", {"u": "1, 2", "v": "3, 4"})
    assert res["ok"] is True
    answer = next(s for s in res["steps"] if s["answer"])
    assert "(4, 6)" in answer["text"]


def test_vector_run_maps_vector_errors_to_localized_messages():
    res = screens.vector_run("add", {"u": "1, 2", "v": "3, 4, 5"})
    assert res["ok"] is False
    assert res["error"] and not res["error"].startswith("error.")


def test_operations_screens_share_one_frontend_renderer():
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # One generic renderer backs both CAS and vectors (no per-screen copy).
    assert "operations(model, ctx)" in js
    assert "cas(model, ctx)" not in js
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "Screens.operations" in shell
    assert "cas_screen" in shell and "vector_screen" in shell


# --- language switching ---


def test_language_switch_relocalizes_the_screen():
    try:
        en = Bridge().formula_screen("mechanics")
        bridge = Bridge()
        bridge.set_language("ru")
        ru = bridge.formula_screen("mechanics")
        assert en["labels"]["compute"] != ru["labels"]["compute"]
        assert en["formulas"][0]["name"] != ru["formulas"][0]["name"]
    finally:
        i18n.set_language("en")


# --- frontend wiring ---


def test_index_loads_screen_assets_in_order():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "screens.css" in html and "screens.js" in html
    # screens.js needs components.js (UI) and dom.js (h) before it, and runs
    # before shell.js (which mounts screens).
    assert html.index("components.js") < html.index("screens.js") < html.index("shell.js")


def test_screens_js_exposes_surface_and_shell_dispatches():
    screens_js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    assert "window.Screens = Screens" in screens_js
    assert "formula(" in screens_js
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "mountScreen" in shell and "formula_screen" in shell and "callApi" in shell


def test_screens_js_handles_enter_and_guards_stale_solves():
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # Enter in a field solves (parity with the Tk <Return> binding).
    assert "'Enter'" in js and "compute()" in js
    # A generation token drops a late async result (formula/op change, Clear, or
    # a newer compute) so it never clobbers the current panel.
    assert "run !== st.run" in js


def test_screens_css_uses_only_tokens():
    import re

    css = (FRONTEND / "screens.css").read_text(encoding="utf-8")
    # Hex colors are forbidden (token-only); rgba overlays are allowed.
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    assert "var(--color-" in css and "var(--space-" in css
