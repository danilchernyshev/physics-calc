# macOS installer

A drag-to-Applications **DMG** containing `Study Calc.app`, built by freezing the
app with the shared PyInstaller spec (`packaging/study-calc.spec`, #62) whose
macOS branch wraps the one-folder bundle into a proper `.app`.

## Files

| File | Purpose |
| --- | --- |
| `build_dmg.sh` | icns → freeze → smoke → DMG, named per host architecture |

`study-calc.icns` and the `dist/*.dmg` output are generated and git-ignored.

## Building

On a Mac with Python and the project installed:

```bash
pip install -e .[packaging]      # PyInstaller
packaging/macos/build_dmg.sh
```

Output: `dist/study-calc-<version>-macos-<arch>.dmg`, where `<arch>` is `arm64`
(Apple Silicon) or `intel` (x86_64) — the DMG matches the Mac it was built on.
Run on both kinds of Mac to ship both; a single universal2 build is a possible
later refinement.

> This **cannot be built on Linux/Windows** — `sips`, `iconutil`, `hdiutil` and
> PyInstaller's `.app` bundling are macOS-only. It is authored and reviewed
> statically; the real build and acceptance run on a macOS CI runner / maintainer
> Mac (same approach as #66 AppImage / #65 Flatpak / #63 Windows).

## What the build does

1. **Icon** — assembles `study-calc.icns` from `icon.png` via an iconset
   (`sips` for each size, `iconutil` to pack), used as the `.app` icon.
2. **Freeze** — `pyinstaller packaging/study-calc.spec` produces
   `dist/Study Calc.app` (and the plain `dist/study-calc/` folder beside it).
3. **Smoke test** — `packaging/smoke_test.py --bundle dist/study-calc` verifies
   the engines and bundled assets headlessly before packaging.
4. **DMG** — stages the `.app` plus an `/Applications` symlink and builds a
   compressed (`UDZO`) disk image with `hdiutil`.

The version and bundle identifier come from `pyproject.toml` via
`study_calc.resources.app_version()` (single source of truth), surfaced in the
`.app`'s `Info.plist`.

## Gatekeeper on first run (unsigned builds)

These builds are **not code-signed or notarized**, so Gatekeeper blocks the app
on first launch (*"Study Calc can't be opened because Apple cannot check it for
malicious software"*). To open it, **right-click the app → Open → Open**, or
allow it under *System Settings → Privacy & Security*. Signing + notarization
with an Apple Developer ID would remove this and is a separate, optional
follow-up (it needs a paid Apple Developer account).
