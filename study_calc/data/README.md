# Element data

`elements.json` is the periodic-table dataset behind the Chemistry tools
(`study_calc/core/periodic.py`): the molar-mass calculator, the equation
balancer, and the periodic-table panel.

One object per element (atomic numbers 1–118), with:

| field | meaning |
| --- | --- |
| `number` | atomic number Z |
| `symbol` | element symbol (e.g. `Na`) |
| `name` | English element name |
| `mass` | standard atomic weight, g/mol (mass number for synthetic elements) |
| `group` | periodic-table group (1–18) |
| `period` | periodic-table period (1–7) |
| `category` | series, e.g. `alkali metal`, `noble gas` |
| `xpos` / `ypos` | column / row for laying the classic table out on a grid |

## Source

Derived from the open
[Periodic-Table-JSON](https://github.com/Bowserinator/Periodic-Table-JSON)
dataset (CC BY-SA 4.0), whose values come from Wikipedia / PubChem and ultimately
the IUPAC standard atomic weights. Only the fields above are kept; everything
else is dropped. Atomic weights are facts (not copyrightable); the curated
categorisation and layout coordinates are used under CC BY-SA.
