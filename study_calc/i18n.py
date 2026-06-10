"""Lightweight, runtime-switchable localization backed by JSON catalogs.

Each language is a flat ``{message_key: text}`` JSON file under ``locales/``.
The :data:`i18n` singleton resolves a key for the active language and falls
back to the default language (then to the key itself) when a translation is
missing, so a partially translated catalog never crashes the UI.

The domain layer stores *keys* (e.g. ``"var.force"``), never display strings;
rendering and language choice live here and in the GUI. That separation keeps
:mod:`study_calc.core` and :mod:`study_calc.domains` free of UI concerns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

_LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LANGUAGE = "en"


class _Translatable(Protocol):
    """Anything with a symbol and message keys — e.g. a domain ``Variable``."""

    symbol: str
    name_key: str
    unit_key: str


class I18n:
    """Holds the loaded catalogs and the currently selected language."""

    def __init__(self, locales_dir: Path = _LOCALES_DIR, default: str = DEFAULT_LANGUAGE) -> None:
        self._dir = Path(locales_dir)
        self._default = default
        self._catalogs: dict[str, dict[str, str]] = {}
        self._language = default
        self._load()
        if default not in self._catalogs:
            raise FileNotFoundError(f"Default locale '{default}' not found in {self._dir}")

    def _load(self) -> None:
        for path in sorted(self._dir.glob("*.json")):
            self._catalogs[path.stem] = json.loads(path.read_text(encoding="utf-8"))

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, code: str) -> None:
        if code not in self._catalogs:
            raise ValueError(f"Unknown language: {code}")
        self._language = code

    def available_languages(self) -> list[tuple[str, str]]:
        """Return ``(code, native_name)`` pairs, ordered by language code."""
        return [
            (code, self._catalogs[code].get("language.native", code))
            for code in sorted(self._catalogs)
        ]

    def t(self, key: str, /, **params: object) -> str:
        """Translate ``key`` for the active language, formatting any ``params``."""
        text = self._catalogs.get(self._language, {}).get(key)
        if text is None:  # fall back to the default language, then the key itself
            text = self._catalogs.get(self._default, {}).get(key, key)
        if params:
            try:
                return text.format(**params)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    def variable_label(self, var: _Translatable) -> str:
        """Render a domain variable as ``Name (symbol, unit)`` in the active language."""
        name = self.t(var.name_key)
        if var.unit_key:
            return f"{name} ({var.symbol}, {self.t(var.unit_key)})"
        return f"{name} ({var.symbol})"


# Module-level singleton used across the GUI.
i18n = I18n()


def t(key: str, /, **params: object) -> str:
    """Shortcut for :meth:`I18n.t` on the shared singleton."""
    return i18n.t(key, **params)
