"""Наборы формул, сгруппированные по разделам физики.

Каждый модуль раздела экспортирует список :class:`~physics_calc.core.formula.Formula`.
:data:`SECTIONS` собирает их вместе в порядке отображения в интерфейсе.
"""

from physics_calc.domains import mechanics, thermodynamics, electromagnetism, waves

# Порядок важен: именно так разделы появятся во вкладках GUI.
SECTIONS = {
    "Механика": mechanics.FORMULAS,
    "Термодинамика": thermodynamics.FORMULAS,
    "Электромагнетизм": electromagnetism.FORMULAS,
    "Волны и оптика": waves.FORMULAS,
}

__all__ = ["SECTIONS"]
