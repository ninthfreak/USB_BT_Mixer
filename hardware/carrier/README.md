# Carrier board

One flat PCB that the three modules solder onto, replacing the hand-wired
loom. All ten passives live on it. Status: **schematic only, not laid out,
not ordered.**

## Why a carrier at all

Both modules are through-hole *and* castellated on the edge (owner, boards in
hand), so each one solders flat with the iron touching the **outside** of
every joint: visible, inspectable, reworkable, no reflow, and the lowest
possible stack height — which matters in a 14.7 mm box.

Because the pads reference the **board outline** rather than hole centres,
the one dimension still unverified (the ESP32's header row spacing — see
below) does not affect the land pattern.

## Files

| File | What |
|---|---|
| `netlist.py` | **Single source of truth** for connectivity. Parts, pin maps, nets, footprint assignments, and what is deliberately left unconnected |
| `gen_fp.py` | Emits the two module land patterns into `carrier.pretty/`, from `enclosure/boards.scad` |
| `gen_sch.py` | Emits `carrier.kicad_sch` |
| `gen_table.py` | Emits `CONNECTIONS.md` |
| `check_netlist.py` | Reads the netlist back *out* of the schematic and diffs it against `netlist.py`; also resolves every footprint and checks its pad numbers |
| `check_footprints.py` | Recomputes every pad coordinate from `boards.scad` and compares; checks each courtyard encloses its fab outline |
| `build.sh` | Runs all of it and refreshes `carrier.pdf` |

```sh
./build.sh
```

`carrier.kicad_sch`, `CONNECTIONS.md` and `carrier.pdf` are generated. Edit
`netlist.py` and rebuild; never hand-edit the schematic.

## Why the schematic is all labels and no wires

Connectivity is carried entirely by global labels. For a carrier board that is
easier to read than a rat's nest, and far easier to verify: `check_netlist.py`
re-extracts the netlist with `kicad-cli` and compares it back to the source.
Both of these deliberate breaks are caught:

- retargeting one UART label → `net U1_RX: missing [('U1', 15)]`
- deleting one ESP32 GND label → `net GND: missing [('U3', 26)]`

That check already found a real bug: `pin_table()` collapsed repeated pin
names, so the ESP32's two J4 ground pads were silently never connected.
`pad_names()` exists because of it.

KiCad 7's `kicad-cli` has no ERC subcommand (added in 8), so there is no
automated ERC here. The netlist check is stricter about connectivity anyway.

## Pin numbering

We draw both the symbol and the footprint, so the numbering is ours:

**RP2350-USB-C** — component side, **programming port (the proud one) at the top**:

- pads 1–9, left edge top to bottom: `5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9`
- pads 10–18, right edge top to bottom: `GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8`

**ESP32-DEV-KIT** — pads 1–19 are header J3, pads 20–38 are J4 (so J4 pin *n*
is our pad 19 + *n*).

## Dimensions: use what is recorded

Both modules are dimensioned by Waveshare and both sets of numbers are already
written down. **Do not ask the owner to re-measure them.**

| Board | Source | Where |
|---|---|---|
| RP2350-USB-C | Waveshare drawing, in their GitHub repo | `enclosure/boards.scad` |
| ESP32-DEV-KIT | Waveshare drawing, supplied by the owner as `ESP32-DEV-KIT-XX.pdf` | `hardware/wiring.md`, `enclosure/boards.scad` |

These carry equal authority. An earlier revision of this file asked for caliper
confirmation of the ESP32 outline while treating the RP2350 outline as settled
— the only real difference being that the RP2350 drawing can be re-opened on
demand and the ESP32 PDF cannot, because it was never committed. Not being able
to re-read a source is not the same as the number being unknown.

`esp_top_h` (4.50) and `esp_hole_dia` (2.60) are the owner's own readings, by
eye rather than calipers. Only the hole diameter is still soft, and it costs a
reprint of a plastic boss, not a PCB spin.

The header row spacing (24.94 mm) comes from the same drawing as everything
else and is taken as recorded. It does not enter an edge-soldered land pattern,
which references the board outline; re-check it only if through-holes are added.

## Land patterns

Both modules solder flat, so the pads straddle the module's **board outline**:
1.30 mm along the edge x 3.00 mm across, protruding 1.10 mm outside. The iron
reaches every joint from outside; at 2.54 mm pitch the gap between pads is
1.24 mm.

Because the land references the outline and not the hole centres, the ESP32
header row spacing never enters `gen_fp.py`.

`carrier.pretty/` is generated. Nothing in it is hand-drawn, and `fp-lib-table`
points KiCad at it. Stock KiCad 7 libraries supply the through-hole passives:
axial parts at P7.62 (leads bend to suit), disc caps at P5.08 (splaying a
2.54 mm part out is easy, squeezing a 5.08 mm one in is not), and the GP29
jumpers are the **Bridged** variant, closed by default and cut to free the pin.

Orientation, since KiCad draws +Y downward and it is easy to misread a render:

| Footprint | +Y is |
|---|---|
| `RP2350-USB-C` | the **programming** port (the proud one). -Y is the exposed port that meets the enclosure wall |
| `ESP32-DEV-KIT` | header **J3** (pads 1-19). -X is the antenna end: keep copper away |

Both checks are proven to detect faults, not merely to pass:

- nudge one RP2350 pad 0.1 mm -> `RP2350 pad 5: (-8.25, 3.46) != (-8.35, 3.46)`
- point U3 at the wrong footprint -> pad sets differ, 18 vs 38
- the courtyard check failed the pre-fix file, which did not enclose the
  programming port's 1.0 mm overhang, and passes the corrected one

## Still open before layout

| Item | State |
|---|---|
| Underside of each module | **Unknown.** Both drawings are top views. A module with parts on the bottom cannot sit flat. A glance at the real boards settles it; no measurement needed |
| ESP32 USB-C overhang | Drawn flush with the short edge. Does not affect the land pattern, only the board outline |
| Board outline | Must follow `enclosure/boards.scad`; the exposed USB-C ports have to meet the port wall |
| `ESP32-DEV-KIT-XX.pdf` | **Archive it.** The numbers are extracted, but the source should live in `docs/` so it survives. Not a blocker |

## Deliberate design choices

- **The two 3V3 rails are never tied together.** Each module has its own
  regulator. Asserted in `NO_CONNECT`.
- **Each input board reaches the rail only through its own Schottky**, so the
  two hosts' 5 V supplies are never connected.
- **`GP29` is grounded through a cuttable solder bridge**, not a hard trace,
  so a third input or an ADC can take it later.
- **`TP1`/`TP2`** exist because review-notes #18 says the rail voltage is an
  estimate that must be measured on the built box.
