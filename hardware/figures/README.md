# Figure generator for `hardware/wiring-guide.html`

The guide's four figures are **pictorials**, not schematics: they draw the real
boards — PCB outline with the retention notches cut, both USB-C shells, the gold
castellated pads with their silkscreen numbers, the WROOM module, and component
bodies with their real markings (a diode's silver cathode band, a resistor's
real colour-code stripes, set per value in `BANDS`).

| File | What it does |
|---|---|
| `pictorial.py` | The drawing library. Board geometry comes from the same numbers as `enclosure/boards.scad` |
| `build_figures.py` | Places the boards and routes the wires for figures 1–4 |
| `splice.py` | Replaces the four `<svg>` blocks in the guide, in order |

```sh
python3 build_figures.py && python3 splice.py
```

## Rules the figures follow

- **Wire colours are CSS variables** (`--w-pwr`, `--w-gnd`, `--w-clk`, `--w-clk2`,
  `--w-dat`, `--w-uart`), and so are the two PCB colours and the component-body
  colour. The guide redefines all of them for dark mode; hard-coded hex would
  leave the black ESP32 board invisible on the dark surface.
- **Never red against green** (CLAUDE.md). The pairs in use are blue/amber,
  orange/teal and orange/dark.
- Figure 1 is the only one drawn to scale. Figures 2–4 keep the boards to scale
  but open the gaps between them so the wires are readable.
- Explanatory text lives in the HTML `<figcaption>`, not in the SVG. Only short
  reference designators (`D1`, `R3`, `GPIO17`) go in the drawing, so nothing
  overflows the viewBox or collides at small widths.

## Check the output before publishing

The figures are placed by hand-written coordinates with no layout engine, so
they must be **looked at**, not just generated. Earlier versions cropped the
whole ESP32 off the canvas while still producing valid SVG.

```sh
node render_check.js      # writes a PNG of each figure in both themes
```
