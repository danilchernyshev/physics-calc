# Linux packaging

study-calc ships two Linux formats (epic #60):

- **Flatpak** (primary, #65) — bundles its own WebKit2GTK via `org.gnome.Platform`,
  so it has no host graphics dependency.
- **AppImage** (fallback, this directory, #66) — a single double-click file for
  distros without Flatpak.

## AppImage host requirement

> **The AppImage does _not_ bundle WebKit2GTK.** It cannot be made relocatable
> inside an AppImage, so the host must already provide **`libwebkit2gtk-4.1-0`**.

Install it once per machine:

```bash
sudo apt install libwebkit2gtk-4.1-0      # Debian / Ubuntu 22.04+ / Mint
sudo dnf install webkit2gtk4.1            # Fedora / RHEL
sudo pacman -S webkit2gtk-4.1             # Arch / Manjaro
sudo zypper install libwebkit2gtk-4_1-0   # openSUSE
```

Then run it:

```bash
chmod +x study-calc-<version>-linux.AppImage
./study-calc-<version>-linux.AppImage
```

If the window does not appear, the host is almost always missing
`libwebkit2gtk-4.1-0`; install it and retry. Users who prefer a dependency-free
install should use the Flatpak instead.

## Building the AppImage

```bash
packaging/linux/build_appimage.sh
```

The script freezes the PyInstaller one-folder bundle from
[`packaging/study-calc.spec`](../study-calc.spec), gates it on
[`packaging/smoke_test.py`](../smoke_test.py), assembles an AppDir with
[`AppRun`](AppRun), [`study-calc.desktop`](study-calc.desktop) and the app icon,
and seals it with `appimagetool` into `dist/study-calc-<version>-linux.AppImage`.
`appimagetool` is taken from `PATH` if present, otherwise downloaded into
`build/`. The version is read from `pyproject.toml`.

### Validating a built AppImage

The smoke test runs against the AppImage's contents without launching a GUI by
extracting it and pointing `--bundle` at the embedded one-folder tree:

```bash
./study-calc-<version>-linux.AppImage --appimage-extract
uv run --extra dev python packaging/smoke_test.py --bundle squashfs-root/usr/bin
```

A clean-VM manual acceptance (with `libwebkit2gtk-4.1-0` present) confirms the
double-click launch.
