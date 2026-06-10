"""Formula sets grouped by section.

Each section module exports a list of :class:`~study_calc.core.formula.Formula`.
:data:`SECTIONS` maps a stable section id (also the ``section.<id>`` i18n key)
to its formulas, in display order. Most sections are Physics; the Chemistry ones
(see :data:`CHEMISTRY_SECTIONS`) reuse the same model but are taught from a
different source set (OpenStax Chemistry 2e).
"""

from study_calc.domains import (
    chemistry,
    electromagnetism,
    mechanics,
    thermodynamics,
    waves,
)

# Order matters: this is the order of the tabs in the GUI.
SECTIONS = {
    "mechanics": mechanics.FORMULAS,
    "thermodynamics": thermodynamics.FORMULAS,
    "electromagnetism": electromagnetism.FORMULAS,
    "waves": waves.FORMULAS,
    **chemistry.SECTIONS,
}

# Section ids whose formulas are Chemistry — used by the reference registry and
# its tests to apply the right (non-physics) source expectations.
CHEMISTRY_SECTIONS = frozenset(chemistry.SECTIONS)

__all__ = ["SECTIONS", "CHEMISTRY_SECTIONS"]
