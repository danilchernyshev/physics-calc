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

## Requirements

- Python ≥ 3.10
- Tkinter (part of the standard library, but on some Linux distributions it is
  shipped as a separate system package):

  ```bash
  sudo apt-get install -y python3-tk        # Debian / Ubuntu
  ```

## Running

```bash
# option 1 — directly
python -m physics_calc

# option 2 — via uv (without installing into the system)
uv run python -m physics_calc

# option 3 — install as a package; a `physics-calc` command appears
pip install -e .
physics-calc
```

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
