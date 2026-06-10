@echo off
REM ============================================================
REM  Study Calculator launcher for Windows.
REM  Double-click this file to start the app.
REM  (Requires Python with Tkinter - see README.md, section
REM   "Getting started on Windows".)
REM ============================================================

REM Run from the folder this file lives in, so Python finds the project.
cd /d "%~dp0"

REM Prefer the "py" launcher; fall back to "python" if it is not installed.
set "PY=py"
where py >nul 2>&1 || set "PY=python"

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
