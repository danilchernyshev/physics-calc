"""Study Calculator — physics, symbolic math, graphing, vectors and learning materials.

The package has three layers:

* :mod:`study_calc.core`    — the formula model with a solver for any variable,
  the unit converter, the SymPy-backed CAS (with MHF4U Advanced Functions tools
  and graphing), the MCV4U vector algebra, and the chemistry engine (periodic
  table, molar mass, equation balancing);
* :mod:`study_calc.domains` — ready-made formula sets grouped by physics and
  chemistry section;
* :mod:`study_calc.web`     — the PyWebView desktop interface.

User-facing text is localized via :mod:`study_calc.i18n` (English, Spanish,
French, Russian, Ukrainian), switchable at runtime.
"""

__version__ = "0.6.0"
