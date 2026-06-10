"""Learning content attached to a computable thing (a formula now, a math topic later).

Deliberately domain- and UI-agnostic, mirroring the rest of :mod:`study_calc.core`:
it stores i18n *keys* and plain URLs, never display prose. The GUI resolves the keys
through :mod:`study_calc.i18n` and renders the references as clickable links.

The same model is meant to back both Physics (each :class:`~study_calc.core.formula.Formula`)
and, later, Math/CAS results — anything that can carry a short theory note, a list of
solving steps, and pointers to external study material.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Reference:
    """A pointer to external learning material.

    :param label_key: i18n key for the link text (e.g. ``"ref.openstax"``).
    :param url: the address opened in the user's browser when the link is clicked.
    """

    label_key: str
    url: str


# The "solve for any variable" procedure is the same for every physics formula in
# this app, so the steps are generic i18n keys shared across formulas. A Math topic
# would supply its own ``steps_keys`` instead.
DEFAULT_SOLVE_STEPS: tuple[str, ...] = (
    "steps.solve.identify",
    "steps.solve.isolate",
    "steps.solve.substitute",
    "steps.solve.compute",
)


@dataclass(frozen=True)
class Explanation:
    """Localizable learning content: a theory note, solving steps, and references.

    :param theory_key: i18n key for the "what this equation means" paragraph.
    :param steps_keys: ordered i18n keys describing how to solve; defaults to the
        generic "solve for any variable" procedure shared by the physics formulas.
    :param references: external study links (textbook section, video solutions).
    """

    theory_key: str
    steps_keys: tuple[str, ...] = DEFAULT_SOLVE_STEPS
    references: tuple[Reference, ...] = field(default_factory=tuple)
