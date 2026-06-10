"""Tests for the bundled-asset locator and version resolver.

``study_calc.resources`` underpins frozen packaging (#62, epic #60): every engine
loads its data through :func:`resource_path`, and the window title shows
:func:`app_version`. These run headlessly against the source checkout (the frozen
``sys._MEIPASS`` branch is exercised by ``packaging/smoke_test.py`` on a real
bundle).
"""

import re
from pathlib import Path

from study_calc import __version__
from study_calc.resources import app_version, package_root, resource_path

# The non-code assets a frozen bundle must carry (mirrors packaging/smoke_test.py
# and the PyInstaller spec's datas).
_REQUIRED_ASSETS = [
    ("data", "elements.json"),
    ("data", "knowledgebase.db"),
    ("web", "frontend", "index.html"),
    ("web", "tokens.json"),
    ("locales", "en.json"),
]


def test_package_root_is_the_study_calc_dir_in_source():
    root = package_root()
    assert root.name == "study_calc"
    assert (root / "__init__.py").is_file()


def test_required_assets_resolve_to_real_files():
    for parts in _REQUIRED_ASSETS:
        path = resource_path(*parts)
        assert path.is_file(), f"{'/'.join(parts)} did not resolve ({path})"


def test_resource_path_is_under_the_package_root():
    assert resource_path("data") == package_root() / "data"


def _pyproject_version() -> str:
    text = (package_root().parent / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', text)
    assert match, "could not find project.version in pyproject.toml"
    return match.group(1)


def test_app_version_matches_pyproject():
    assert app_version() == _pyproject_version()


def test_dunder_version_is_single_sourced():
    assert __version__ == app_version()
