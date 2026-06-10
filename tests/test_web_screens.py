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


# --- guide overlay model (issue #40) ---

_GUIDE_SECTION_IDS = ("physics", "math", "tools", "problems", "learning", "language", "credits")


def test_guide_screen_model():
    """guide_screen() returns a fully i18n-sourced model, never literals."""
    model = screens.guide_screen()

    # Top-level keys are present.
    assert "title" in model and "intro" in model and "sections" in model

    # Title and intro come from the guide.* i18n keys (not raw keys, not empty).
    assert model["title"] == t("guide.title")
    assert model["intro"] == t("guide.intro")
    assert model["title"] and not model["title"].startswith("guide.")
    assert model["intro"] and not model["intro"].startswith("guide.")

    # The close-button label is i18n-sourced too (no hardcoded "Close" in the
    # frontend); the overlay reads model.close for the × button's aria-label.
    assert model["close"] == t("ui.close")
    assert model["close"] and not model["close"].startswith("ui.")

    # Exactly seven sections in the canonical order (issue #41 appends "credits").
    assert len(model["sections"]) == 7, (
        f"expected 7 sections, got {len(model['sections'])}"
    )
    for i, sid in enumerate(_GUIDE_SECTION_IDS):
        sec = model["sections"][i]
        assert {"head", "body"} <= sec.keys(), f"section {sid} missing head/body"
        # Values are sourced from i18n, not hardcoded English.
        assert sec["head"] == t(f"guide.{sid}.head"), f"wrong head for {sid}"
        assert sec["body"] == t(f"guide.{sid}.body"), f"wrong body for {sid}"
        # Non-empty (all five locales carry these keys).
        assert sec["head"], f"empty head for {sid}"
        assert sec["body"], f"empty body for {sid}"

    # Copyright footer is present, i18n-sourced, and non-empty (issue #41).
    assert "copyright" in model, "model missing 'copyright' field"
    assert model["copyright"] == t("guide.credits.copyright")
    assert model["copyright"], "copyright must not be empty"
    assert not model["copyright"].startswith("guide."), "copyright must be resolved, not a raw key"


def test_guide_credits_names_both_authors_and_matches_license():
    """Credits & licence names both authors and stays aligned with LICENSE (#41).

    QA on #41 required the displayed author name to be reconciled with the
    repository LICENSE; the follow-up decision keeps *both* names (Mark
    Chernyshev, the student author, and his father Danil Chernyshev). This
    guards that the in-app credits and the LICENSE copyright holder list both
    names, and that the © line is byte-identical across every locale.
    """
    import json

    repo_root = Path(__file__).resolve().parent.parent
    names = ("Mark Chernyshev", "Danil Chernyshev")

    # LICENSE lists both authors on its copyright line.
    license_text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Mark Chernyshev and Danil Chernyshev" in license_text

    # The © line is a legal notice: byte-identical across every locale and
    # carrying both names in canonical Latin form. (The body prose may
    # transliterate the names per each language's convention — e.g. ru renders
    # "Марком Чернышевым" — so only the © line is asserted name-for-name.)
    locales_dir = repo_root / "study_calc" / "locales"
    copyrights = set()
    for path in sorted(locales_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cr = data["guide.credits.copyright"]
        copyrights.add(cr)
        for name in names:
            assert name in cr, f"{path.name}: copyright missing {name!r}"

    assert len(copyrights) == 1, f"copyright line differs across locales: {copyrights}"


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
    # Every vector field is a persistent main input — the frontend keeps u/v/k
    # across op changes (mirror of the Tk VectorPanel, which only disables them).
    assert all(f["persist"] for o in screen["operations"] for f in o["fields"])


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


# --- Unit converter screen ---


def test_converter_screen_lists_categories_with_units_and_labels():
    from study_calc.core.units import categories, units_of

    screen = screens.converter_screen()
    assert screen["available"] is True
    # All categories from the engine are present and in the same order.
    assert [c["id"] for c in screen["categories"]] == categories()
    # Each category carries localized labels and its unit list.
    first = screen["categories"][0]
    assert not first["label"].startswith("category.")   # localized, not a raw key
    assert [u["id"] for u in first["units"]] == units_of(first["id"])
    assert not first["units"][0]["label"].startswith("unit.")
    # Temperature is the special-cased category; its units must also be present.
    temp = next(c for c in screen["categories"] if c["id"] == "temperature")
    assert {u["id"] for u in temp["units"]} == {"celsius", "kelvin", "fahrenheit"}
    # Chrome labels use the same i18n keys as the Tk ConverterPanel.
    labels = screen["labels"]
    assert labels["category"] == t("ui.category")
    assert labels["value"] == t("ui.value")
    assert labels["from"] == t("ui.from")
    assert labels["to"] == t("ui.to")
    assert labels["convert"] == t("ui.convert")
    assert labels["clear"] == t("ui.clear")
    assert labels["result"] == t("ui.result")


def test_convert_run_linear_happy_path():
    # 1 km  =  1000 m (a linear category, integer result).
    res = screens.convert_run("length", "1", "kilometer", "meter")
    assert res["ok"] is True
    assert "1 km" in res["result"] and "1000 m" in res["result"]
    assert "=" in res["result"]


def test_convert_run_accepts_comma_decimal_separator():
    res = screens.convert_run("length", "1,5", "kilometer", "meter")
    assert res["ok"] is True
    assert "1500 m" in res["result"]


def test_convert_run_temperature_happy_path():
    # Temperature is special-cased (offset conversion, not linear).
    res = screens.convert_run("temperature", "0", "celsius", "kelvin")
    assert res["ok"] is True
    # 0 °C = 273.15 K (not a whole number, so 6 sig-digit formatting applies).
    assert "273.15" in res["result"] or "273.15 K" in res["result"]
    assert "0 °C" in res["result"]


def test_convert_run_maps_conversion_error_to_localized_message():
    res = screens.convert_run("length", "5", "meter", "celsius")  # mismatched units
    assert res["ok"] is False
    assert res["error"] and not res["error"].startswith("error.")


def test_convert_run_maps_not_a_number_to_localized_message():
    res = screens.convert_run("length", "abc", "meter", "kilometer")
    assert res["ok"] is False
    assert "abc" in res["error"]


def test_converter_screen_is_localized_on_language_switch():
    try:
        en = Bridge().converter_screen()
        bridge = Bridge()
        bridge.set_language("ru")
        ru = bridge.converter_screen()
        # Category labels must differ between English and Russian.
        en_labels = [c["label"] for c in en["categories"]]
        ru_labels = [c["label"] for c in ru["categories"]]
        assert en_labels != ru_labels
        # Chrome labels must differ too.
        assert en["labels"]["convert"] != ru["labels"]["convert"]
    finally:
        i18n.set_language("en")


def test_converter_screen_has_dedicated_frontend_renderer():
    # The converter is category+units shaped, not operation+fields shaped, so it
    # warrants its own renderer rather than reusing Screens.operations.
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    assert "converter(model, ctx)" in js
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "Screens.converter" in shell
    assert "converter_screen" in shell
    assert "convert_run" in shell


# --- Periodic-table screen ---


def test_periodic_screen_lists_all_elements_with_positions_and_series():
    screen = screens.periodic_screen()
    assert screen["available"] is True
    els = screen["elements"]
    assert len(els) == 118
    # Each element must carry the full set of fields the grid renderer needs.
    required = {"number", "symbol", "name", "mass", "group", "period",
                "category", "xpos", "ypos", "series"}
    assert required <= set(els[0].keys())
    # xpos/ypos must span the 18-column periodic table (columns 1-18, rows 1-10).
    assert all(1 <= e["xpos"] <= 18 and 1 <= e["ypos"] <= 10 for e in els)
    # Hydrogen: top-left corner, diatomic nonmetal.
    h_el = next(e for e in els if e["symbol"] == "H")
    assert h_el["xpos"] == 1 and h_el["ypos"] == 1
    assert h_el["series"] == "diatomic-nonmetal"
    # Synthetic/unknown elements map to the fallback slug, not a hex colour.
    assert all(not e["series"].startswith("#") for e in els)
    # Labels are localized prose — never raw i18n keys.
    L = screen["labels"]
    assert not L["molarMass"].startswith("ui.")
    assert not L["equation"].startswith("ui.")
    assert not L["balance"].startswith("ui.")


def test_molar_mass_run_happy_path():
    # H2O: 2 × 1.008 + 15.999 = 18.015 g/mol.
    res = screens.molar_mass_run("H2O")
    assert res["ok"] is True
    # Mirror the Tk format: "H2O = 18.015 g/mol  (H:2, O:1)".
    assert "H2O" in res["result"]
    assert "18." in res["result"]
    assert "g/mol" in res["result"]       # unit label (English default)
    assert "H:2" in res["result"] and "O:1" in res["result"]


def test_molar_mass_run_unknown_element_returns_localized_error():
    res = screens.molar_mass_run("Xx")   # "Xx" is not a real element
    assert res["ok"] is False
    # Localized prose, not the raw "error.*" key.
    assert res["error"] and not res["error"].startswith("error.")


def test_balance_run_happy_path():
    # 2H2 + O2 -> 2H2O
    res = screens.balance_run("H2 + O2 -> H2O")
    assert res["ok"] is True
    assert "->" in res["result"] and "H2O" in res["result"]


def test_balance_run_no_arrow_returns_localized_error():
    res = screens.balance_run("H2 O2 H2O")   # no arrow separator
    assert res["ok"] is False
    assert res["error"] and not res["error"].startswith("error.")


def test_periodic_screen_has_dedicated_frontend_renderer():
    # The periodic table is its own 118-cell grid — not a section, CAS/vectors
    # operation, or converter — so it gets its own Screens.periodic renderer.
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    assert "periodic(model, ctx)" in js
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "Screens.periodic" in shell
    assert "periodic_screen" in shell
    assert "molar_mass_run" in shell
    assert "balance_run" in shell


# --- Problems (practice) screen ---


def test_problems_screen_lists_subject_problems_with_statements():
    screen = screens.problems_screen("physics")
    assert screen["subjectId"] == "physics"
    problems = screen["problems"]
    assert problems, "physics should have practice problems"
    p = problems[0]
    # Each problem carries its statement, hidden solution and metadata fields.
    required = {"id", "title", "badge", "given", "find", "steps", "answer",
                "videoUrl", "topic"}
    assert required <= set(p.keys())
    # Title is localized prose, never a raw i18n key.
    assert p["title"] and not p["title"].startswith("ui.")
    # Labels are localized prose too.
    L = screen["labels"]
    assert not L["choose"].startswith("ui.")
    assert not L["revealSteps"].startswith("ui.")
    assert not L["revealAnswer"].startswith("ui.")


def test_problems_screen_accepts_bare_and_navigation_item_ids():
    bare = screens.problems_screen("math")
    nav = screens.problems_screen("problems:math")
    assert bare == nav
    assert bare["subjectId"] == "math"


def test_problems_screen_empty_subject_yields_no_problems():
    # The Tools subject has no Problems item, so its problem set is empty — the
    # frontend renders the quiet `empty` hint rather than a list.
    screen = screens.problems_screen("tools")
    assert screen["problems"] == []
    assert not screen["labels"]["empty"].startswith("problems.")


def test_problem_carries_curriculum_badge_when_it_has_courses():
    # Chemistry problems carry Ontario course codes, rendered as a curriculum badge.
    problems = screens.problems_screen("chemistry")["problems"]
    badged = [p for p in problems if p["badge"]]
    assert badged, "expected at least one chemistry problem with a curriculum badge"
    assert badged[0]["badge"].startswith(t("ui.curriculum"))


def test_problem_video_link_and_baked_topic_blocks():
    problems = screens.problems_screen("physics")["problems"]
    # At least one physics problem links a video solution (a real URL).
    assert any(p["videoUrl"].startswith("http") for p in problems)
    # A problem with a backing topic bakes its learning blocks (heading + body),
    # so "Learn the theory" expands inline with no round-trip.
    with_topic = next(p for p in problems if p["topic"])
    kinds = {block["type"] for block in with_topic["topic"]}
    assert "heading" in kinds


def test_all_problem_screens_covers_every_problems_subject():
    from study_calc.navigation import SUBJECTS, Problems

    expected = {
        item.subject_id
        for _subject, items in SUBJECTS
        for item in items
        if isinstance(item, Problems)
    }
    assert set(screens.all_problem_screens().keys()) == expected


def test_problems_screen_is_localized_on_language_switch():
    try:
        en = Bridge().problems_screen("physics")
        bridge = Bridge()
        bridge.set_language("ru")
        ru = bridge.problems_screen("physics")
        # Chrome labels must differ between English and Russian.
        assert en["labels"]["choose"] != ru["labels"]["choose"]
        assert en["labels"]["revealSteps"] != ru["labels"]["revealSteps"]
    finally:
        i18n.set_language("en")


def test_problems_screen_has_dedicated_frontend_renderer():
    # The problems surface is list+solution shaped, not section/operation/converter
    # shaped, so it gets its own Screens.problems renderer wired in shell.js.
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    assert "problems(model)" in js
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "Screens.problems" in shell
    assert "problems_screen" in shell


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


# --- issue #51: closeOverlays wiring ---


def test_screens_js_exports_close_overlays():
    """closeOverlays() must be on the Screens object exported to the shell."""
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # The method lives on the Screens object literal (before window.Screens = Screens).
    assert "closeOverlays()" in js
    assert "window.Screens = Screens" in js


def test_shell_calls_close_overlays_before_rebuild():
    """render() in shell.js must call Screens.closeOverlays() before rebuilding #app.

    DOM-level verification is not feasible without a headless browser, so this
    test checks the source wiring: the call must appear in shell.js, and it
    must come before app.replaceChildren (i.e. before the #app rebuild).
    """
    shell = (FRONTEND / "shell.js").read_text(encoding="utf-8")
    assert "Screens.closeOverlays()" in shell
    # The closeOverlays call must precede the DOM rebuild within render().
    close_pos = shell.index("Screens.closeOverlays()")
    rebuild_pos = shell.index("app.replaceChildren(")
    assert close_pos < rebuild_pos, (
        "Screens.closeOverlays() must be called before app.replaceChildren() in render()"
    )


def test_screens_js_uses_shared_destroy_overlay():
    """Both openGuide and openConcept route teardown through _destroyOverlay.

    The shared helper is the single place that handles focus tracking,
    preventing duplicated or divergent focus-restore logic (issue #51).
    """
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # The helper is defined at module level.
    assert "function _destroyOverlay(" in js
    # Both overlay types call it.
    assert js.count("_destroyOverlay(") >= 3  # closeOverlays + openGuide + openConcept


# --- issue #19 / #52: localized close label ---
#
# Issue #19 (bug): aria-label "Close" was hardcoded in screens.js.
# Issue #52 (linked enhancement): formally add ui.close to all five locale
# catalogs, thread it through every screen's labels payload (formula_screen,
# cas_screen, vector_screen via _operation_labels, and guide_screen), and
# replace the hardcoded literal with L.close / model.close in screens.js.
# Both issues are addressed by the same set of changes.


def test_close_key_present_in_all_locales():
    """ui.close must be in every locale catalog (issue #19).

    The key is used as the aria-label for every overlay close (×) button, so it
    must be translated in all five languages — not just the English fallback.
    A missing translation would silently fall back to the raw key string
    ``"ui.close"``, which would be read aloud by a screen reader verbatim.
    """
    import json
    from study_calc.i18n import _LOCALES_DIR

    for code in ("en", "es", "fr", "ru", "uk"):
        catalog = json.loads((_LOCALES_DIR / f"{code}.json").read_text(encoding="utf-8"))
        assert "ui.close" in catalog, (
            f"{code}.json is missing 'ui.close' — "
            "add a translation so the aria-label is never an untranslated key"
        )
        value = catalog["ui.close"]
        assert value and not value.startswith("ui."), (
            f"{code}.json has 'ui.close' = {value!r}, which looks like a fallback key"
        )


def test_formula_screen_labels_carry_localized_close():
    """formula_screen() labels include close == t("ui.close"), not a hardcoded string."""
    screen = screens.formula_screen("mechanics")
    labels = screen["labels"]
    assert "close" in labels, "formula_screen labels must include 'close'"
    assert labels["close"] == t("ui.close")
    assert labels["close"] and not labels["close"].startswith("ui.")


def test_cas_screen_labels_carry_localized_close():
    """cas_screen() labels include close == t("ui.close") (issue #19).

    The key-term pop-up (openConcept) is reachable from every operations screen
    (CAS and vectors) via the learning card, so the close label must be wired
    into the operations labels payload too — not only formula_screen.
    """
    screen = screens.cas_screen()
    if not screen.get("available", True):
        return  # SymPy absent — no labels payload in this case
    labels = screen["labels"]
    assert "close" in labels, "cas_screen labels must include 'close'"
    assert labels["close"] == t("ui.close")
    assert labels["close"] and not labels["close"].startswith("ui.")


def test_close_label_changes_with_language_switch():
    """The close label in both overlay models changes when the language is switched."""
    try:
        en_guide = Bridge().guide_screen()
        en_formula = Bridge().formula_screen("mechanics")

        bridge = Bridge()
        bridge.set_language("ru")
        ru_guide = bridge.guide_screen()
        ru_formula = bridge.formula_screen("mechanics")

        # Guide overlay close label.
        assert en_guide["close"] != ru_guide["close"], (
            "guide_screen close label must differ between English and Russian"
        )
        # Formula screen labels close (used by openConcept via L.close).
        assert en_formula["labels"]["close"] != ru_formula["labels"]["close"], (
            "formula_screen labels.close must differ between English and Russian"
        )
    finally:
        i18n.set_language("en")


def test_screens_js_has_no_hardcoded_english_close_string():
    """No user-facing 'Close' literal must remain in screens.js (issue #19 / #52).

    Both overlay buttons read their aria-label from the localized model
    (model.close for openGuide, L.close for openConcept), so the only
    occurrences of the word 'Close' in the source should be in comments.
    """
    js = (FRONTEND / "screens.js").read_text(encoding="utf-8")
    # Strip comment lines (// ...) and check no standalone 'Close' string literal remains.
    non_comment_lines = [
        line for line in js.splitlines()
        if not line.lstrip().startswith("//")
    ]
    code_only = "\n".join(non_comment_lines)
    # 'Close' as a quoted JS string literal would be 'Close' or "Close".
    assert "'Close'" not in code_only, "Hardcoded 'Close' string found in screens.js code"
    assert '"Close"' not in code_only, 'Hardcoded "Close" string found in screens.js code'
