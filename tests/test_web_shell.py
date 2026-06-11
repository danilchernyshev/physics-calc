"""App-shell tests (issue #4).

Cover the headless pieces: the ``navigation`` item helpers and the
``web.bridge`` state model. The shell must be generated entirely from
``navigation.SUBJECTS`` (nothing hardcoded), every subject/item reachable, and a
language switch must relabel without changing the structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from study_calc import navigation
from study_calc.core.settings import Settings
from study_calc.i18n import i18n
from study_calc.web import app as web_app
from study_calc.web.bridge import Bridge, item_courses, item_visible, navigation_model

_FRONTEND = Path(__file__).resolve().parent.parent / "study_calc" / "web" / "frontend"


@pytest.fixture(autouse=True)
def _restore_language():
    """Bridge.set_language mutates the shared i18n singleton — restore it."""
    original = i18n.language
    yield
    i18n.set_language(original)


# --- navigation helpers ------------------------------------------------------

def test_item_helpers_cover_every_item():
    seen_ids = set()
    for _subject_id, items in navigation.SUBJECTS:
        for item in items:
            kind = navigation.item_kind(item)
            assert kind in {"section", "tool", "problems", "placeholder"}
            # ids are unique within a subject and label keys are non-empty.
            seen_ids.add(navigation.item_id(item))
            assert navigation.item_label_key(item)
    # Sanity: the ids really are distinct across the whole tree.
    total = sum(len(items) for _s, items in navigation.SUBJECTS)
    assert len(seen_ids) == total


def test_item_helpers_reject_unknown():
    for fn in (navigation.item_kind, navigation.item_id, navigation.item_label_key):
        with pytest.raises(TypeError):
            fn(object())


# --- bridge state ------------------------------------------------------------

def test_state_is_generated_from_subjects():
    state = Bridge().get_state()
    assert [s["id"] for s in state["subjects"]] == [sid for sid, _ in navigation.SUBJECTS]
    for (sid, items), model in zip(navigation.SUBJECTS, state["subjects"]):
        assert model["label"]  # localized, non-empty
        assert model["monogram"] == model["label"][:1].upper()
        assert model["tagline"]
        assert [it["id"] for it in model["items"]] == [navigation.item_id(i) for i in items]
        assert len(model["items"]) == len(items)


def test_state_exposes_languages_and_chrome_labels():
    state = Bridge().get_state()
    codes = {lang["code"] for lang in state["languages"]}
    assert {"en", "ru"} <= codes
    assert state["lang"] == i18n.language
    for key in ("appTitle", "subjectsHeading", "howToUse", "language", "placeholder"):
        assert state["labels"][key]


def test_set_language_relabels_without_restructuring():
    bridge = Bridge()
    en = bridge.get_state()
    ru = bridge.set_language("ru")
    assert ru["lang"] == "ru"
    # Same structure (ids unchanged), different labels.
    assert [s["id"] for s in ru["subjects"]] == [s["id"] for s in en["subjects"]]
    physics_en = next(s for s in en["subjects"] if s["id"] == "physics")
    physics_ru = next(s for s in ru["subjects"] if s["id"] == "physics")
    assert physics_en["label"] == "Physics"
    assert physics_ru["label"] == "Физика"
    assert physics_ru["tagline"] != physics_en["tagline"]


def test_set_language_rejects_unknown():
    with pytest.raises(ValueError):
        Bridge().set_language("zz")


# --- curriculum filter (epic #102, issue #125) -------------------------------

def _filtered_bridge(tmp_path, grade, course):
    """A Bridge whose settings store has the given active grade/course."""
    settings = Settings(path=tmp_path / "settings.json")
    settings.set_active_grade(grade)
    settings.set_active_course(course)
    return Bridge(settings=settings)


def _ids(subjects, sid):
    subject = next((s for s in subjects if s["id"] == sid), None)
    return [it["id"] for it in subject["items"]] if subject else None


def test_item_courses_unions_topic_and_problem_tags():
    # A tagged physics section, an untagged one, a multi-course problems item,
    # and a tool that carries no curriculum tag.
    assert item_courses(navigation.Section("mechanics")) == frozenset({"SPH4U"})
    assert item_courses(navigation.Section("thermodynamics")) == frozenset()
    assert item_courses(navigation.Problems("math")) == frozenset({"MDM4U", "MHF4U"})
    assert item_courses(navigation.Tool("cas")) == frozenset()


def test_item_visible_rules():
    # all → everything; tools/untagged always shown; tagged gated on the code.
    assert item_visible(navigation.Section("mechanics"), "all")
    assert item_visible(navigation.Tool("cas"), "SCH4U")  # tool: never hidden
    assert item_visible(navigation.Section("thermodynamics"), "SCH4U")  # untagged
    assert item_visible(navigation.Section("mechanics"), "SPH4U")
    assert not item_visible(navigation.Section("mechanics"), "SCH4U")


def test_filter_all_is_the_full_tree(tmp_path):
    full = Bridge().get_state()["subjects"]
    filtered = _filtered_bridge(tmp_path, "all", "all").get_state()["subjects"]
    assert [s["id"] for s in filtered] == [s["id"] for s in full]
    for a, b in zip(full, filtered):
        assert [i["id"] for i in a["items"]] == [i["id"] for i in b["items"]]


def test_filter_sph4u_hides_other_courses(tmp_path):
    subjects = _filtered_bridge(tmp_path, "12", "SPH4U").get_state()["subjects"]
    # Physics keeps all its items (3 SPH4U sections + the untagged thermo + the
    # SPH4U problems set).
    assert _ids(subjects, "physics") == [
        "section:mechanics", "section:thermodynamics",
        "section:electromagnetism", "section:waves", "problems:physics",
    ]
    # Math drops its MDM4U/MHF4U problems but keeps the two tools.
    assert _ids(subjects, "math") == ["tool:cas", "tool:vectors"]
    # Chemistry keeps only the periodic-table tool (its SCH4U content is hidden).
    assert _ids(subjects, "chemistry") == ["tool:periodic_table"]
    # Tools are never curriculum-gated.
    assert _ids(subjects, "tools") == ["tool:converter"]


def test_filter_sch4u_keeps_untagged_and_chemistry(tmp_path):
    subjects = _filtered_bridge(tmp_path, "12", "SCH4U").get_state()["subjects"]
    # Physics keeps only the untagged thermodynamics section.
    assert _ids(subjects, "physics") == ["section:thermodynamics"]
    # Chemistry keeps its full SCH4U-tagged set.
    assert _ids(subjects, "chemistry") == [
        "section:chem_solutions", "section:chem_acid_base",
        "tool:periodic_table", "problems:chemistry",
    ]


def test_navigation_model_drops_subjects_left_empty():
    # A synthetic course nothing is tagged with hides every tagged item; only
    # subjects retaining a tool/untagged item survive (physics keeps thermo).
    model = navigation_model("ZZZ9U", "en")
    ids = {s["id"] for s in model}
    assert "tools" in ids  # converter tool always survives
    physics = next((s for s in model if s["id"] == "physics"), None)
    assert physics and [i["id"] for i in physics["items"]] == ["section:thermodynamics"]


def test_set_active_course_method_filters_and_persists(tmp_path):
    bridge = _filtered_bridge(tmp_path, "all", "all")
    bridge.set_active_grade("12")
    state = bridge.set_active_course("SPH4U")
    assert _ids(state["subjects"], "chemistry") == ["tool:periodic_table"]
    # Clearing the grade restores the full tree.
    cleared = bridge.set_active_grade(None)
    assert _ids(cleared["subjects"], "chemistry") == [
        "section:chem_solutions", "section:chem_acid_base",
        "tool:periodic_table", "problems:chemistry",
    ]


def test_filter_is_stable_across_language_change(tmp_path):
    bridge = _filtered_bridge(tmp_path, "12", "SPH4U")
    en = bridge.get_state()
    ru = bridge.set_language("ru")
    # Same filtered structure in both languages...
    assert _ids(ru["subjects"], "chemistry") == _ids(en["subjects"], "chemistry")
    assert _ids(ru["subjects"], "math") == ["tool:cas", "tool:vectors"]
    # ...but relabelled.
    physics_ru = next(s for s in ru["subjects"] if s["id"] == "physics")
    assert physics_ru["label"] == "Физика"


# --- preview rendering (browser/screenshot path, no PyWebView) ---------------

def test_preview_html_inlines_state():
    html = web_app.render_preview_html()
    assert "window.__STUDY_CALC_STATE__" in html
    assert "shell.js" in html and "tokens.css" in html
    # The injected state is valid and carries the subjects.
    assert '"subjects"' in html


def test_preview_html_injects_bridge_api_stubs():
    # The browser/screenshot preview stands in for the live PyWebView bridge via
    # window.__STUDY_CALC_API__. If any per-screen stub were dropped, that screen
    # would silently fail to mount in the preview with no failing test (issue #24).
    html = web_app.render_preview_html()
    assert "window.__STUDY_CALC_API__" in html
    for method in (
        "formula_screen",
        "solve_formula",
        "cas_screen",
        "cas_run",
        "vector_screen",
        "vector_run",
    ):
        assert method in html, f"preview API stub for {method!r} is missing"


# --- favicon / window icon assets (issue #57) --------------------------------

def test_favicon_svg_exists():
    assert (_FRONTEND / "favicon.svg").is_file(), "favicon.svg is missing from frontend/"


def test_favicon_png_exists():
    assert (_FRONTEND / "favicon.png").is_file(), "favicon.png is missing from frontend/"


def test_window_icon_png_exists():
    assert (_FRONTEND / "icon.png").is_file(), "icon.png is missing from frontend/"


def test_window_icon_constant_points_at_asset():
    # run() passes this path to PyWebView's icon= argument.
    assert web_app._WINDOW_ICON.is_file()
    assert web_app._WINDOW_ICON.name == "icon.png"


def test_index_html_references_favicon():
    html = (_FRONTEND / "index.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in html, "index.html has no <link rel=\"icon\"> for the favicon"
    assert "favicon.svg" in html, "index.html does not reference favicon.svg"
    assert "favicon.png" in html, "index.html does not reference favicon.png"
