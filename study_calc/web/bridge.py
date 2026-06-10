"""The JS<->Python bridge for the redesign frontend (ADR 0001).

This is the ``js_api`` object PyWebView exposes to the web UI: the frontend calls
``window.pywebview.api.get_state()`` / ``set_language(code)`` and gets back a
fully localized navigation model. It is **pure Python with no PyWebView import**,
so it loads and is unit-tested headlessly (mirroring how ``navigation.py`` stays
Tk-free). The actual window lives in :mod:`study_calc.web.app`.

The model is generated entirely from :data:`study_calc.navigation.SUBJECTS` — the
single source of truth — so adding or reordering a subject stays a one-line edit
there, with nothing to change here or in the frontend. Display strings are
resolved through :mod:`study_calc.i18n` (keys, never hardcoded prose), exactly as
the Tkinter shell does.
"""

from __future__ import annotations

from . import screens
from .. import navigation
from ..core import updates as updates_core
from ..core.settings import Settings
from ..i18n import i18n, t
from ..resources import app_version


def subject_tagline_key(subject_id: str) -> str:
    """The i18n key for a subject's header subtitle/tagline."""
    return f"subject.{subject_id}.tagline"


def _item_model(item: object) -> dict:
    return {
        "id": navigation.item_id(item),
        "kind": navigation.item_kind(item),
        "label": t(navigation.item_label_key(item)),
    }


def _subject_model(subject_id: str, items: tuple) -> dict:
    label = t(f"subject.{subject_id}")
    return {
        "id": subject_id,
        "label": label,
        "monogram": label[:1].upper(),
        "tagline": t(subject_tagline_key(subject_id)),
        "items": [_item_model(it) for it in items],
    }


def navigation_model() -> list[dict]:
    """The localized subject/item tree, in :data:`navigation.SUBJECTS` order."""
    return [_subject_model(sid, items) for sid, items in navigation.SUBJECTS]


class Bridge:
    """PyWebView ``js_api``: the shell's localized state, regenerated on demand.

    The constructor takes optional injectables so the update feature (#74) stays
    headlessly testable: ``version`` (defaults to the single-sourced
    :func:`study_calc.resources.app_version`), a :class:`~study_calc.core.settings.Settings`
    store, and an ``update_fetcher`` callable the check uses instead of hitting
    the network. Defaults give the real app; tests pass fakes.
    """

    def __init__(
        self,
        *,
        version: str | None = None,
        settings: Settings | None = None,
        update_fetcher: updates_core.Fetcher | None = None,
    ) -> None:
        self._version = version or app_version()
        self._settings = settings if settings is not None else Settings()
        self._update_fetcher = update_fetcher

    def get_state(self) -> dict:
        """The full shell model: language, the language list, chrome labels, subjects."""
        return {
            "lang": i18n.language,
            "version": self._version,
            # The frontend runs a non-blocking startup check only when this is on.
            "autoUpdateCheck": self._settings.auto_update_check,
            "languages": [
                {"code": code, "label": native}
                for code, native in i18n.available_languages()
            ],
            "labels": {
                "appTitle": t("app.title"),
                "subjectsHeading": t("nav.subjects"),
                "howToUse": t("menu.guide"),
                "updates": t("menu.updates"),
                "language": t("menu.language"),
                "placeholder": t("shell.placeholder"),
            },
            "subjects": navigation_model(),
        }

    def set_language(self, code: str) -> dict:
        """Switch the active language and return the freshly localized state."""
        i18n.set_language(code)
        return self.get_state()

    # --- per-screen content (issue #6 onward) ---

    def formula_screen(self, section_id: str) -> dict:
        """The physics formula screen for a ``section`` item: labels + formulas."""
        return screens.formula_screen(section_id)

    def solve_formula(self, formula_key: str, values: dict) -> dict:
        """Solve a formula from the input fields; localized result or error."""
        return screens.solve_formula(formula_key, values)

    def cas_screen(self) -> dict:
        """The symbolic-math screen: operations + labels, or a SymPy-absent notice."""
        return screens.cas_screen()

    def cas_run(self, op: str, values: dict | None = None) -> dict:
        """Run a CAS operation; localized step-by-step (green answers) or error."""
        return screens.cas_run(op, values)

    def vector_screen(self) -> dict:
        """The vectors screen: operations + labels."""
        return screens.vector_screen()

    def vector_run(self, op: str, values: dict | None = None) -> dict:
        """Run a vector operation; localized step-by-step (green answers) or error."""
        return screens.vector_run(op, values)

    def converter_screen(self) -> dict:
        """The unit-converter screen: all categories with their unit lists."""
        return screens.converter_screen()

    def convert_run(self, category: str, value: str, from_unit: str, to_unit: str) -> dict:
        """Convert a value between units; localized result string or error."""
        return screens.convert_run(category, value, from_unit, to_unit)

    def periodic_screen(self) -> dict:
        """The periodic-table screen: all 118 elements pre-baked for the CSS grid."""
        return screens.periodic_screen()

    def molar_mass_run(self, formula: str) -> dict:
        """Compute the molar mass of a chemical formula; localized result or error."""
        return screens.molar_mass_run(formula)

    def balance_run(self, equation: str) -> dict:
        """Balance a chemical equation; localized result or error."""
        return screens.balance_run(equation)

    def problems_screen(self, subject_id: str) -> dict:
        """The practice-problems screen for a subject: every problem + its solution."""
        return screens.problems_screen(subject_id)

    def guide_screen(self) -> dict:
        """The guide overlay model: title, intro, and six localized sections."""
        return screens.guide_screen()

    # --- software updates (#74) ---

    def update_screen(self) -> dict:
        """The updates overlay model before any check has run (labels + current version)."""
        return screens.updates_screen(
            None, current=self._version, auto_check=self._settings.auto_update_check
        )

    def check_updates(self) -> dict:
        """Force an update check now; localized up-to-date / available / error model."""
        result = updates_core.check_updates(self._version, fetcher=self._update_fetcher)
        return screens.updates_screen(
            result, current=self._version, auto_check=self._settings.auto_update_check
        )

    def set_auto_update_check(self, enabled: bool) -> dict:
        """Persist the auto-check preference and echo back the refreshed model."""
        self._settings.set_auto_update_check(bool(enabled))
        return screens.updates_screen(
            None, current=self._version, auto_check=self._settings.auto_update_check
        )
