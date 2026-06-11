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

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

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

# PyWebView's Linux backend reaches WebKit2GTK through PyGObject (gi), which it
# imports *dynamically* (by platform) — invisible to PyInstaller's static
# analysis, so nothing pulls gi in and the bundle crashes with "No module named
# 'gi'" on a clean host (#158). Fix it on Linux only (Windows/macOS use native
# backends, never GTK):
#   * name `gi` AND the gi.repository namespaces the GTK backend imports, so
#     PyInstaller's bundled GObject hooks fire and collect the matching
#     introspection typelibs (Gtk-3.0, WebKit2-4.1, …) plus the girepository
#     glue. Listing only `gi` is NOT enough — the per-namespace hooks (and thus
#     the .typelib files) only run when gi.repository.<Name> is in the graph, so
#     `from gi.repository import Gtk` would still fail at runtime;
#   * collect_all('gi'/'cairo') adds the Python packages and their shared libs.
# The heavy GTK/WebKit .so's stay on the host (see packaging/linux/README.md);
# only the Python + typelib glue is bundled.
binaries = []
hiddenimports = ["sympy"]
if sys.platform.startswith("linux"):
    hiddenimports += [
        "gi",
        "gi.repository.Gtk",
        "gi.repository.Gdk",
        "gi.repository.GLib",
        "gi.repository.Gio",
        "gi.repository.GObject",
        "gi.repository.WebKit2",
    ]
    for _gi_pkg in ("gi", "cairo"):
        try:
            _pkg_datas, _pkg_binaries, _pkg_hidden = collect_all(_gi_pkg)
            datas += _pkg_datas
            binaries += _pkg_binaries
            hiddenimports += _pkg_hidden
        except Exception:
            # A package may be unavailable in the build env; the hiddenimports
            # above still drive the GObject hooks for whatever is installed.
            pass

a = Analysis(
    [str(_PKG / "__main__.py")],
    pathex=[str(_ROOT)],
    binaries=binaries,
    datas=datas,
    # SymPy and PyWebView pull modules dynamically; let PyInstaller's hooks find
    # them and add the few it may miss. The gi/gi.repository entries above are
    # what make PyWebView's GTK backend importable in the frozen bundle on Linux.
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[str(Path(SPECPATH).resolve().parent / "hooks" / "runtime_gi_typelib_path.py")],
    # The graphing surface (matplotlib/numpy/Pillow — the `graph` extra) is not
    # wired into the web UI yet and no shipping code path imports it, so keep it
    # out of the frozen bundle. Excluding here makes the build lean regardless of
    # which extras happen to be installed in the build environment.
    excludes=[
        "matplotlib", "numpy", "PIL", "Pillow", "kiwisolver",
        "scipy", "pandas", "IPython",
        "tkinter", "pytest", "_pytest",
    ],
    noarchive=False,
)

# PyInstaller's GTK/GdkPixbuf hooks vacuum the *build host's* entire icon and
# theme trees (``/usr/share/icons`` + ``/usr/share/themes``) into the bundle —
# well over a gigabyte on a themed desktop. The Linux build is not self-contained
# for graphics (the AppImage relies on the host's GTK/WebKit; see
# packaging/linux/README.md), so these are dead weight. Drop them and other host
# data trees the app never reads, keeping the bundle within the AppImage size
# budget (#66).
_DATA_PREFIX_EXCLUDES = (
    "share/icons",
    "share/themes",
    "share/fonts",
    "share/locale",
    "share/cursors",
    "share/backgrounds",
)
a.datas = [
    entry
    for entry in a.datas
    if not entry[0].replace("\\", "/").startswith(_DATA_PREFIX_EXCLUDES)
]

pyz = PYZ(a.pure)

# EXE icon: Windows accepts only .exe/.ico (and the lean build has no Pillow to
# auto-convert a PNG), so on Windows use the .ico that build_installer.ps1
# generates from icon.png *before* freezing; macOS/Linux accept the PNG. If the
# .ico is somehow absent, fall back to no icon rather than failing the freeze.
if sys.platform == "win32":
    _win_ico = _ROOT / "packaging" / "windows" / "study-calc.ico"
    _exe_icon = str(_win_ico) if _win_ico.exists() else None
else:
    _exe_icon = str(_PKG / "web" / "frontend" / "icon.png")

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
    icon=_exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="study-calc",
)

# On macOS, wrap the one-folder bundle into a proper ``Study Calc.app`` so the
# user drags it to /Applications and launches it from Launchpad (the DMG in
# packaging/macos/build_dmg.sh, #64, packages this). The guard keeps this a
# no-op on Linux/Windows — COLLECT above is what #66/#63 wrap there. PyInstaller
# still emits the plain ``dist/study-calc/`` folder alongside the ``.app``, so
# packaging/smoke_test.py --bundle can validate the engines headlessly. The
# ``.icns`` is generated from icon.png by build_dmg.sh before this runs.
if sys.platform == "darwin":
    from study_calc.resources import app_version  # lightweight, pyproject-backed

    app = BUNDLE(
        coll,
        name="Study Calc.app",
        icon=str(_ROOT / "packaging" / "macos" / "study-calc.icns"),
        bundle_identifier="io.github.danilchernyshev.StudyCalc",
        version=app_version(),
        info_plist={
            "CFBundleName": "Study Calc",
            "CFBundleDisplayName": "Study Calc",
            "CFBundleShortVersionString": app_version(),
            "NSHighResolutionCapable": True,
            # PyWebView's macOS backend (pywebview[cocoa]) targets modern macOS.
            "LSMinimumSystemVersion": "11.0",
        },
    )
