<#
.SYNOPSIS
    Build the study-calc Windows installer (#63, epic #60).

.DESCRIPTION
    Wires the whole packaging flow on a Windows host / CI runner:
      1. Freeze the app with PyInstaller (packaging/study-calc.spec, #62)
         -> dist\study-calc\ (one-folder bundle).
      2. Smoke-test that frozen bundle headlessly (packaging/smoke_test.py).
      3. Generate study-calc.ico from study_calc/web/frontend/icon.png
         (Inno Setup's SetupIconFile needs a real .ico).
      4. Fetch the Microsoft Edge WebView2 Evergreen Bootstrapper (~2 MB) that
         the installer runs when the runtime is absent.
      5. Compile study-calc.iss with Inno Setup, injecting the single-sourced
         version from pyproject.toml.

    Output: packaging\windows\Output\study-calc-<version>-windows-setup.exe

.NOTES
    Requirements (provisioned by CI; see packaging/windows/README.md):
      - Python with the project installed (`pip install -e .[packaging]`).
      - Inno Setup 6 (iscc.exe on PATH or at the default install location).
    Run from the project root:  powershell -File packaging\windows\build_installer.ps1
#>
[CmdletBinding()]
param(
    # Override the version instead of reading it from pyproject.toml.
    [string]$Version
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Root = (Resolve-Path (Join-Path $Here "..\..")).Path
Push-Location $Root
try {
    # --- Resolve the single-sourced version -------------------------------
    if (-not $Version) {
        $line = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"' |
            Select-Object -First 1
        if (-not $line) { throw "Could not read version from pyproject.toml" }
        $Version = $line.Matches[0].Groups[1].Value
    }
    Write-Host ">> Building study-calc $Version Windows installer"

    # --- 1. Freeze with PyInstaller --------------------------------------
    Write-Host ">> [1/5] PyInstaller freeze"
    if (Test-Path "dist\study-calc") { Remove-Item -Recurse -Force "dist\study-calc" }
    python -m PyInstaller --noconfirm --clean "packaging\study-calc.spec"
    $exe = "dist\study-calc\study-calc.exe"
    if (-not (Test-Path $exe)) { throw "Expected frozen exe not found: $exe" }

    # --- 2. Smoke-test the frozen bundle ---------------------------------
    Write-Host ">> [2/5] Smoke test (frozen bundle)"
    python "packaging\smoke_test.py" --bundle "dist\study-calc"
    if ($LASTEXITCODE -ne 0) { throw "Smoke test failed" }

    # --- 3. Generate the installer icon ----------------------------------
    Write-Host ">> [3/5] Generating study-calc.ico"
    & (Join-Path $Here "make_ico.ps1") `
        -Source "study_calc\web\frontend\icon.png" `
        -Destination (Join-Path $Here "study-calc.ico")

    # --- 4. Fetch the WebView2 bootstrapper ------------------------------
    Write-Host ">> [4/5] Fetching WebView2 Evergreen Bootstrapper"
    $bootstrap = Join-Path $Here "MicrosoftEdgeWebview2Setup.exe"
    if (-not (Test-Path $bootstrap)) {
        # Microsoft's stable evergreen bootstrapper redirect.
        Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" `
            -OutFile $bootstrap -UseBasicParsing
    }

    # --- 5. Compile with Inno Setup --------------------------------------
    Write-Host ">> [5/5] Inno Setup compile"
    $iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if (-not $iscc) {
        $candidates = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
        )
        $iscc = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if (-not $iscc) { throw "iscc.exe (Inno Setup 6) not found on PATH or default location" }
    } else {
        $iscc = $iscc.Source
    }
    & $iscc "/DMyAppVersion=$Version" (Join-Path $Here "study-calc.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed" }

    $out = Join-Path $Here "Output\study-calc-$Version-windows-setup.exe"
    if (-not (Test-Path $out)) { throw "Installer not produced: $out" }
    Write-Host ">> Done: $out"
    Get-Item $out | Select-Object Name, Length
} finally {
    Pop-Location
}
