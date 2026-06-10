# Updating Study Calculator

Study Calculator checks GitHub Releases for a newer version and **never updates
itself silently**. The platform-agnostic check, notification, and opt-in policy
live in #74; this page documents how the update is actually *applied* on each
packaging format (#75).

## How the app decides

`study_calc.core.installer.detect_format()` classifies the running build:

| Format | Detected by | Self-update? |
| --- | --- | --- |
| Flatpak | `FLATPAK_ID` / `/.flatpak-info` | No — defers to the system updater |
| AppImage | `APPIMAGE` env | Yes — replace in place (AppImageUpdate) |
| Windows | frozen + `win32` | Yes — re-run the installer |
| macOS | frozen + `darwin` | Yes — download + drag-replace the DMG |
| source | not frozen | No — `git pull` + reinstall |

When the in-app **Updates** panel reports a newer release, it shows the matching
guidance (and, for Flatpak/source, the exact command to run).

## Per-format apply

- **Windows (#63):** download the latest
  `study-calc-<version>-windows-setup.exe` from the release page and run it. The
  per-user Inno Setup installer upgrades the existing install in place; close the
  app first if prompted.
- **macOS (#64):** download the matching-arch
  `study-calc-<version>-macos-<arch>.dmg`, open it, and drag the app into
  `/Applications`, replacing the old version. (Sparkle-based auto-update is a
  possible follow-up once the build is signed and notarized.)
- **Flatpak (#65):** the app does **not** self-update. Update through GNOME
  Software / KDE Discover, or run `flatpak update io.github.danilchernyshev.StudyCalc`.
  Flathub drives updates once the app is published there.
- **AppImage (#66):** download the new
  `study-calc-<version>-linux.AppImage` and replace your current file. If the
  AppImage embeds update info, `AppImageUpdate` / `appimageupdatetool` can update
  it in place with zsync.

## Integrity

Before any downloaded artifact is executed, verify it against the checksum
published with the release: `study_calc.core.installer.verify_sha256(path, digest)`
returns `False` for a tampered, truncated, or missing file, so a failed check
falls back to the manual "download from the release page" link instead of running
anything.

## Acceptance (per-platform, on clean VMs)

Automated download-and-relaunch is platform-specific and verified outside the
unit suite: install version *N*, publish *N+1*, update via the app, and confirm
the app reports *N+1*. The headlessly-tested core here covers format detection,
the integrity check, and the per-format guidance model (`tests/test_installer.py`,
`tests/test_web_updates.py`).
