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

import json
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable

from . import screens
from .. import navigation
from ..core import installer
from ..core import updates as updates_core
from ..core.settings import Settings
from ..i18n import i18n, t
from ..resources import app_version


def subject_tagline_key(subject_id: str) -> str:
    """The i18n key for a subject's header subtitle/tagline."""
    return f"subject.{subject_id}.tagline"


def item_courses(item: object, language: str = "en") -> frozenset[str]:
    """The set of Ontario course codes carried by everything under a nav *item*.

    For a :class:`~study_calc.navigation.Section` it is the union of the
    ``courses`` on each formula's topic; for
    :class:`~study_calc.navigation.Problems` the union across that subject's
    practice problems. Tools and placeholders carry no curriculum tag and return
    an empty set (they are never hidden by the filter).

    This lives in the bridge rather than ``navigation`` so that module stays
    stdlib-only and content-layer-free (enforced by ``tests/test_navigation``);
    the bridge is already the layer that joins navigation with the content store.
    The content layer is imported lazily; any failure yields an empty set so an
    item reads as untagged (universally visible) — fail-soft.
    """
    try:
        if isinstance(item, navigation.Section):
            from ..core.learning import load_topic
            from ..domains import SECTIONS

            codes: set[str] = set()
            for formula in SECTIONS.get(item.section_id, ()):
                topic = load_topic(formula.key, language)
                if topic is not None:
                    codes.update(topic.courses)
            return frozenset(codes)
        if isinstance(item, navigation.Problems):
            from ..core.learning import problems_for_subject

            codes = set()
            for problem in problems_for_subject(item.subject_id, language):
                codes.update(problem.courses)
            return frozenset(codes)
    except Exception:  # pragma: no cover - defensive; content layer is normally fine
        return frozenset()
    return frozenset()


def item_visible(item: object, active_course: str, language: str = "en") -> bool:
    """Whether a nav *item* survives the active-course filter.

    ``active_course == "all"`` shows everything. Otherwise:

    - A :class:`~study_calc.navigation.Tool` or
      :class:`~study_calc.navigation.Placeholder` is always shown.
    - A :class:`~study_calc.navigation.Problems` item is **always shown** — the
      filter narrows the *list inside* the surface, not the tab itself (ADR 0003
      §1). Forward-compatible: this unconditional ``return True`` remains correct
      when #175 widens ``active_course`` to a ``frozenset[str]``.
    - An **untagged** ``Section`` (no courses) is always shown (universal content).
    - A tagged ``Section`` is shown only when the active course is among its codes.
    """
    if active_course == "all":
        return True
    if isinstance(item, (navigation.Tool, navigation.Placeholder)):
        return True
    # ADR 0003 §1: a Problems item is a content collection — it stays reachable
    # so the student can see the filtered-empty state ("no problems for this
    # course").  Drop-on-mismatch is correct only for Section/calculator items.
    if isinstance(item, navigation.Problems):
        return True
    courses = item_courses(item, language)
    if not courses:
        return True
    return active_course in courses


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


def navigation_model(active_course: str = "all", language: str = "en") -> list[dict]:
    """The localized subject/item tree, in :data:`navigation.SUBJECTS` order.

    When *active_course* is a specific code (not ``"all"``), items whose
    curriculum tags don't include it are dropped (tools, placeholders and
    untagged items always survive — see :func:`navigation.item_visible`). A
    subject left with no visible items is omitted entirely.
    """
    model: list[dict] = []
    for sid, items in navigation.SUBJECTS:
        visible = tuple(it for it in items if item_visible(it, active_course, language))
        if visible:
            model.append(_subject_model(sid, visible))
    return model


class Bridge:
    """PyWebView ``js_api``: the shell's localized state, regenerated on demand.

    The constructor takes optional injectables so the update feature (#74/#75)
    stays headlessly testable: ``version`` (defaults to the single-sourced
    :func:`study_calc.resources.app_version`), a :class:`~study_calc.core.settings.Settings`
    store, an ``update_fetcher`` callable the check uses instead of hitting the
    network, and ``package_format`` (defaults to
    :func:`study_calc.core.installer.detect_format`) so the per-format apply
    guidance is exercised for every format. Defaults give the real app; tests
    pass fakes.
    """

    def __init__(
        self,
        *,
        version: str | None = None,
        settings: Settings | None = None,
        update_fetcher: updates_core.Fetcher | None = None,
        package_format: str | None = None,
        apply_update_fn: "Callable[[str, str], installer.ApplyResult] | None" = None,
    ) -> None:
        self._version = version or app_version()
        self._settings = settings if settings is not None else Settings()
        self._update_fetcher = update_fetcher
        self._format = package_format or installer.detect_format()
        # The automated self-update apply (#94). Injectable so the localized
        # result model is unit-tested without network/subprocess; the default
        # wires the real GitHub download + checksum verify + installer launch.
        self._apply_update_fn = apply_update_fn or self._default_apply_update

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
            # The persisted curriculum filter (epic #102). The header bar and the
            # Settings overlay both read these; ``filter`` carries the localized
            # labels + the CURRICULUM_GRADES-derived grade→course map (#126).
            "activeGrade": self._settings.active_grade,
            "activeCourse": self._settings.active_course,
            "filter": self._filter_model(),
            "subjects": navigation_model(self._settings.active_course, i18n.language),
        }

    def _filter_model(self) -> dict:
        """The curriculum-filter descriptor for the current persisted selection."""
        return screens.curriculum_filter_model(
            self._settings.active_grade, self._settings.active_course
        )

    def set_language(self, code: str) -> dict:
        """Switch the active language and return the freshly localized state.

        Only the display language changes — the persisted curriculum filter is
        untouched, so the filtered subject tree and selection survive (#126).
        """
        i18n.set_language(code)
        return self.get_state()

    # --- curriculum filter (epic #102, issue #125) ---

    def set_active_grade(self, grade: str | None) -> dict:
        """Set the active grade (resets the course) and return refreshed state.

        ``None`` or ``"all"`` clears the grade. The persisted value is validated
        by :class:`~study_calc.core.settings.Settings`; the refreshed shell model
        already reflects the new (un)filtered subject tree.
        """
        self._settings.set_active_grade("all" if grade is None else str(grade))
        return self.get_state()

    def set_active_course(self, course: str | None) -> dict:
        """Set the active course (within the chosen grade) and return refreshed state.

        ``None`` or ``"all"`` clears the course. An unknown code, or one outside
        the active grade, falls back to ``"all"`` (handled by ``Settings``).
        """
        self._settings.set_active_course("all" if course is None else str(course))
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
        """The practice-problems screen for a subject: every problem + its solution.

        Threads the persisted ``active_course`` through so the returned model
        already reflects the curriculum filter (ADR 0003 §3).
        """
        return screens.problems_screen(subject_id, self._settings.active_course)

    def guide_screen(self) -> dict:
        """The guide overlay model: title, intro, and six localized sections."""
        return screens.guide_screen()

    # --- software updates (#74 check / #75 per-format apply) ---

    def update_screen(self) -> dict:
        """The updates overlay model before any check has run (labels + current version)."""
        return screens.updates_screen(
            None,
            current=self._version,
            auto_check=self._settings.auto_update_check,
            fmt=self._format,
            curriculum=self._filter_model(),
        )

    def check_updates(self) -> dict:
        """Force an update check now; localized up-to-date / available / error model.

        When an update is available the model carries per-format apply guidance
        (#75) built from the detected packaging format.
        """
        result = updates_core.check_updates(self._version, fetcher=self._update_fetcher)
        return screens.updates_screen(
            result,
            current=self._version,
            auto_check=self._settings.auto_update_check,
            fmt=self._format,
            curriculum=self._filter_model(),
        )

    def set_auto_update_check(self, enabled: bool) -> dict:
        """Persist the auto-check preference and echo back the refreshed model."""
        self._settings.set_auto_update_check(bool(enabled))
        return screens.updates_screen(
            None,
            current=self._version,
            auto_check=self._settings.auto_update_check,
            fmt=self._format,
            curriculum=self._filter_model(),
        )

    def apply_update(self, version: str) -> dict:
        """Automatically install the update for a self-updating format (#94).

        Only Windows and AppImage self-apply; other formats keep the v1 guidance.
        Returns a localized result model (success or a failure that points the
        user at the manual download link). Never raises.
        """
        result = self._apply_update_fn(self._format, str(version))
        return screens.apply_result_model(result)

    def _default_apply_update(self, fmt: str, version: str) -> installer.ApplyResult:
        """Real apply seams: GitHub download + SHA256SUMS verify + launch.

        Impure (network + subprocess); not unit-tested — exercised by per-OS VM
        acceptance. The pure orchestration in :func:`installer.apply_update` does
        the verify-before-run gating with these as injected callables.
        """
        if not installer.supports_auto_apply(fmt):
            return installer.ApplyResult("unsupported", "updates.apply.error.unsupported")
        import tempfile

        dest_dir = tempfile.mkdtemp(prefix="study-calc-update-")
        return installer.apply_update(
            fmt,
            version,
            download=lambda name: _download_release_asset(name, dest_dir),
            checksums=_fetch_release_checksums(),
            run=lambda path: _run_artifact(fmt, path),
        )


# --- real apply seams (impure; VM-exercised, not unit-tested) -------------
# Network download from the latest GitHub Release + checksum fetch + the
# per-format launch. Kept out of core.installer so that module stays pure; the
# pure orchestration there gates run() on a verified SHA-256 (#94).

_UA = {"User-Agent": "study-calc-self-update", "Accept": "application/vnd.github+json"}


def _latest_release_json() -> dict:
    request = urllib.request.Request(updates_core.LATEST_RELEASE_API, headers=_UA)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _asset_url(release: dict, name: str) -> str | None:
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset.get("browser_download_url")
    return None


def _download_release_asset(name: str, dest_dir: str) -> Path:
    """Download release asset ``name`` into ``dest_dir`` and return its path."""
    url = _asset_url(_latest_release_json(), name)
    if not url:
        raise RuntimeError(f"asset {name!r} not found in the latest release")
    dest = Path(dest_dir) / name
    request = urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]})
    with urllib.request.urlopen(request, timeout=120) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)
    return dest


def _fetch_release_checksums() -> dict:
    """The latest release's ``SHA256SUMS`` parsed to ``{name: hex}`` (empty on failure)."""
    try:
        url = _asset_url(_latest_release_json(), "SHA256SUMS")
        if not url:
            return {}
        request = urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]})
        with urllib.request.urlopen(request, timeout=30) as response:
            return installer.parse_sha256sums(response.read().decode("utf-8"))
    except Exception:
        return {}


def _run_artifact(fmt: str, path: Path) -> None:
    """Launch the verified artifact: installer (Windows) / in-place swap (AppImage)."""
    if fmt == "windows":
        # Run the per-user installer to upgrade in place, then quit so it can
        # replace files; the Inno installer relaunches the app afterwards.
        subprocess.Popen([str(path), "/SILENT"], close_fds=True)
        sys.exit(0)
    if fmt == "appimage":
        target = os.environ.get("APPIMAGE")
        if not target:
            raise RuntimeError("APPIMAGE is not set; not running inside an AppImage")
        # Make the freshly-downloaded image owner-executable only; never widen
        # group/other write or open it up world-writable (the file lives in a
        # private mkdtemp dir). Add the owner-execute bit to its current mode.
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        shutil.move(str(path), target)  # swap the running image (cross-device safe)
        os.execv(target, [target, *sys.argv[1:]])  # relaunch on the new version
    raise RuntimeError(f"no automated apply for format {fmt!r}")
