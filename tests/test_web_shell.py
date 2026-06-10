"""App-shell tests (issue #4).

Cover the headless pieces: the ``navigation`` item helpers and the
``web.bridge`` state model. The shell must be generated entirely from
``navigation.SUBJECTS`` (nothing hardcoded), every subject/item reachable, and a
language switch must relabel without changing the structure.
"""

from __future__ import annotations

import pytest

from study_calc import navigation
from study_calc.i18n import i18n
from study_calc.web import app as web_app
from study_calc.web.bridge import Bridge


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


# --- preview rendering (browser/screenshot path, no PyWebView) ---------------

def test_preview_html_inlines_state():
    html = web_app.render_preview_html()
    assert "window.__STUDY_CALC_STATE__" in html
    assert "shell.js" in html and "tokens.css" in html
    # The injected state is valid and carries the subjects.
    assert '"subjects"' in html
