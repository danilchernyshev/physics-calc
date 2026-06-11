# Linux packaging

study-calc ships three Linux formats (epic #60):

- **Flatpak** (primary, #65) — bundles its own WebKit2GTK via `org.gnome.Platform`,
  so it has no host graphics dependency.
- **`.deb`** (Debian / Ubuntu / Linux Mint, this directory, #146) — the native
  APT package for Debian-family users; `apt install` or a Software Manager
  double-click, with a proper menu entry, icon and clean uninstall.
- **AppImage** (fallback, this directory, #66) — a single double-click file for
  distros without Flatpak.

## `.deb` (Debian / Ubuntu / Linux Mint)

The native path for Debian-family users — and the best fit for **Linux Mint**.
Like the AppImage it wraps the PyInstaller one-folder bundle (so it carries no
host Python), installs it under `/opt/study-calc/`, and adds a `/usr/bin/study-calc`
launcher symlink plus a freedesktop `.desktop` entry and hicolor icon for the
application menu.

```bash
sudo apt install ./study-calc_<version>_amd64.deb   # resolves WebKit2GTK from APT
study-calc                                          # or launch from the menu
sudo apt remove study-calc                          # clean uninstall, no /opt orphans
```

It declares `Depends: libwebkit2gtk-4.1-0, gir1.2-webkit2-4.1`, so `apt` pulls the
host WebKit2GTK the frozen bundle needs (the same dependency the AppImage requires
manually). `apt install ./file.deb` (or a Software Manager double-click) is all
Mint users need — no Python, `uv` or terminal.

### Building the `.deb`

```bash
packaging/linux/build_deb.sh                  # freezes, packages into dist/
REUSE_BUNDLE=1 packaging/linux/build_deb.sh   # reuse an existing dist/study-calc
```

The script freezes the bundle from [`packaging/study-calc.spec`](../study-calc.spec)
(unless `REUSE_BUNDLE=1` and one is present), gates it on
[`packaging/smoke_test.py`](../smoke_test.py), lays out the `/opt` + `/usr` tree
with the [`.desktop`](study-calc.desktop), icon, [`copyright`](deb/copyright) and
the [`postinst`](deb/postinst)/[`postrm`](deb/postrm) cache-refresh scripts, then
runs `dpkg-deb` into `dist/study-calc_<version>_amd64.deb`. The version is read
from `pyproject.toml`. If `lintian` is installed it runs advisory-only (it never
fails the build).

**Documented lintian notes:** the bundle lives under `/opt` (lintian's
`dir-or-file-in-opt` is informational — standard for a self-contained frozen app,
mirroring the Flatpak/AppImage approach), and the frozen `_internal/` ships
PyInstaller's bundled shared libraries (the usual `embedded-library` /
`statically-linked` advisories for a frozen Python app). These are expected and
not errors.

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
