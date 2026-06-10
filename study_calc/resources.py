"""Locate the package's bundled data and resolve the app version.

study-calc ships non-code assets — locale catalogs, the learning knowledgebase,
``elements.json``, the PyWebView frontend and the design tokens — that must be
found both when running from a source checkout *and* from a frozen one-folder
PyInstaller bundle (the packaging epic, #60). The two layouts differ:

* **source** — the assets sit inside the ``study_calc`` package directory next
  to this module, e.g. ``study_calc/locales/``.
* **frozen** — PyInstaller extracts the bundled ``datas`` under ``sys._MEIPASS``
  while the Python modules may live in a zipped archive whose ``__file__`` is not
  a real filesystem path. So every loader must resolve assets through
  ``sys._MEIPASS`` rather than ``Path(__file__)``.

:func:`resource_path` hides that difference: callers ask for a path *relative to
the package root* (``resource_path("data", "elements.json")``) and get a real
filesystem path in either mode. The PyInstaller spec (``packaging/study-calc.spec``)
bundles each asset tree under the same ``study_calc/<...>`` prefix, so the
mapping stays one-to-one.

:func:`app_version` resolves the single-sourced version (``pyproject.toml``'s
``project.version``): from installed/​bundled distribution metadata when present,
falling back to parsing ``pyproject.toml`` in a source checkout.
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path

_PACKAGE = "study_calc"


@lru_cache(maxsize=1)
def package_root() -> Path:
    """Return the directory that holds the package's bundled data.

    In a frozen PyInstaller bundle this is ``<_MEIPASS>/study_calc``; from a
    source checkout it is the ``study_calc`` package directory next to this file.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        base = Path(meipass) if meipass else Path(sys.executable).resolve().parent
        return base / _PACKAGE
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """Resolve a bundled asset path relative to the package root.

    ``resource_path("data", "elements.json")`` -> the real filesystem path to
    that asset, valid both from source and inside a frozen bundle.
    """
    return package_root().joinpath(*parts)


def _version_from_pyproject() -> str | None:
    """Parse ``project.version`` from the source-checkout ``pyproject.toml``.

    Returns ``None`` when the file is absent (e.g. inside a frozen bundle, where
    distribution metadata is used instead).
    """
    pyproject = package_root().parent / "pyproject.toml"
    if not pyproject.is_file():
        return None
    text = pyproject.read_text(encoding="utf-8")
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:
        tomllib = None
    if tomllib is not None:
        data = tomllib.loads(text)
        version = data.get("project", {}).get("version")
        if isinstance(version, str):
            return version
    # Python 3.10 has no tomllib; fall back to a narrow regex on the [project]
    # version line. The manifest is hand-written and simple, so this is safe.
    match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else None


@lru_cache(maxsize=1)
def app_version() -> str:
    """Return the single-sourced application version (``pyproject.toml``).

    Resolution order: installed/​bundled distribution metadata (works in a frozen
    bundle when the spec collects it), then the source ``pyproject.toml``. Falls
    back to ``"0.0.0"`` if neither is available, so the UI never crashes on it.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("study-calc")
        except PackageNotFoundError:
            pass
    except Exception:  # pragma: no cover - importlib.metadata is always present
        pass
    return _version_from_pyproject() or "0.0.0"
