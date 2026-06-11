#!/usr/bin/env bash
# Build the study-calc Linux AppImage (#66, epic #60).
#
# A single-file, double-click fallback for distros without Flatpak. It wraps the
# PyInstaller one-folder bundle (packaging/study-calc.spec, #62) in an AppDir and
# seals it with appimagetool. WebKit2GTK is intentionally NOT bundled — it cannot
# be made relocatable in an AppImage — so the host must have libwebkit2gtk-4.1-0
# (documented in packaging/linux/README.md and on the release page, #68).
#
# Usage:
#   packaging/linux/build_appimage.sh            # build into ./dist
#   OUTPUT_DIR=/tmp packaging/linux/build_appimage.sh
#
# Requirements: a Linux x86_64 host, uv (for the frozen build), and either a
# pre-downloaded appimagetool on PATH or network access to fetch it. Produces
# dist/study-calc-<version>-linux.AppImage.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT}/dist}"
BUILD_DIR="${ROOT}/build"
APPDIR="${BUILD_DIR}/AppDir"
ARCH="${ARCH:-x86_64}"

cd "${ROOT}"

# 1. Resolve the single-sourced version from pyproject.toml.
VERSION="$(uv run --extra packaging python -c \
    'from study_calc.resources import app_version; print(app_version())')"
echo ">> Building study-calc ${VERSION} AppImage (${ARCH})"

# 2. Freeze the one-folder bundle from the shared spec.
#
# PyGObject must be importable *at freeze time* so PyInstaller bundles gi + the
# GObject-Introspection typelibs for PyWebView's GTK backend (#158). This inner
# `uv run` resolves its own environment, so the pin must be named HERE — naming it
# only on an outer `uv run … bash build_appimage.sh` wrapper does NOT propagate
# (that was the v0.8.1 release failure: gi "not a package" at freeze → unlaunchable
# bundle). Pinned <3.52 for girepository-1.0 hosts (ubuntu-22.04); override
# PYGOBJECT_PIN for another host, or set it empty (PYGOBJECT_PIN=) to rely on a
# system-site gi instead of a uv-built one.
echo ">> [1/5] PyInstaller one-folder build"
_pin="${PYGOBJECT_PIN-pygobject<3.52}"
_freeze_with=()
[ -n "${_pin}" ] && _freeze_with=(--with "${_pin}")
uv run --extra packaging "${_freeze_with[@]}" pyinstaller packaging/study-calc.spec \
    --noconfirm --distpath "${OUTPUT_DIR}" --workpath "${BUILD_DIR}/pyinstaller"

BUNDLE="${OUTPUT_DIR}/study-calc"
test -x "${BUNDLE}/study-calc" || { echo "frozen bundle missing"; exit 1; }

# 3. Gate on the headless smoke test against the freshly built bundle.
echo ">> [2/5] Smoke test (engine mode) against the frozen bundle"
uv run --extra dev python packaging/smoke_test.py --bundle "${BUNDLE}"

# 4. Generate icons in multiple hicolor sizes (16, 24, 32, 48, 64, 128, 256).
echo ">> [3/5] Generating multi-sized hicolor icons"
ICON_BUILD_DIR="${BUILD_DIR}/icons"
rm -rf "${ICON_BUILD_DIR}"
uv run --with pillow python "${HERE}/generate_icon_sizes.py" \
    "${ROOT}/study_calc/web/frontend/icon.png" "${ICON_BUILD_DIR}" \
    --name "study-calc.png"

# 5. Assemble the AppDir around the bundle.
echo ">> [4/5] Assembling AppDir"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin" \
         "${APPDIR}/usr/share/applications" \
         "${APPDIR}/usr/share/icons/hicolor"
cp -a "${BUNDLE}/." "${APPDIR}/usr/bin/"
install -m 0755 "${HERE}/AppRun" "${APPDIR}/AppRun"
# appimagetool expects the .desktop and icon at the AppDir root, with a matching
# copy under the usual XDG locations for desktop integration once installed.
install -m 0644 "${HERE}/study-calc.desktop" "${APPDIR}/study-calc.desktop"
install -m 0644 "${HERE}/study-calc.desktop" \
    "${APPDIR}/usr/share/applications/study-calc.desktop"
# Install the largest icon size as the root icon for appimagetool, and all sizes
# to the hicolor tree for desktop integration.
install -m 0644 "${ICON_BUILD_DIR}/256x256/apps/study-calc.png" "${APPDIR}/study-calc.png"
cp -r "${ICON_BUILD_DIR}"/* "${APPDIR}/usr/share/icons/hicolor/"

# 6. Seal the AppDir into a single AppImage.
echo ">> [5/6] Locating appimagetool"
APPIMAGETOOL="$(command -v appimagetool || true)"
if [ -z "${APPIMAGETOOL}" ]; then
    TOOL="${BUILD_DIR}/appimagetool-${ARCH}.AppImage"
    if [ ! -x "${TOOL}" ]; then
        echo ">> Downloading appimagetool"
        curl -fsSL -o "${TOOL}" \
            "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
        chmod +x "${TOOL}"
    fi
    APPIMAGETOOL="${TOOL}"
fi

OUTPUT="${OUTPUT_DIR}/study-calc-${VERSION}-linux.AppImage"
echo ">> [6/6] Building ${OUTPUT}"
# --appimage-extract-and-run lets appimagetool run on hosts without FUSE (CI).
ARCH="${ARCH}" "${APPIMAGETOOL}" --appimage-extract-and-run \
    --no-appstream "${APPDIR}" "${OUTPUT}"

echo ">> Done: ${OUTPUT}"
ls -lh "${OUTPUT}"
