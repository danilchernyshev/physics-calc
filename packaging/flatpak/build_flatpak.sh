#!/usr/bin/env bash
# Build the study-calc Flatpak — the primary Linux package (#65, epic #60).
#
# Produces a single-file bundle dist/study-calc-<version>-linux.flatpak from the
# org.gnome.Platform runtime, so a user installs it with `flatpak install` and
# launches from their application menu — no host GTK/WebKit, pip or terminal.
#
# Usage:
#   packaging/flatpak/build_flatpak.sh
#
# Requirements: flatpak + flatpak-builder, the org.gnome.{Platform,Sdk}//47
# runtimes (installed below if missing from the user remote), and network for the
# first dependency resolution. CI provisions these.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
APP_ID="io.github.danilchernyshev.StudyCalc"
MANIFEST="${HERE}/${APP_ID}.yml"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT}/dist}"
BUILD_DIR="${ROOT}/build/flatpak"
STATE_DIR="${BUILD_DIR}/state"
REPO="${BUILD_DIR}/repo"

cd "${ROOT}"

VERSION="$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')"
echo ">> Building ${APP_ID} ${VERSION} Flatpak"

# 1. Vendor hash-pinned pip sources for the manifest (offline, reproducible build).
echo ">> [1/4] Generating pinned Python dependency sources"
"${HERE}/generate-deps.sh"

# 2. Ensure the GNOME runtime/SDK are available (no-op if already installed).
echo ">> [2/4] Ensuring org.gnome.Platform//47 and org.gnome.Sdk//47"
flatpak install --user --noninteractive --or-update flathub \
    org.gnome.Platform//47 org.gnome.Sdk//47 || true

# 3. Build into a local repo.
echo ">> [3/4] flatpak-builder"
rm -rf "${STATE_DIR}" "${REPO}"
flatpak-builder --user --force-clean --disable-rofiles-fuse \
    --state-dir "${STATE_DIR}" --repo "${REPO}" \
    "${BUILD_DIR}/build" "${MANIFEST}"

# 4. Export a single-file bundle.
echo ">> [4/4] Exporting bundle"
mkdir -p "${OUTPUT_DIR}"
OUTPUT="${OUTPUT_DIR}/study-calc-${VERSION}-linux.flatpak"
flatpak build-bundle "${REPO}" "${OUTPUT}" "${APP_ID}"

echo ">> Done: ${OUTPUT}"
ls -lh "${OUTPUT}"

# Smoke-test the bundled app. Install the exported bundle and run the smoke test
# command. This tests the actual artifact users will install, and avoids the strict
# --run option parsing of flatpak-builder 1.4.x (which rejects options before positional
# args in --run mode). The manifest installs smoke_test.py as /app/bin/study-calc-smoke.
echo ">> Smoke test: installing and running bundled app"
flatpak install --user --noninteractive "${OUTPUT}"
flatpak run --command=study-calc-smoke "${APP_ID}"
echo ">> Smoke OK"
