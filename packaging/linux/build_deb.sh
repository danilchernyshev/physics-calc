#!/usr/bin/env bash
# Build the study-calc Debian package (.deb) for Debian / Ubuntu / Linux Mint
# (#146, epic #60).
#
# The native APT path: a double-clickable / `apt install`-able package that wraps
# the PyInstaller one-folder frozen bundle (packaging/study-calc.spec, #62) under
# /opt/study-calc/, with a /usr/bin launcher symlink and a freedesktop .desktop
# entry + hicolor icon so the app appears in the Cinnamon/MATE/Xfce/GNOME menu.
# No host Python or uv is needed to *run* it — only the frozen bundle's shared
# graphics dependency (host WebKit2GTK), exactly like the AppImage (#66).
#
# Usage:
#   packaging/linux/build_deb.sh                 # build into ./dist
#   OUTPUT_DIR=/tmp packaging/linux/build_deb.sh
#   REUSE_BUNDLE=1 packaging/linux/build_deb.sh  # reuse an existing dist/study-calc
#
# Requirements: a Linux x86_64 host, uv (for the frozen build), dpkg-deb. lintian
# is run if present (advisory only). Produces
# dist/study-calc_<version>_amd64.deb.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT}/dist}"
BUILD_DIR="${ROOT}/build"
PKGROOT="${BUILD_DIR}/deb"
ARCH="amd64"

cd "${ROOT}"

# 1. Resolve the single-sourced version from pyproject.toml.
VERSION="$(uv run --extra packaging python -c \
    'from study_calc.resources import app_version; print(app_version())')"
echo ">> Building study-calc ${VERSION} .deb (${ARCH})"

# 2. Freeze the one-folder bundle from the shared spec (skip if reusing one a
#    prior step — e.g. the AppImage job — already built).
BUNDLE="${OUTPUT_DIR}/study-calc"
if [ "${REUSE_BUNDLE:-0}" = "1" ] && [ -x "${BUNDLE}/study-calc" ]; then
    echo ">> [1/5] Reusing existing frozen bundle at ${BUNDLE}"
else
    echo ">> [1/5] PyInstaller one-folder build"
    uv run --extra packaging pyinstaller packaging/study-calc.spec \
        --noconfirm --distpath "${OUTPUT_DIR}" --workpath "${BUILD_DIR}/pyinstaller"
fi
test -x "${BUNDLE}/study-calc" || { echo "frozen bundle missing"; exit 1; }

# 3. Gate on the headless smoke test against the freshly built bundle.
echo ">> [2/5] Smoke test (engine mode) against the frozen bundle"
uv run --extra dev python packaging/smoke_test.py --bundle "${BUNDLE}"

# 4. Generate icons in multiple hicolor sizes (16, 24, 32, 48, 64, 128, 256).
#    Desktop environments request small sizes and don't downscale a lone 256px icon,
#    so the app menu entry would show no icon. Use Pillow to resize from the source.
echo ">> [3/5] Generating multi-sized hicolor icons"
ICON_BUILD_DIR="${BUILD_DIR}/icons"
rm -rf "${ICON_BUILD_DIR}"
uv run --with pillow python "${HERE}/generate_icon_sizes.py" \
    "${ROOT}/study_calc/web/frontend/icon.png" "${ICON_BUILD_DIR}" \
    --name "study-calc.png"

# 5. Lay out the package root mirroring where the files land on the target system.
echo ">> [4/5] Assembling the package tree"
rm -rf "${PKGROOT}"
mkdir -p "${PKGROOT}/opt/study-calc" \
         "${PKGROOT}/usr/bin" \
         "${PKGROOT}/usr/share/applications" \
         "${PKGROOT}/usr/share/doc/study-calc" \
         "${PKGROOT}/usr/share/lintian/overrides" \
         "${PKGROOT}/DEBIAN"

# The frozen bundle (launcher + _internal/) goes under /opt; cp -a keeps the
# executable bits PyInstaller set on the launcher and the bundled .so files.
cp -a "${BUNDLE}/." "${PKGROOT}/opt/study-calc/"

# /usr/bin launcher so `study-calc` is on PATH and the .desktop Exec resolves.
ln -s /opt/study-calc/study-calc "${PKGROOT}/usr/bin/study-calc"

# Desktop entry + icons (reuse the AppImage's .desktop — its Exec=study-calc and
# Icon=study-calc match the launcher symlink and the hicolor icon name). Install
# all generated icon sizes so the desktop environment can pick the best fit.
install -m 0644 "${HERE}/study-calc.desktop" \
    "${PKGROOT}/usr/share/applications/study-calc.desktop"
cp -r "${ICON_BUILD_DIR}"/* "${PKGROOT}/usr/share/icons/hicolor/"

# Machine-readable copyright (lintian errors without it).
install -m 0644 "${HERE}/deb/copyright" \
    "${PKGROOT}/usr/share/doc/study-calc/copyright"

# lintian override: the bundle lives under /opt by design (#146), which raises
# dir-or-file-in-opt for every bundled file. Ship the override so lintian
# reports clean — the package name file is what lintian reads at check time.
install -m 0644 "${HERE}/deb/lintian-overrides" \
    "${PKGROOT}/usr/share/lintian/overrides/study-calc"

# Maintainer scripts: refresh the desktop/icon caches on (un)install.
install -m 0755 "${HERE}/deb/postinst" "${PKGROOT}/DEBIAN/postinst"
install -m 0755 "${HERE}/deb/postrm" "${PKGROOT}/DEBIAN/postrm"

# Normalise directory permissions to 0755 regardless of the build host's umask
# (a group-writable dir would draw a lintian non-standard-dir-perm warning). File
# modes are left as-is so the launcher and bundled .so keep their bits.
find "${PKGROOT}" -type d -exec chmod 0755 {} +

# 5. Control file. Installed-Size is in KiB of the payload (lintian expects it);
#    Depends declares the host graphics stack the frozen bundle relies on (the
#    same libwebkit2gtk-4.1-0 the AppImage needs, plus the GI typelib that pulls
#    it). dpkg substitutes nothing here, so the version is interpolated directly.
INSTALLED_SIZE="$(du -ks --exclude=DEBIAN "${PKGROOT}" | cut -f1)"
cat > "${PKGROOT}/DEBIAN/control" <<EOF
Package: study-calc
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Danil Chernyshev <danil.chernyshev@gmail.com>
Section: education
Priority: optional
Installed-Size: ${INSTALLED_SIZE}
Depends: libwebkit2gtk-4.1-0, gir1.2-webkit2-4.1
Homepage: https://github.com/danilchernyshev/study-calc
Description: Study calculator for physics, chemistry and math
 A desktop study calculator with physics formulas (mechanics, thermodynamics,
 electromagnetism, waves), chemistry tools (periodic table, molar mass, equation
 balancing, solution and acid-base formulas), a unit converter, a SymPy-backed
 symbolic-math (CAS) tab, a vectors tab, and built-in learning materials, in five
 languages (English, Spanish, French, Russian, Ukrainian).
 .
 This package wraps a self-contained frozen bundle, so no system Python is
 required. It does rely on the host's WebKit2GTK for the application window.
EOF

# 6. Build the archive (root:root ownership without needing fakeroot/sudo).
echo ">> [5/6] dpkg-deb --build"
OUTPUT="${OUTPUT_DIR}/study-calc_${VERSION}_${ARCH}.deb"
mkdir -p "${OUTPUT_DIR}"
dpkg-deb --root-owner-group --build "${PKGROOT}" "${OUTPUT}"

# 7. Lint. The acceptance is "lintian reports no errors" (#146): the /opt
#    placement that raised 112 dir-or-file-in-opt errors is silenced by the
#    shipped override above, so the report is clean. Kept advisory (|| true) so
#    a transient lint hiccup never blocks a release — the criterion is checked by
#    reading this output, which now shows no E: lines. Warnings (the expected
#    embedded-library / statically-linked tags of a frozen Python app) still
#    print for the record. If lintian is absent (local dev), skip.
echo ">> [6/6] lintian"
if command -v lintian >/dev/null 2>&1; then
    lintian --no-tag-display-limit "${OUTPUT}" || true
else
    echo "   lintian not installed — skipping"
fi

echo ">> Done: ${OUTPUT}"
ls -lh "${OUTPUT}"
