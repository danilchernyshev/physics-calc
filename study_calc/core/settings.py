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

#: Sentinel meaning "no filter" for the curriculum grade/course keys.
ALL = "all"

#: Grade levels still recognised if the curriculum map can't be imported.
_FALLBACK_GRADE_LEVELS = ("11", "12")

#: Every persisted key with its default. Settings outside this set are ignored.
DEFAULTS: dict[str, object] = {
    # Check GitHub Releases for a newer version on startup (non-blocking, silent
    # on failure). The user can turn this off; the manual "Check for updates"
    # action always works regardless.
    "auto_update_check": True,
    # Global curriculum filter (epic #102). The active Ontario grade level
    # ("all" | "11" | "12") and course code ("all" | "SPH4U" | …). A specific
    # course is only valid once a grade is chosen; both default to "all" (show
    # everything) and fall back to "all" on any unknown/stale value.
    "active_grade": ALL,
    "active_course": ALL,
}


def _curriculum_grades() -> dict[str, int]:
    """The course-code → grade-level map, or empty if it can't be imported.

    Imported lazily so this tiny settings store stays decoupled from the
    knowledgebase loader (:mod:`study_calc.core.learning` pulls in the SQLite
    layer). A failure here is swallowed — validation simply falls back to the
    sentinel, never crashing the calculator.
    """
    try:
        from study_calc.core.learning import CURRICULUM_GRADES

        return dict(CURRICULUM_GRADES)
    except Exception:  # pragma: no cover - defensive; import is normally fine
        return {}


def _allowed_grades() -> set[str]:
    """``{"all"}`` plus every distinct grade level in the curriculum map."""
    levels = {str(level) for level in _curriculum_grades().values()}
    return {ALL, *(levels or set(_FALLBACK_GRADE_LEVELS))}


def _allowed_courses() -> set[str]:
    """``{"all"}`` plus every course code in the curriculum map."""
    return {ALL, *_curriculum_grades()}


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
            raw = None
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw:
                    self._data[key] = raw[key]
        # Coerce the curriculum-filter keys into the allowed set, so a stale or
        # hand-edited file (e.g. a course whose grade left CURRICULUM_GRADES)
        # can never feed an invalid value to the UI.
        self._normalize_filter()

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

    # --- curriculum filter (epic #102) ------------------------------------

    @property
    def active_grade(self) -> str:
        """The active grade level: ``"all"``, ``"11"`` or ``"12"``."""
        return str(self._data["active_grade"])

    @property
    def active_course(self) -> str:
        """The active course code: ``"all"`` or a ``CURRICULUM_GRADES`` key."""
        return str(self._data["active_course"])

    def set_active_grade(self, grade: object) -> None:
        """Persist the active grade and reset the course to ``"all"``.

        A course belongs to exactly one grade, so changing the grade always
        invalidates the previously chosen course (design §2c). An unknown grade
        falls back to ``"all"`` (fail-soft).
        """
        value = str(grade)
        self._data["active_grade"] = value if value in _allowed_grades() else ALL
        self._data["active_course"] = ALL
        self.save()

    def set_active_course(self, course: object) -> None:
        """Persist the active course, validated against the active grade.

        A specific course is only honoured when a matching grade is already
        set; an unknown code, or one from a different grade, falls back to
        ``"all"`` (fail-soft).
        """
        value = str(course)
        self._data["active_course"] = value if self._course_ok(value) else ALL
        self.save()

    def _course_ok(self, course: str) -> bool:
        """True if ``course`` is a valid choice under the current grade."""
        if course == ALL:
            return True
        if course not in _allowed_courses():
            return False
        grade = self.active_grade
        if grade == ALL:
            return False  # a specific course needs a chosen grade
        return str(_curriculum_grades().get(course)) == grade

    def _normalize_filter(self) -> None:
        """Coerce the persisted grade/course into the allowed set (fail-soft)."""
        grade = str(self._data["active_grade"])
        self._data["active_grade"] = grade if grade in _allowed_grades() else ALL
        course = str(self._data["active_course"])
        self._data["active_course"] = course if self._course_ok(course) else ALL
