# Physics Calculator

A desktop calculator for solving problems in **mechanics, thermodynamics,
electromagnetism and waves**, and for **converting units of measurement**.
A simple, clear Tkinter interface: pick a formula, fill in every field but
one — the program computes the missing quantity.

The interface is **localized** (English, Spanish, French, Russian, Ukrainian)
and the language can be switched at runtime.

## Features

- **Solve for any variable.** In the formula `F = m·a` you can find any of
  `F`, `m`, `a` — just leave the field you want to compute empty.
- **Four physics sections** with ready-made formulas:
  - Mechanics — Newton's laws, kinematics, momentum, energy, work, power;
  - Thermodynamics — heat, the ideal gas law, Carnot efficiency, thermal
    expansion;
  - Electromagnetism — Ohm's law, power, Coulomb's law, capacitors, conductor
    resistance;
  - Waves & optics — wave speed, period/frequency, photon energy, light
    wavelength, Snell's law.
- **Unit converter**: length, mass, time, speed, energy, pressure, force and
  temperature.
- **Runtime language switching** across English, Spanish, French, Russian and
  Ukrainian.
- **Zero external dependencies** — only the Python standard library.

## Getting started on Windows (step by step)

New to Python? No problem — this section walks you through everything from the
beginning. You do not need any prior experience. Just follow the steps in order,
and you will have the calculator running in a few minutes.

You will do three things: install Python, get the project files, and run one
command.

### Step 1 — Install Python

1. Open [python.org/downloads/windows](https://www.python.org/downloads/windows/)
   and download the latest **Windows installer** (the regular 64-bit version is
   fine).
2. Run the file you downloaded.
3. On the first screen, check the box **"Add python.exe to PATH"** at the
   bottom. This step is easy to miss, but it matters — it lets Windows find
   Python later.
4. Make sure the **"tcl/tk and IDLE"** option stays selected (it is on by
   default). This is the part that draws the program's window, so the calculator
   needs it.
5. Click **Install Now** and wait for it to finish. You can close the installer
   when it is done.

To check that it worked, open the **Start menu**, type `PowerShell`, and open it.
In the window that appears, type the following and press **Enter**:

```powershell
py --version
```

If you see something like `Python 3.12.x`, you are ready for the next step. If
you instead see an error, the most common cause is a missed "Add to PATH" box —
reinstalling and checking that box usually fixes it.

### Step 2 — Get the project files

Copy the `physics-calc` folder onto your computer — for example, from the USB
drive to your Desktop or to `C:\physics-calc`. Keep all the files together in
one folder; nothing else needs to be set up.

### Step 3 — Run the calculator

1. Open the `physics-calc` folder in File Explorer.
2. Right-click an empty area inside the folder and choose
   **"Open in Terminal"** (on older Windows versions this may say
   "Open PowerShell window here").
3. Type this command and press **Enter**:

   ```powershell
   py -m physics_calc
   ```

The calculator window should open. That's it! To use it again later, just repeat
Step 3.

> **Optional:** if you would rather not open a terminal each time, you can create
> a shortcut. Make a new text file in the project folder, paste the line
> `py -m physics_calc` into it, and save it as `Run.bat` (make sure the name
> ends in `.bat`, not `.txt`). Double-clicking `Run.bat` then opens the
> calculator directly.

If you get stuck on any step, it is completely normal — feel free to ask for
help. The shorter, technical instructions for each operating system are below.

## Requirements

- Python ≥ 3.10
- Tkinter — part of the Python standard library. It ships with the official
  installers on Windows and macOS, but some Linux distributions package it
  separately (see the platform notes below).

## Running

The app runs on **Windows, macOS and Linux** — it only needs Python and Tkinter,
both cross-platform. Pick the command for your shell:

```bash
# option 1 — run the module directly
python -m physics_calc

# option 2 — via uv (no system install; resolves the project automatically)
uv run python -m physics_calc

# option 3 — install as a package; a `physics-calc` command appears on PATH
pip install -e .
physics-calc
```

### Windows

The installers from [python.org](https://www.python.org/downloads/windows/)
include Tkinter by default (keep the "tcl/tk and IDLE" option checked during
setup). Use the `py` launcher in **PowerShell** or **cmd**:

```powershell
py -m physics_calc
```

If you cloned the repo, run it from the project folder. To install it as a
command instead:

```powershell
py -m pip install -e .
physics-calc
```

> Note: the Python from the Microsoft Store also bundles Tkinter and works the
> same way.

### macOS

The official [python.org](https://www.python.org/downloads/macos/) installer
includes Tkinter:

```bash
python3 -m physics_calc
```

If you use Homebrew's Python, install the Tk bindings once:

```bash
brew install python-tk
```

### Linux

Tkinter is usually a separate system package. Install it for your distribution,
then run `python3 -m physics_calc`:

```bash
sudo apt-get install -y python3-tk        # Debian / Ubuntu / Mint
sudo dnf install -y python3-tkinter       # Fedora / RHEL
sudo pacman -S tk                         # Arch / Manjaro
sudo zypper install python3-tk            # openSUSE
```

A graphical session (X11 or Wayland) is required, since the interface is a
desktop window.

## Tests

The calculation and converter logic is covered by tests that do not require a
graphical environment:

```bash
uv run --extra dev pytest        # or: pytest
```

## Project structure

```
physics_calc/
├── core/            # formula model + solving engine, unit converter
│   ├── formula.py
│   └── units.py
├── domains/         # formula sets grouped by physics section
│   ├── mechanics.py
│   ├── thermodynamics.py
│   ├── electromagnetism.py
│   └── waves.py
├── gui/             # Tkinter interface
│   └── app.py
├── i18n.py          # runtime localization engine
├── locales/         # translation catalogs (en, es, fr, ru, uk)
└── __main__.py      # entry point for `python -m physics_calc`
tests/               # pytest tests for the core (no GUI)
```

## How to add a formula

Formulas are declarative. To add a new one, create a `Formula` object in the
relevant section module and provide one solver per variable the formula can
compute. Display text is referenced by i18n *keys* (`name_key`, `unit_key`),
which must be added to every catalog in `physics_calc/locales/`:

```python
Formula(
    key="ohm",
    name_key="formula.ohm",
    expression="U = I · R",
    variables=(
        Variable("U", "var.voltage", "unit.volt"),
        Variable("I", "var.current", "unit.ampere"),
        Variable("R", "var.resistance", "unit.ohm"),
    ),
    solvers={
        "U": lambda v: v["I"] * v["R"],
        "I": lambda v: v["U"] / v["R"],
        "R": lambda v: v["U"] / v["I"],
    },
)
```

The GUI picks up the new formula automatically — no interface changes are
needed. (See `CLAUDE.md` for the full i18n contract.)

## License

MIT — see [LICENSE](LICENSE).
