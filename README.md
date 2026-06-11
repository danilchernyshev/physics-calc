# Study Calculator

A desktop study calculator for solving problems in **mechanics,
thermodynamics, electromagnetism and waves**, for **symbolic math (CAS)**,
**function analysis**, **vector algebra**, **chemistry** (periodic table, molar
mass, equation balancing) and for **converting units of measurement** — with
**built-in learning materials** (key terms, useful formulas, a step-by-step
method and a worked example) shown alongside every problem. A clean, card-based
desktop interface — a [PyWebView](https://pywebview.flowrl.com/) window (see
[ADR 0001](docs/adr/0001-ui-framework.md)): pick a formula, fill in every field
but one — the program computes the missing quantity. Tabs are grouped by
subject — **Physics**, **Math**, **Tools** and **Chemistry** — and the Physics,
Math and Chemistry subjects each carry a **Problems** tab of worked practice
questions you can solve step by step.

The symbolic-math and vector tabs are aligned with the Ontario Grade 12
**Advanced Functions (MHF4U)** and **Calculus and Vectors (MCV4U)** courses:
logarithms, trigonometric identities, polynomial and rational functions and
inequalities, rates of change, limits, and 2-D/3-D vectors. Each topic's learning
panel shows a **curriculum badge** with the Ontario course and grade it belongs to.
The recognized courses are **MCR3U** (Functions, Grade 11) and the Grade 12 courses
**MHF4U** (Advanced Functions), **MCV4U** (Calculus and Vectors), **MDM4U**
(Mathematics of Data Management), **SPH4U** (Physics) and **SCH4U** (Chemistry) —
so the badge also appears on the Physics (SPH4U) and Chemistry (SCH4U) screens.

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
- **Vectors (MCV4U)**: a dedicated tab for 2-D and 3-D vectors — magnitude,
  addition/subtraction, scalar multiplication, the **dot** and **cross**
  products, the **angle** between vectors, **projections** and **unit vectors**,
  each with worked steps.
- **Chemistry**: a clickable 118-element periodic table, a molar-mass calculator
  and an equation balancer, alongside solution and acid-base formulas.
- **Practice problems**: a *Problems* tab inside Physics, Math and Chemistry
  lists worked questions; read the statement, then reveal the solution steps and
  the answer at your own pace, with a link to a video walkthrough and the
  underlying theory.
- **Runtime language switching** across English, Spanish, French, Russian and
  Ukrainian.
- **Lean dependencies** — SymPy powers the symbolic-math tab and PyWebView draws
  the window; everything else, including the converter, vectors and chemistry
  tabs, uses only the Python standard library.

## Install

The easiest way to use Study Calculator: download one file and open it — **no
Python, no terminal**. Grab the file for your system from the
[**Releases page**](https://github.com/danilchernyshev/study-calc/releases) — open
the latest release and download from its **Assets**.

### Windows

1. Download `study-calc-<version>-windows-setup.exe`.
2. Double-click it. The installer is **per-user** — it needs no administrator
   rights and installs in a few seconds.
3. Launch **Study Calculator** from the Start menu.

The app uses the Microsoft Edge **WebView2** runtime, which the installer adds
automatically if it isn't already present (it ships with Windows 11 and recent
Windows 10).

> **SmartScreen warning?** These builds aren't code-signed yet, so Windows may
> show a blue *"Windows protected your PC"* prompt. Click **More info → Run
> anyway** to continue.

### macOS

1. Download the DMG that matches your Mac:
   - Apple Silicon (M1/M2/M3…): `study-calc-<version>-macos-arm64.dmg`
   - Intel: `study-calc-<version>-macos-intel.dmg`
2. Open the DMG and drag **Study Calculator** into **Applications**.
3. Launch it from Launchpad or Applications.

> **"Apple cannot check it for malicious software"?** These builds aren't
> notarized yet. **Right-click** (or Control-click) the app → **Open** → **Open**
> the first time, and macOS will remember your choice.

### Linux

**Flatpak (recommended).** Bundles its own WebKit, so it works on any distro with
Flatpak — no system packages to install:

```bash
flatpak install study-calc-<version>-linux.flatpak
flatpak run io.github.danilchernyshev.StudyCalc
```

The app then appears in your application menu like any native app.

**`.deb` (Debian / Ubuntu / Linux Mint).** The native APT package — the best fit
for Mint. Download `study-calc_<version>_amd64.deb`, then double-click it in your
Software Manager, or install from a terminal:

```bash
sudo apt install ./study-calc_<version>_amd64.deb
```

`apt` pulls the WebKitGTK it needs, and Study Calculator appears in your
application menu with its icon. Remove it any time with `sudo apt remove
study-calc`.

**AppImage (fallback).** Download `study-calc-<version>-linux.AppImage`, make it
executable, and run it:

```bash
chmod +x study-calc-<version>-linux.AppImage
./study-calc-<version>-linux.AppImage
```

(Prefer no terminal? In your file manager, right-click the AppImage →
**Properties** → allow **Executable**, then double-click it.)

> The AppImage relies on your system's **WebKitGTK**. If it doesn't start,
> install `libwebkit2gtk-4.1-0` (Debian/Ubuntu/Mint), `webkit2gtk4.1` (Fedora),
> or your distro's equivalent. The Flatpak has no such requirement.

### Updating

Study Calculator checks [GitHub Releases](https://github.com/danilchernyshev/study-calc/releases)
for a newer version on startup and **never updates itself silently**. Open the
**Updates** panel (the ⬆ button in the sidebar) to:

- see whether a newer version is available, with its release notes;
- **force a check** at any time with **Check for updates**;
- turn the automatic startup check on or off.

Minor and patch updates are **optional** — you choose whether to install them and
can keep your current version. How you apply an update depends on how you
installed the app:

- **Windows** — download and run the latest installer; it upgrades in place.
- **macOS** — download the matching DMG and drag-replace the app in Applications.
- **Flatpak** — update through your software centre or `flatpak update
  io.github.danilchernyshev.StudyCalc` (the app never self-updates here).
- **`.deb`** — download the newer `.deb` and install it over the current one
  (`sudo apt install ./study-calc_<version>_amd64.deb`).
- **AppImage** — replace the file with the new one (AppImageUpdate where
  supported).

## Run from source (developers)

Prefer to run from the source tree (to contribute, or before a release is
published for your platform)? The per-OS walkthroughs below install Python, fetch
the project, and run it. End users should use the one-click [Install](#install)
section above instead.

### From source on Windows (step by step)

New to Python? No problem — this section walks you through everything from the
beginning. You do not need any prior experience. Just follow the steps in order,
and you will have the calculator running in a few minutes.

You will do three things: install Python, get the project files, and run one
command.

#### Step 1 — Install Python

1. Open [python.org/downloads/windows](https://www.python.org/downloads/windows/)
   and download the latest **Windows installer** (the regular 64-bit version is
   fine).
2. Run the file you downloaded.
3. On the first screen, check the box **"Add python.exe to PATH"** at the
   bottom. This step is easy to miss, but it matters — it lets Windows find
   Python later.
4. Click **Install Now** and wait for it to finish. You can close the installer
   when it is done. The calculator's window is drawn with the Microsoft Edge
   WebView2 runtime, which is already built into Windows 10 and 11 — nothing
   else to tick.

To check that it worked, open the **Start menu**, type `PowerShell`, and open it.
In the window that appears, type the following and press **Enter**:

```powershell
py --version
```

If you see something like `Python 3.12.x`, you are ready for the next step. If
you instead see an error, the most common cause is a missed "Add to PATH" box —
reinstalling and checking that box usually fixes it.

#### Step 2 — Get the project files

Copy the `study-calc` folder onto your computer — for example, from the USB
drive to your Desktop or to `C:\study-calc`. Keep all the files together in
one folder; nothing else needs to be set up.

#### Step 3 — Run the calculator

The simplest way: open the `study-calc` folder in File Explorer and
**double-click `Run.bat`**. The first time, it installs what the app needs
(PyWebView and SymPy) and then opens the window; every run after that is
instant. No terminal needed.

> If Windows shows a blue "Windows protected your PC" message the first time,
> click **"More info"** and then **"Run anyway"** — the file is just new, not
> unsafe.

Prefer the terminal? Right-click an empty area inside the folder, choose
**"Open in Terminal"** (on older Windows versions this may say "Open PowerShell
window here"), and run these two lines:

```powershell
py -m pip install .
py -m study_calc
```

The first line installs the app (a one-time step); the second opens it. After
installing, a `study-calc` command also works from any terminal, and `Run.bat`
keeps working too. (Double-clicking `Install.bat` does the same one-time install
for you.)

If you get stuck on any step, it is completely normal — feel free to ask for
help. The shorter, technical instructions for each operating system are below.

### From source on macOS (step by step)

New to Python on the Mac? This section walks you through the same three things:
install Python, get the project files, and run one command. No prior experience
needed.

#### Step 1 — Install Python

1. Open [python.org/downloads/macos](https://www.python.org/downloads/macos/)
   and download the latest **macOS installer** (the universal2 `.pkg`).
2. Open the downloaded `.pkg` and click through the installer (the defaults are
   fine). Nothing else needs to be ticked — PyWebView draws the window with the
   **WebKit** that is already part of macOS.

To check that it worked, open **Terminal** (press ⌘ + Space, type `Terminal`,
press Enter) and run:

```bash
python3 --version
```

If you see something like `Python 3.12.x`, you are ready for the next step.

#### Step 2 — Get the project files

Copy the `study-calc` folder onto your Mac — for example, onto your Desktop.
Keep all the files together in one folder.

#### Step 3 — Run the calculator

In Terminal, go into the folder (type `cd `, then drag the `study-calc` folder
onto the Terminal window and press Enter) and run these two lines:

```bash
pip3 install .
python3 -m study_calc
```

The first line installs the app (a one-time step); the second opens the window.
After installing, a `study-calc` command also works from any terminal.

### From source on Linux (step by step)

The same three things — with one extra: on Linux the window's web view comes
from system packages, so you install those first.

#### Step 1 — Install Python and the web-view packages

Most Linux distributions already ship Python 3. Check with:

```bash
python3 --version
```

If it is missing or older than 3.10, install it with your distribution's package
manager (e.g. `sudo apt-get install -y python3 python3-pip` on Debian/Ubuntu).
Then install **WebKit2GTK** and **PyGObject**, which PyWebView needs to draw the
window — pick the line for your distribution:

```bash
sudo apt-get install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1   # Debian / Ubuntu / Mint
sudo dnf install -y python3-gobject gtk3 webkit2gtk4.1                  # Fedora / RHEL
sudo pacman -S python-gobject gtk3 webkit2gtk                          # Arch / Manjaro
sudo zypper install python3-gobject webkit2gtk3                        # openSUSE
```

#### Step 2 — Get the project files

Copy the `study-calc` folder onto your computer and keep all the files together
in one folder.

#### Step 3 — Run the calculator

Open a terminal in that folder and run:

```bash
pip install .
python3 -m study_calc
```

The first line installs the app (a one-time step); the second opens the window.
Because PyGObject is a system package, run the app with a Python that can see it
— the system interpreter, or a virtualenv created with `--system-site-packages`.

## Requirements

- Python ≥ 3.10
- [PyWebView](https://pywebview.flowrl.com/) — pulled in automatically when you
  install the package. It draws the window with each platform's native web view:
  the Microsoft Edge **WebView2** runtime on Windows (already built into Windows
  10 and 11), **WebKit** on macOS, and **WebKit2GTK** on Linux (a system package
  on some distributions — see the platform notes below).
- A graphical session (X11 or Wayland on Linux); the app is a desktop window.

## Running

`python -m study_calc` (and the `study-calc` command) open the **PyWebView**
desktop window — a flat, card-based UI built from the shared
`core`/`domains`/`navigation`/i18n layers (see
[ADR 0001](docs/adr/0001-ui-framework.md)). PyWebView is a core dependency, so
installing the package is all you need. The app runs on **Windows, macOS and
Linux**:

```bash
# option 1 — via uv (no system install; resolves the project automatically)
uv run python -m study_calc

# option 2 — install the package; a `study-calc` command appears on PATH
pip install .
study-calc
```

(`study-calc-web` is an alias for the same window.)

### Windows

The official [python.org](https://www.python.org/downloads/windows/) installer
is all you need (keep **"Add python.exe to PATH"** checked). The window uses the
Microsoft Edge **WebView2** runtime, which ships with Windows 10 and 11. Use the
`py` launcher in **PowerShell** or **cmd**:

```powershell
py -m pip install .
py -m study_calc
```

Or just use the bundled `Run.bat` — it installs on first run; see
[From source on Windows](#from-source-on-windows-step-by-step).

> Note: the Python from the Microsoft Store works the same way.

### macOS

The official [python.org](https://www.python.org/downloads/macos/) installer
works as-is — PyWebView draws the window with the system **WebKit**:

```bash
pip3 install .
python3 -m study_calc
```

### Linux

PyWebView's backend needs **WebKit2GTK** and **PyGObject** from your
distribution's packages. Install them, then install and run the app:

```bash
sudo apt-get install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1   # Debian / Ubuntu / Mint
sudo dnf install -y python3-gobject gtk3 webkit2gtk4.1                  # Fedora / RHEL
sudo pacman -S python-gobject gtk3 webkit2gtk                          # Arch / Manjaro
sudo zypper install python3-gobject webkit2gtk3                        # openSUSE
```

```bash
pip install .
python3 -m study_calc
```

Because PyGObject is a system package, run the app with a Python that can see it
— the system interpreter, or a virtualenv created with `--system-site-packages`.

## Tests

The calculation and converter logic is covered by tests that do not require a
graphical environment:

```bash
uv run --extra dev pytest        # or: pytest
```

## Project structure

```
study_calc/
├── core/            # domain engine (UI- and language-agnostic)
│   ├── formula.py   #   Formula/Variable model + "solve for any variable"
│   ├── units.py     #   unit converter
│   ├── cas.py       #   symbolic math (SymPy wrapper, sandboxed parse)
│   ├── vectors.py   #   2-D/3-D vector algebra
│   ├── periodic.py  #   chemistry engine: molar mass, composition, balancer
│   ├── explain.py   #   learning-content model (i18n keys + references)
│   ├── learning.py  #   rich learning-material + practice-problem loader
│   └── db.py        #   SQLite knowledgebase repository
├── domains/         # declarative formula sets, one module per section
│   ├── mechanics.py
│   ├── thermodynamics.py
│   ├── electromagnetism.py
│   ├── waves.py
│   ├── chemistry.py #   solutions, acids & bases
│   └── references.py#   registry of study links (OpenStax + videos)
├── data/            # data files for the engines
│   ├── elements.json    #   118-element periodic table
│   ├── knowledgebase.db #   SQLite learning-content store
│   ├── schema.sql       #   its schema
│   └── README.md
├── web/             # PyWebView desktop interface (ADR 0001)
│   ├── app.py       #   opens the window over frontend/
│   ├── bridge.py    #   JS<->Python js_api (builds the localized shell model)
│   ├── screens.py   #   per-screen view-model builders
│   ├── tokens.json  #   canonical, framework-agnostic design tokens
│   ├── tokens.py    #   loader + CSS-custom-property generator
│   └── frontend/    #   index.html + vanilla-JS components and screens
├── navigation.py    # subject grouping for the app tabs (UI-framework-free)
├── learning/        # learning content: topics, glossary, practice problems
├── i18n.py          # runtime localization engine
├── locales/         # translation catalogs (en, es, fr, ru, uk)
├── resources.py     # bundled-resource path resolver (data/, frontend/)
└── __main__.py      # entry point for `python -m study_calc`
tests/               # pytest tests for the core (no graphical environment)
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

The app picks up the new formula automatically — no interface changes are
needed. (See `CLAUDE.md` for the full i18n contract.)

## Design decisions

Architecture decisions are recorded as ADRs under [`docs/adr/`](docs/adr/):

- [0001 — UI framework for the redesign](docs/adr/0001-ui-framework.md): adopts
  a PyWebView web frontend (reusing the existing `core`/`domains`/i18n layers)
  for the upcoming flat, card-based redesign.

The redesign's visual style (colors, typography, spacing, radii, elevation) is
captured as a single source of truth in
[`study_calc/web/tokens.json`](study_calc/web/tokens.json) and documented in
[`docs/design-tokens.md`](docs/design-tokens.md); `tokens.py` emits them as the
CSS custom properties the frontend consumes.

## License

MIT — see [LICENSE](LICENSE).
