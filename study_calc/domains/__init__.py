"""Formula sets grouped by physics section.

Each section module exports a list of :class:`~study_calc.core.formula.Formula`.
:data:`SECTIONS` maps a stable section id (also the ``section.<id>`` i18n key)
to its formulas, in display order.
"""

from study_calc.domains import mechanics, thermodynamics, electromagnetism, waves

# Order matters: this is the order of the tabs in the GUI.
SECTIONS = {
    "mechanics": mechanics.FORMULAS,
    "thermodynamics": thermodynamics.FORMULAS,
    "electromagnetism": electromagnetism.FORMULAS,
    "waves": waves.FORMULAS,
}

__all__ = ["SECTIONS"]
