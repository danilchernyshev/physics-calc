"""The GUI's subject grouping — what tabs exist and how they nest.

This is the single source of truth for the *navigation* layer, kept deliberately
free of Tkinter (and of any panel class) so it can be imported and unit-tested
headlessly. :mod:`study_calc.gui.app` reads :data:`SUBJECTS` and maps each item to
a concrete widget; the structure here only names *what* goes where.

The top level is a subject (Physics, Math, Tools, Chemistry). Each subject holds an
ordered list of items, every item one of four kinds:

- :class:`Section` — a physics formula section; ``section_id`` is a key of
  :data:`study_calc.domains.SECTIONS`.
- :class:`Tool` — a standalone tool panel (the converter, the CAS tab, vectors).
- :class:`Problems` — the practice-problems surface for a subject.
- :class:`Placeholder` — a "coming soon" notice (its ``message_key`` is an i18n key),
  used to show a subject whose content is not built yet (Chemistry).

A subject with a single item renders that panel directly; a subject with several
renders an inner notebook. Keeping the spec declarative means a new subject or a
reordering is a one-line edit here, with no widget code to touch.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """A physics formula section; ``section_id`` indexes ``domains.SECTIONS``."""

    section_id: str


@dataclass(frozen=True)
class Tool:
    """A standalone tool panel, identified by ``name`` (e.g. ``"cas"``)."""

    name: str


@dataclass(frozen=True)
class Problems:
    """The practice-problems surface for ``subject_id`` (e.g. ``"physics"``)."""

    subject_id: str


@dataclass(frozen=True)
class Placeholder:
    """A "coming soon" notice; ``message_key`` is the i18n key for its text."""

    message_key: str


# Tool names the GUI knows how to build. Kept here (not in the GUI) so the spec is
# self-validating in tests without importing Tk.
TOOL_NAMES: frozenset[str] = frozenset({"converter", "cas", "vectors", "periodic_table"})

# Subject id -> ordered items. The id is also the ``subject.<id>`` i18n key, and the
# order is the tab order in the window.
SUBJECTS: tuple[tuple[str, tuple[object, ...]], ...] = (
    ("physics", (
        Section("mechanics"),
        Section("thermodynamics"),
        Section("electromagnetism"),
        Section("waves"),
        Problems("physics"),
    )),
    ("math", (
        Tool("cas"),
        Tool("vectors"),
        Problems("math"),
    )),
    ("tools", (
        Tool("converter"),
    )),
    ("chemistry", (
        Section("chem_solutions"),
        Section("chem_acid_base"),
        Tool("periodic_table"),
        Problems("chemistry"),
    )),
)

__all__ = ["Section", "Tool", "Problems", "Placeholder", "TOOL_NAMES", "SUBJECTS"]
