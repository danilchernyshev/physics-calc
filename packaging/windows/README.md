# Windows installer

A per-user Windows installer for study-calc, built with [Inno Setup
6](https://jrsoftware.org/isinfo.php). It wraps the PyInstaller one-folder bundle
(`packaging/study-calc.spec`, #62) and provisions the Edge WebView2 runtime that
PyWebView needs on Windows.

## Files

| File | Purpose |
| --- | --- |
| `study-calc.iss` | Inno Setup script (per-user install, WebView2 bootstrap) |
| `build_installer.ps1` | End-to-end build: freeze → smoke → icon → bootstrapper → compile |
| `make_ico.ps1` | Generates `study-calc.ico` from `icon.png` (System.Drawing only) |

Three files are **fetched or generated** at build time and git-ignored:
`MicrosoftEdgeWebview2Setup.exe`, `study-calc.ico`, and the `Output/` folder.

## Building

On a Windows host (or CI runner) with Python and Inno Setup 6 installed:

```powershell
pip install -e .[packaging]      # PyInstaller
powershell -File packaging\windows\build_installer.ps1
```

Output: `packaging\windows\Output\study-calc-<version>-windows-setup.exe`.

The version is read from `pyproject.toml` (single source of truth) and injected
into the compile with `iscc /DMyAppVersion=<version>`; override it with
`-Version` if needed.

> This installer **cannot be built or compiled on Linux/macOS** — Inno Setup and
> the WebView2 runtime are Windows-only. The real build and acceptance run on a
> Windows CI runner / maintainer machine; everything here is authored and
> reviewed statically on other platforms.

## What the installer does

- **Per-user, no administrator rights** (`PrivilegesRequired=lowest`), installed
  under `%LOCALAPPDATA%\Programs\study-calc`.
- **Start-menu shortcut** always; an optional desktop shortcut (off by default).
- **WebView2 runtime**: the script checks the EdgeUpdate registry keys (HKLM,
  the WOW6432Node view, and HKCU) for the Evergreen Runtime client. If it is
  absent, the bundled bootstrapper runs silently (`/silent /install`). It is
  preinstalled on Windows 11 and on Windows 10 (2019+), so most users never see
  this step.
- **No console window** — the app is frozen with `console=False`.
- **Clean uninstall** via *Apps & features* (the standard Inno uninstaller).

## SmartScreen on first run (unsigned builds)

These builds are **not code-signed**, so Microsoft Defender SmartScreen shows a
blue *"Windows protected your PC"* prompt the first time the installer runs.
To proceed, click **More info → Run anyway**. Signing the installer with an
Authenticode / EV certificate would remove this warning and is a separate,
optional follow-up (it needs a purchased certificate, so it is out of scope for
the open-source release).
