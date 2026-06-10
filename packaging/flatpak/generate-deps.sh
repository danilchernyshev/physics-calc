#!/usr/bin/env bash
# Regenerate python3-deps.yaml — the vendored, hash-pinned pip sources for the
# Flatpak manifest (#65). Run this whenever the runtime dependencies in
# pyproject.toml change (sympy, pywebview, or their transitive set).
#
# It uses flatpak-pip-generator, which resolves each requirement to a wheel/sdist
# with a sha256, so flatpak-builder can install them offline. Requires network
# and flatpak-pip-generator (from the flatpak-builder-tools repo); CI installs it.
#
# Usage:
#   packaging/flatpak/generate-deps.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GENERATOR="${FLATPAK_PIP_GENERATOR:-flatpak-pip-generator}"
if ! command -v "${GENERATOR}" >/dev/null 2>&1; then
    cat >&2 <<'MSG'
flatpak-pip-generator not found. Get it from flatpak-builder-tools:
  curl -fsSLO https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator
  chmod +x flatpak-pip-generator
Then re-run with FLATPAK_PIP_GENERATOR=./flatpak-pip-generator.
MSG
    exit 1
fi

# Keep this list in sync with [project].dependencies in pyproject.toml.
echo ">> Resolving sympy + pywebview into hash-pinned Flatpak sources"
"${GENERATOR}" --output "${HERE}/python3-deps" sympy pywebview

echo ">> Wrote ${HERE}/python3-deps.yaml"
