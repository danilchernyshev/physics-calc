# Study Calculator

A desktop study calculator for solving problems in **mechanics,
thermodynamics, electromagnetism and waves**, for **symbolic math (CAS)**,
**function analysis and graphing**, **vector algebra**, and for **converting
units of measurement** — with **built-in learning materials** (key terms,
useful formulas, a step-by-step method and a worked example) shown alongside
every problem. A simple, clear Tkinter interface: pick a formula, fill in every
field but one — the program computes the missing quantity. Tabs are grouped by
subject — **Physics**, **Math** and **Tools**, with **Chemistry** on the way — and
the Physics and Math subjects each carry a **Problems** tab of worked practice
questions you can solve step by step.

The symbolic-math, graphing and vector tabs are aligned with the Ontario Grade 12
**Advanced Functions (MHF4U)** and **Calculus and Vectors (MCV4U)** courses:
logarithms, trigonometric identities, polynomial and rational functions and
inequalities, rates of change, limits, and 2-D/3-D vectors. Each topic's learning
panel shows a **curriculum badge** with the Ontario course and grade it belongs to
(MCR3U — Grade 11, MHF4U — Grade 12, or MCV4U — Grade 12).

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
- **Unit converter**: length, mass, time, speed, energy, pressure, force,
  temperature and **angle** (degrees ↔ radians ↔ gradians).
- **Symbolic math (CAS)** powered by [SymPy](https://www.sympy.org/): an
  *Analyze* overview (simplified, factored, derivative, integral, real roots and
  Taylor series at once, à la Wolfram Alpha), plus standalone simplify, expand,
  factor, differentiate, integrate, Taylor series, solve equations, and evaluate
  numerically. The variable is auto-detected when there is only one unknown, and
  every answer comes with a step-by-step explanation. Type math naturally — `^`
  means a power and `2x` means `2·x`. Input is parsed in a sandbox, never
  executed as Python.
- **Advanced Functions (MHF4U) tools** in the same tab: solve polynomial and
  rational **inequalities**, apply the **laws of logarithms**, simplify
  trigonometric expressions and **prove trig identities**, analyze a function's
  key features for curve sketching (domain, intercepts, vertical/horizontal/
  oblique **asymptotes**, **holes**, end behaviour, turning points), find
  **average and instantaneous rates of change**, evaluate **limits**, and
  **combine or compose** two functions.
- **Graphing**: a *Plot* button draws any expression with
  [matplotlib](https://matplotlib.org/), marking the axes and vertical
  asymptotes — connecting the algebra to the picture.
- **Vectors (MCV4U)**: a dedicated tab for 2-D and 3-D vectors — magnitude,
  addition/subtraction, scalar multiplication, the **dot** and **cross**
  products, the **angle** between vectors, **projections** and **unit vectors**,
  each with worked steps.
- **Practice problems**: a *Problems* tab inside Physics and Math lists worked
  questions; read the statement, then reveal the solution steps and the answer at
  your own pace, with a link to a video walkthrough and the underlying theory.
- **Runtime language switching** across English, Spanish, French, Russian and
  Ukrainian.
- **Two lightweight dependencies** — SymPy (symbolic math) and matplotlib
  (graphing); everything else, including the vector tab, uses only the Python
  standard library.

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

Copy the `study-calc` folder onto your computer — for example, from the USB
drive to your Desktop or to `C:\study-calc`. Keep all the files together in
one folder; nothing else needs to be set up.

### Step 3 — Run the calculator

1. Open the `study-calc` folder in File Explorer.
2. Right-click an empty area inside the folder and choose
   **"Open in Terminal"** (on older Windows versions this may say
   "Open PowerShell window here").
3. Type this command and press **Enter**:

   ```powershell
   py -m study_calc
   ```

The calculator window should open. That's it! To use it again later, just repeat
Step 3.

> **Easiest option:** the project already includes a `Run.bat` file. Once Python
> is installed (Step 1), you can simply **double-click `Run.bat`** in the project
> folder to open the calculator — no terminal needed.

> **Optional — install it as a command:** if you would like to start the
> calculator by typing `study-calc` from any terminal (instead of running it
> from this folder), **double-click `Install.bat`** once. It installs the app
> into your Python using `py -m pip install .`. After that, `study-calc`
> works from anywhere, and `Run.bat` keeps working too.

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
python -m study_calc

# option 2 — via uv (no system install; resolves the project automatically)
uv run python -m study_calc

# option 3 — install as a package; a `study-calc` command appears on PATH
pip install -e .
study-calc
```

### Windows

The installers from [python.org](https://www.python.org/downloads/windows/)
include Tkinter by default (keep the "tcl/tk and IDLE" option checked during
setup). Use the `py` launcher in **PowerShell** or **cmd**:

```powershell
py -m study_calc
```

If you cloned the repo, run it from the project folder. To install it as a
command instead:

```powershell
py -m pip install .
study-calc
```

> Note: the Python from the Microsoft Store also bundles Tkinter and works the
> same way.

### macOS

The official [python.org](https://www.python.org/downloads/macos/) installer
includes Tkinter:

```bash
python3 -m study_calc
```

If you use Homebrew's Python, install the Tk bindings once:

```bash
brew install python-tk
```

### Linux

Tkinter is usually a separate system package. Install it for your distribution,
then run `python3 -m study_calc`:

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
study_calc/
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
├── navigation.py    # subject grouping for the GUI tabs (Tk-free)
├── learning/        # learning content: topics, glossary, practice problems
├── i18n.py          # runtime localization engine
├── locales/         # translation catalogs (en, es, fr, ru, uk)
└── __main__.py      # entry point for `python -m study_calc`
tests/               # pytest tests for the core (no GUI)
```

## How to add a formula

Formulas are declarative. To add a new one, create a `Formula` object in the
relevant section module and provide one solver per variable the formula can
compute. Display text is referenced by i18n *keys* (`name_key`, `unit_key`),
which must be added to every catalog in `study_calc/locales/`:

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

## Design decisions

Architecture decisions are recorded as ADRs under [`docs/adr/`](docs/adr/):

- [0001 — UI framework for the redesign](docs/adr/0001-ui-framework.md): adopts
  a PyWebView web frontend (reusing the existing `core`/`domains`/i18n layers)
  for the upcoming flat, card-based redesign.

## License

MIT — see [LICENSE](LICENSE).
