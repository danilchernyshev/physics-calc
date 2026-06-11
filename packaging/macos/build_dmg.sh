#!/usr/bin/env bash
# Build the study-calc macOS app + DMG (#64, epic #60).
#
# Reuses the shared PyInstaller spec (packaging/study-calc.spec, #62), whose
# macOS branch wraps the one-folder bundle into "Study Calc.app". This script:
#   1. Generates study-calc.icns from icon.png (native sips + iconutil).
#   2. Freezes the app -> dist/Study Calc.app (+ the plain dist/study-calc/).
#   3. Smoke-tests the frozen bundle headlessly (packaging/smoke_test.py).
#   4. Packages the .app into a drag-to-Applications DMG.
#
# The DMG is named per the host architecture (arm64); Intel builds are no longer
# supported (#151). Building on Apple Silicon yields study-calc-<version>-macos-arm64.dmg.
# Universal builds are a later option.
#
# Usage (on macOS, with the project installed: pip install -e .[packaging]):
#   packaging/macos/build_dmg.sh
#
# macOS-only: PyInstaller's BUNDLE, sips, iconutil and hdiutil are all native
# tools. The real build and acceptance run on a macOS CI runner / maintainer Mac.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
cd "${ROOT}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "build_dmg.sh must run on macOS (needs sips, iconutil, hdiutil)." >&2
    exit 1
fi

VERSION="$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')"
case "$(uname -m)" in
    arm64) ARCH="arm64" ;;
    x86_64) ARCH="intel" ;;
    *) ARCH="$(uname -m)" ;;
esac
APP="dist/Study Calc.app"
DMG="dist/study-calc-${VERSION}-macos-${ARCH}.dmg"
echo ">> Building study-calc ${VERSION} macOS DMG (${ARCH})"

# 1. Icon: assemble an .icns from the PNG via an iconset of the required sizes.
echo ">> [1/4] Generating study-calc.icns"
ICONSET="$(mktemp -d)/study-calc.iconset"
mkdir -p "${ICONSET}"
SRC="study_calc/web/frontend/icon.png"
for size in 16 32 128 256 512; do
    sips -z "${size}" "${size}" "${SRC}" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "${double}" "${double}" "${SRC}" --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${ICONSET}" -o "${HERE}/study-calc.icns"

# 2. Freeze. The spec's darwin branch produces the .app from the COLLECT output.
echo ">> [2/4] PyInstaller freeze"
rm -rf "dist/study-calc" "${APP}"
python -m PyInstaller --noconfirm --clean packaging/study-calc.spec

# 3. Smoke-test the plain one-folder bundle PyInstaller emits next to the .app.
echo ">> [3/4] Smoke test (frozen bundle)"
python packaging/smoke_test.py --bundle "dist/study-calc"

# 4. Package the .app into a compressed, drag-to-Applications DMG.
echo ">> [4/4] Building DMG"
rm -f "${DMG}"
STAGING="$(mktemp -d)/dmg"
mkdir -p "${STAGING}"
cp -R "${APP}" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"
hdiutil create -volname "Study Calc" -srcfolder "${STAGING}" \
    -ov -format UDZO "${DMG}"

echo ">> Done: ${DMG}"
ls -lh "${DMG}"
