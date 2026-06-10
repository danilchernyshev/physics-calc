"""Tests for the GUI's subject grouping (``study_calc/navigation.py``).

These validate the navigation spec without a display: the module must stay Tk-free
(so it is importable headless), every section it places must exist in ``SECTIONS``
and be placed exactly once, tool/subject ids must be known, and the labels it refers
to must resolve in English.
"""

from pathlib import Path

import pytest

from study_calc import navigation
from study_calc.navigation import Placeholder, Problems, Section, Tool, SUBJECTS, TOOL_NAMES
from study_calc.domains import SECTIONS
from study_calc.i18n import I18n

KNOWN_SUBJECTS = {"physics", "math", "tools", "chemistry"}


def _items():
    for _subject_id, items in SUBJECTS:
        yield from items


def test_navigation_module_is_tk_free():
    """The spec must not import Tkinter, or it could not be unit-tested headless."""
    source = Path(navigation.__file__).read_text(encoding="utf-8")
    assert "import tkinter" not in source
    assert "from tkinter" not in source
    assert "from study_calc.gui" not in source


def test_subject_ids_are_known_and_unique():
    ids = [subject_id for subject_id, _it in SUBJECTS]
    assert set(ids) <= KNOWN_SUBJECTS
    assert len(ids) == len(set(ids)), "duplicate subject id"


def test_sections_cover_SECTIONS_exactly_once():
    placed = [item.section_id for item in _items() if isinstance(item, Section)]
    assert sorted(placed) == sorted(SECTIONS), "sections must each be placed once"


def test_tool_names_are_known():
    for item in _items():
        if isinstance(item, Tool):
            assert item.name in TOOL_NAMES, item.name


def test_problems_subjects_are_known():
    for item in _items():
        if isinstance(item, Problems):
            assert item.subject_id in KNOWN_SUBJECTS, item.subject_id


def test_chemistry_surfaces_its_problems():
    """Chemistry is no longer a placeholder — it shows its practice problems."""
    chemistry = dict(SUBJECTS)["chemistry"]
    assert any(isinstance(item, Problems) and item.subject_id == "chemistry"
               for item in chemistry)


def test_navigation_labels_resolve_in_english():
    catalog = I18n()._catalogs["en"]
    for subject_id, _it in SUBJECTS:
        assert f"subject.{subject_id}" in catalog, subject_id
    assert "tab.problems" in catalog
    for item in _items():
        if isinstance(item, Placeholder):
            assert item.message_key in catalog, item.message_key
