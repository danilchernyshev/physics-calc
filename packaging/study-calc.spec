# PyInstaller spec for study-calc — the shared packaging foundation (#62, epic #60).
#
# Builds a **one-folder** bundle (not one-file): one-file re-extracts to a temp
# dir on every launch — slow, and a frequent antivirus false-positive trigger —
# whereas one-folder launches instantly and is what the platform installers
# (#63 Windows / #66 AppImage) wrap. Build it with::
#
#     pyinstaller packaging/study-calc.spec --noconfirm
#
# The result is ``dist/study-calc/`` with the launcher executable plus an
# ``_internal/`` tree carrying Python and every bundled asset. ``packaging/
# smoke_test.py`` validates that tree headlessly.
#
# Asset bundling: the engines load non-code data through
# ``study_calc.resources.resource_path``, which resolves to ``<_MEIPASS>/study_calc/<...>``
# in a frozen bundle. So every ``datas`` entry below maps a source asset tree to
# the matching ``study_calc/<...>`` destination prefix, keeping the layout
# identical to a source checkout.

from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

# The spec file's directory is ``packaging/``; the project root is its parent.
_ROOT = Path(SPECPATH).resolve().parent
_PKG = _ROOT / "study_calc"


def _asset(rel_dir: str):
    """Map ``study_calc/<rel_dir>`` to the same destination prefix in the bundle."""
    return (str(_PKG / rel_dir), f"study_calc/{rel_dir}")


# Every non-code asset the frozen app reads at runtime (see the epic #60 list and
# study_calc.resources). Directories are bundled whole; the data file is explicit.
datas = [
    _asset("locales"),
    _asset("web/frontend"),
    (str(_PKG / "web" / "tokens.json"), "study_calc/web"),
    (str(_PKG / "data" / "elements.json"), "study_calc/data"),
    (str(_PKG / "data" / "knowledgebase.db"), "study_calc/data"),
]
# Collect the installed distribution metadata so importlib.metadata.version(
# "study-calc") — and thus study_calc.resources.app_version() — works inside the
# frozen bundle, surfacing the version in the window title.
datas += copy_metadata("study-calc")

a = Analysis(
    [str(_PKG / "__main__.py")],
    pathex=[str(_ROOT)],
    binaries=[],
    datas=datas,
    # SymPy and PyWebView pull modules dynamically; let PyInstaller's hooks find
    # them and add the few it may miss.
    hiddenimports=["sympy"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="study-calc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # --noconsole: a GUI app must not pop a terminal window on Windows/macOS.
    console=False,
    icon=str(_PKG / "web" / "frontend" / "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="study-calc",
)
