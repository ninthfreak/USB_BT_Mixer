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
| `netlist.py` | **Single source of truth.** Parts, pin maps, nets, and what is deliberately left unconnected |
| `gen_sch.py` | Emits `carrier.kicad_sch` from it |
| `gen_table.py` | Emits `CONNECTIONS.md` from it |
| `check_netlist.py` | Reads the netlist back *out* of the schematic and diffs it against `netlist.py` |
| `build.sh` | Runs all four and refreshes `carrier.pdf` |

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

## Still open before layout

| Item | State |
|---|---|
| ESP32 board width and length | 27.94 × 53.80 from the drawing, ~90%. **Confirm with calipers** |
| ESP32 header row spacing | Unknown (24.94 vs 25.40). Irrelevant for edge-soldered pads; matters only if through-holes are added |
| `ESP32-DEV-KIT-XX.pdf` | Not in this repo. It was attached in chat and lost. Commit it to `docs/` when re-supplied |
| Footprints | None drawn yet |
| Board outline | Must follow `enclosure/boards.scad`; the exposed USB-C ports have to meet the port wall |

## Deliberate design choices

- **The two 3V3 rails are never tied together.** Each module has its own
  regulator. Asserted in `NO_CONNECT`.
- **Each input board reaches the rail only through its own Schottky**, so the
  two hosts' 5 V supplies are never connected.
- **`GP29` is grounded through a cuttable solder bridge**, not a hard trace,
  so a third input or an ADC can take it later.
- **`TP1`/`TP2`** exist because review-notes #18 says the rail voltage is an
  estimate that must be measured on the built box.
