@echo off
REM ============================================================
REM  Physics Calculator installer for Windows.
REM  Double-click this file to install the app into your Python.
REM  After it finishes, you can start the calculator from any
REM  terminal by typing:  physics-calc
REM  (Requires Python - see README.md, section
REM   "Getting started on Windows".)
REM ============================================================

REM Install from the folder this file lives in.
cd /d "%~dp0"

echo Installing Physics Calculator into your Python...
echo.
py -m pip install -e .

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
    echo Done! You can now run the calculator by typing:  physics-calc
    echo (or just double-click Run.bat).
    echo.
    pause
)
