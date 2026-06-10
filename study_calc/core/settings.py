"""Tiny persisted user settings — introduced for the update policy (#74).

The app has had no user-writable state until now; the update-check feature needs
exactly one durable choice — *auto-check on startup?* — that must survive a
restart. This is a deliberately minimal JSON store in the platform's
config directory, with an injectable path so it is unit-tested headlessly.

It is **fail-soft by design**: a missing, unreadable or corrupt file falls back
to the defaults, and a write that fails (read-only home, etc.) is swallowed — a
settings problem must never crash a calculator. Only keys present in
:data:`DEFAULTS` are honoured, so an unknown or malformed value can't poison the
running config.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_APP_DIR = "study-calc"

#: Every persisted key with its default. Settings outside this set are ignored.
DEFAULTS: dict[str, object] = {
    # Check GitHub Releases for a newer version on startup (non-blocking, silent
    # on failure). The user can turn this off; the manual "Check for updates"
    # action always works regardless.
    "auto_update_check": True,
}


def config_dir() -> Path:
    """The per-user config directory for this app, per OS convention.

    Windows ``%APPDATA%``, macOS ``~/Library/Application Support``, otherwise
    ``$XDG_CONFIG_HOME`` (or ``~/.config``) — each with a ``study-calc`` subdir.
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / _APP_DIR


class Settings:
    """Load/save a small JSON settings file, falling back to :data:`DEFAULTS`."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path is not None else config_dir() / "settings.json"
        self._data: dict[str, object] = dict(DEFAULTS)
        self.load()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        """Read the file if present; keep defaults for anything missing/invalid."""
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw:
                    self._data[key] = raw[key]

    def save(self) -> None:
        """Persist the current values; swallow any write failure (fail-soft)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8"
            )
        except OSError:
            pass

    @property
    def auto_update_check(self) -> bool:
        return bool(self._data["auto_update_check"])

    def set_auto_update_check(self, enabled: bool) -> None:
        self._data["auto_update_check"] = bool(enabled)
        self.save()
