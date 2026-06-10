@echo off
REM ============================================================
REM  Study Calculator launcher for Windows.
REM  Double-click this file to start the app.
REM  (Requires Python - see README.md, section
REM   "Getting started on Windows". The window is drawn with the
REM   built-in Microsoft Edge WebView2 runtime, no extra setup.)
REM ============================================================

REM Run from the folder this file lives in, so Python finds the project.
cd /d "%~dp0"

REM Prefer the "py" launcher; fall back to "python" if it is not installed.
set "PY=py"
where py >nul 2>&1 || set "PY=python"

REM The window is drawn with pywebview, a third-party package. If it is not
REM importable yet, install the project (pulls pywebview + sympy) on first run.
%PY% -c "import webview" >nul 2>&1 || (
    echo First-time setup: installing the calculator and its dependencies...
    echo.
    %PY% -m pip install .
    echo.
)

%PY% -m study_calc

REM If the app failed to start, keep the window open and show a hint.
if errorlevel 1 (
    echo.
    echo The calculator could not start.
    echo Please make sure Python is installed and that you kept the
    echo "Add python.exe to PATH" option checked during setup.
    echo See README.md, section "Getting started on Windows", for help.
    echo.
    pause
)
