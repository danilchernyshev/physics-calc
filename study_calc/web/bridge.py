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

from .. import navigation
from ..i18n import i18n, t


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
    """PyWebView ``js_api``: the shell's localized state, regenerated on demand."""

    def get_state(self) -> dict:
        """The full shell model: language, the language list, chrome labels, subjects."""
        return {
            "lang": i18n.language,
            "languages": [
                {"code": code, "label": native}
                for code, native in i18n.available_languages()
            ],
            "labels": {
                "appTitle": t("app.title"),
                "subjectsHeading": t("nav.subjects"),
                "howToUse": t("menu.guide"),
                "language": t("menu.language"),
                "placeholder": t("shell.placeholder"),
            },
            "subjects": navigation_model(),
        }

    def set_language(self, code: str) -> dict:
        """Switch the active language and return the freshly localized state."""
        i18n.set_language(code)
        return self.get_state()
