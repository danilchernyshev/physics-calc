"""Physics Calculator — mechanics, thermodynamics, electromagnetism and waves.

The package has three layers:

* :mod:`physics_calc.core`    — the formula model with a solver for any variable,
  and the unit converter;
* :mod:`physics_calc.domains` — ready-made formula sets grouped by physics section;
* :mod:`physics_calc.gui`     — the Tkinter desktop interface.

User-facing text is localized via :mod:`physics_calc.i18n` (English, Spanish,
French, Russian, Ukrainian), switchable at runtime.
"""

__version__ = "0.3.0"
