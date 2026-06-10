# Flatpak package (primary Linux channel)

Flatpak is study-calc's **primary** Linux distribution (the [AppImage](../linux)
is the fallback). It targets the `org.gnome.Platform` 47 runtime, which bundles
WebKit2GTK and PyGObject — so PyWebView's GTK backend works inside the sandbox
with **no host GTK/WebKit dependency**, on any distro with Flatpak.

## Files

| File | Purpose |
| --- | --- |
| `io.github.danilchernyshev.StudyCalc.yml` | Flatpak manifest (runtime, modules, build) |
| `io.github.danilchernyshev.StudyCalc.desktop` | Application launcher |
| `io.github.danilchernyshev.StudyCalc.metainfo.xml` | AppStream metadata for GNOME Software / KDE Discover |
| `generate-deps.sh` | Regenerates `python3-deps.yaml` (hash-pinned pip sources) |
| `build_flatpak.sh` | Builds and exports the `.flatpak` bundle |

`python3-deps.yaml` is a **generated** lockfile (vendored, hash-pinned wheels for
`sympy`, `pywebview` and their transitive deps) and is not committed — the build
script regenerates it. Run `generate-deps.sh` whenever the runtime dependencies in
`pyproject.toml` change.

## Building

```bash
packaging/flatpak/build_flatpak.sh
```

This generates the pinned dependency sources, installs the GNOME runtime/SDK if
missing, builds with `flatpak-builder`, exports
`dist/study-calc-<version>-linux.flatpak`, and runs the smoke test
(`/app/bin/study-calc-smoke`) inside the sandbox.

Requirements: `flatpak`, `flatpak-builder`, `flatpak-pip-generator` (from
[flatpak-builder-tools](https://github.com/flatpak/flatpak-builder-tools)), and
network for the first dependency resolution. CI provisions these.

## Installing the built bundle

```bash
flatpak install --user study-calc-<version>-linux.flatpak
flatpak run io.github.danilchernyshev.StudyCalc
```

The app then appears in the application menu like any native app. Flathub
submission can follow as a separate step.

## Validating

```bash
desktop-file-validate packaging/flatpak/io.github.danilchernyshev.StudyCalc.desktop
appstreamcli validate --no-net packaging/flatpak/io.github.danilchernyshev.StudyCalc.metainfo.xml
# Engines inside the sandbox:
flatpak run --command=study-calc-smoke io.github.danilchernyshev.StudyCalc
```
