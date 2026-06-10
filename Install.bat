@echo off
REM ============================================================
REM  Study Calculator installer for Windows.
REM  Double-click this file to install the app into your Python.
REM  After it finishes, you can start the calculator from any
REM  terminal by typing:  study-calc
REM  (Requires Python - see README.md, section
REM   "Getting started on Windows".)
REM ============================================================

REM Install from the folder this file lives in.
cd /d "%~dp0"

REM Prefer the "py" launcher; fall back to "python" if it is not installed.
set "PY=py"
where py >nul 2>&1 || set "PY=python"

echo Installing Study Calculator into your Python...
echo.
%PY% -m pip install .

if errorlevel 1 (
    echo.
    echo The installation failed.
    echo Please make sure Python is installed and that you kept the
    echo "Add python.exe to PATH" option checked during setup.
    echo See README.md, section "Getting started on Windows", for help.
    echo.
    pause
) else (
    echo.
    echo Done! You can now run the calculator by typing:  study-calc
    echo (or just double-click Run.bat).
    echo.
    pause
)
