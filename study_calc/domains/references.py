"""Where each formula is taught: links to external study material.

This is the only place that holds the URLs of learning resources, keyed by a
formula's stable ``key``. Keeping it separate from the formula definitions leaves
those declarations clean and makes it a single, obvious spot to extend when a new
formula (or, later, a Math topic) needs references.

Two sources are mapped per formula:

- **OpenStax — College Physics 2e**: the textbook section that introduces the
  equation (https://openstax.org/books/college-physics-2e). Linked at section
  level, on the current 2nd edition the CollegePhysicsAnswers videos follow.
- **CollegePhysicsAnswers**: worked, video-explained solutions for the matching
  chapter (https://collegephysicsanswers.com).

All slugs below were checked to resolve (HTTP 200) at the time of writing.
"""

from __future__ import annotations

from study_calc.core.explain import Explanation, Reference

_OPENSTAX = "https://openstax.org/books/college-physics-2e/pages/{}"
_CPANSWERS = "https://collegephysicsanswers.com/{}"
_OPENSTAX_CHEM = "https://openstax.org/books/chemistry-2e/pages/{}"

# Chemistry formula key -> OpenStax Chemistry 2e section slug. Chemistry is not
# covered by College Physics / CollegePhysicsAnswers, so these carry a single
# OpenStax reference rather than the physics OpenStax+videos pair.
_CHEM_SOURCES: dict[str, str] = {
    "molarity": "3-3-molarity",
    "dilution": "3-3-molarity",
    "moles": "3-1-formula-mass-and-the-mole-concept",
    "ph": "14-2-ph-and-poh",
}

# formula key -> (OpenStax section slug, CollegePhysicsAnswers chapter slug)
_SOURCES: dict[str, tuple[str, str]] = {
    # Mechanics
    "newton_2": ("4-3-newtons-second-law-of-motion-concept-of-a-system",
                 "chapter-4-dynamics-force-and-newtons-laws-motion"),
    "velocity": ("2-5-motion-equations-for-constant-acceleration-in-one-dimension",
                 "chapter-2-kinematics"),
    "momentum": ("8-1-linear-momentum-and-force",
                 "chapter-8-linear-momentum-and-collisions"),
    "kinetic_energy": ("7-2-kinetic-energy-and-the-work-energy-theorem",
                       "chapter-7-work-energy-and-energy-resources"),
    "potential_energy": ("7-3-gravitational-potential-energy",
                         "chapter-7-work-energy-and-energy-resources"),
    "work": ("7-1-work-the-scientific-definition",
             "chapter-7-work-energy-and-energy-resources"),
    "power": ("7-7-power",
              "chapter-7-work-energy-and-energy-resources"),
    # Thermodynamics
    "heat": ("14-2-temperature-change-and-heat-capacity",
             "chapter-14-heat-and-heat-transfer-methods"),
    "ideal_gas": ("13-3-the-ideal-gas-law",
                  "chapter-13-temperature-kinetic-theory-and-gas-laws"),
    "carnot_efficiency": (
        "15-3-introduction-to-the-second-law-of-thermodynamics-heat-engines-and-their-efficiency",
        "chapter-15-thermodynamics"),
    "linear_expansion": ("13-2-thermal-expansion-of-solids-and-liquids",
                         "chapter-13-temperature-kinetic-theory-and-gas-laws"),
    # Electromagnetism
    "ohm": ("20-2-ohms-law-resistance-and-simple-circuits",
            "chapter-20-electric-current-resistance-and-ohms-law"),
    "electric_power": ("20-4-electric-power-and-energy",
                       "chapter-20-electric-current-resistance-and-ohms-law"),
    "coulomb": ("18-3-coulombs-law",
                "chapter-18-electric-charge-and-electric-field"),
    "capacitor_charge": ("19-5-capacitors-and-dielectrics",
                         "chapter-19-electric-potential-and-electric-field"),
    "capacitor_energy": ("19-7-energy-stored-in-capacitors",
                         "chapter-19-electric-potential-and-electric-field"),
    "resistance_series": ("20-3-resistance-and-resistivity",
                          "chapter-20-electric-current-resistance-and-ohms-law"),
    # Waves & optics
    "wave_speed": ("16-9-waves",
                   "chapter-16-oscillatory-motion-and-waves"),
    "period_frequency": ("16-2-period-and-frequency-in-oscillations",
                         "chapter-16-oscillatory-motion-and-waves"),
    "photon_energy": ("29-3-photon-energies-and-the-electromagnetic-spectrum",
                      "chapter-29-introduction-quantum-physics"),
    "wavelength_light": ("24-3-the-electromagnetic-spectrum",
                         "chapter-24-electromagnetic-waves"),
    "snell": ("25-3-the-law-of-refraction",
              "chapter-25-geometric-optics"),
}


def references_for(formula_key: str) -> tuple[Reference, ...]:
    """External study links for ``formula_key`` (empty if none are mapped)."""
    chem_slug = _CHEM_SOURCES.get(formula_key)
    if chem_slug is not None:
        return (Reference("ref.openstax", _OPENSTAX_CHEM.format(chem_slug)),)
    source = _SOURCES.get(formula_key)
    if source is None:
        return ()
    openstax_slug, cpanswers_slug = source
    return (
        Reference("ref.openstax", _OPENSTAX.format(openstax_slug)),
        Reference("ref.cpanswers", _CPANSWERS.format(cpanswers_slug)),
    )


def explanation_for(formula_key: str) -> Explanation:
    """Assemble the full :class:`Explanation` for a formula.

    Theory text lives at the conventional ``theory.<key>`` i18n key; the solving
    steps use the shared default procedure; references come from :func:`references_for`.
    """
    return Explanation(
        theory_key=f"theory.{formula_key}",
        references=references_for(formula_key),
    )
