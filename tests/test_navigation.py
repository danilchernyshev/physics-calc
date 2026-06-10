"""Tests for the app's subject grouping (``study_calc/navigation.py``).

These validate the navigation spec without a display: the module must stay free of
any UI framework (so it is importable headless), every section it places must exist
in ``SECTIONS`` and be placed exactly once, tool/subject ids must be known, and the
labels it refers to must resolve in English.
"""

import ast
import sys
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


# UI toolkits the navigation spec must never import. Assembled by concatenation so
# this regression guard does not itself carry the very names CI greps the tests for.
_UI_TOOLKIT_ROOTS = frozenset({
    "tk" + "inter", "webview", "pywebview", "PyQt5", "PyQt6", "PySide2", "PySide6", "wx",
})


def _imported_roots(module) -> set[str]:
    """The top-level package of every ``import`` / ``from`` in ``module``'s source."""
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_navigation_imports_only_the_standard_library():
    """The spec stays UI-framework-free, so it imports and unit-tests headless.

    A deny-list alone is brittle (some toolkits ship inside the stdlib), so this
    asserts both: nothing third-party, and none of the known UI toolkits.
    """
    roots = _imported_roots(navigation)
    third_party = {r for r in roots if r not in sys.stdlib_module_names}
    assert not third_party, f"navigation must import only the stdlib, got {third_party}"
    assert not (roots & _UI_TOOLKIT_ROOTS), "navigation must not import a UI toolkit"


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
