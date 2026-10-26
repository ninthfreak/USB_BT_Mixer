# Carrier board

> **Status: KiCad DRC clean, routed, not built, not ordered.**
>
> - **Antenna clearance: accepted as is** (owner, 2026-10-26). Copper is
>   6.55 mm in front of the antenna against Espressif's 15 mm; the antenna
>   itself hangs fully past the board edge
>   ([`AUDIT.md` #21](AUDIT.md#21-antenna-clearance-on-the-front-side-new)).
> - Recommendation before ordering: **the two-I2S clock loop-back is still
>   untested.** A jumper-wire bench test of one input board + the ESP32 would
>   prove it for the price of an afternoon.

One flat PCB that the three modules solder onto, replacing the hand-wired
loom. All passives are through-hole and live on it.

## At a glance

| | |
|---|---|
| Size | 70.0 × 79.6 mm, L-shaped (see below), 2 layers, 1.6 mm |
| Parts | U1, U2 input boards; U3 ESP32 devkit; 2 Schottky diodes; 9 resistors; 4 capacitors; 1 six-pin header; 2 test pads |
| Nets | 25 (24 signal + GND) |
| Rules | 0.40 mm track, 0.25 mm clearance, 0.8/0.4 mm vias, 0.5 mm copper to edge, 0.5 mm drill to drill. Loose for any fab |
| Power traces | VBUS1, VBUS2, RAIL at 0.8 mm |
| Ground | Pour on both layers, 56 stitching vias. Bottom pour covers 87 % of the board |
| Routing | 199 track segments, 59 vias, 934 mm of track. Signals mostly on top |
| Joints to solder | 43 of 70 module lands, plus the passives |

## Why it is an L, not a rectangle

The front must be 70 mm wide for the two input boards side by side. The ESP32
devkit sits across the back, its USB-C end hanging 1 mm past the left edge so
a flashing cable fits. That puts the antenna at the right.

Espressif's first choice is an antenna **outside** the base board, with any
board under it cut away. So the back-right corner is cut off and the
devkit's antenna end hangs 7.5 mm into free air. An L costs nothing extra:
fabs price by the bounding box.

The catch is the antenna's front side, where the front-right block comes
close: 6.55 mm, where Espressif asks for 15. The owner accepted that rather
than make the board ~8.5 mm deeper ([AUDIT.md #21](AUDIT.md#21-antenna-clearance-on-the-front-side-new)).

## Build

```sh
./build.sh
```

Everything runs under the **system** python (`/usr/bin/python3`), which has
KiCad 7's `pcbnew` bindings. Every step must pass. The output is
byte-identical across rebuilds, so a diff means something really changed.

`carrier.kicad_sch`, `carrier.kicad_pcb`, `carrier.pretty/`,
`CONNECTIONS.md` and the PDFs are generated. Edit `netlist.py` (connectivity)
or `gen_pcb.py` (placement) and rebuild. Never hand-edit the outputs.

## Files

| File | What |
|---|---|
| `netlist.py` | **Single source of truth** for connectivity: parts, pin maps, nets, footprints, and what is deliberately unconnected |
| `gen_fp.py` | The two module land patterns, from `enclosure/boards.scad` |
| `gen_sch.py` | `carrier.kicad_sch` |
| `gen_table.py` | `CONNECTIONS.md`: every net, and which pads to solder |
| `gen_pcb.py` | `carrier.kicad_pcb`, built with pcbnew: outline, placement, pad nets, schematic links, labels, pour zones |
| `route.py` | Two-layer grid router (A*), then KiCad fills the pours |
| `drc.py` | **The gate.** KiCad's own DRC with this board's rules, plus every pad's net against `netlist.py` |
| `check_footprints.py` | Recomputes every pad coordinate from `boards.scad` |
| `check_netlist.py` | Reads the netlist back out of the schematic and diffs it; checks diode and capacitor polarity against the footprint's own markings |
| `check_pcb.py` | Mechanical intent: ports on the front edge, ESP32 overhangs at both ends, hole webs |
| `check_routing.py` | Routed intent: power widths, I2S chain lengths, bottom pour coverage, stitching |
| `AUDIT.md` | The 2026-10-26 audit and what was done about each finding |

## How it is verified

KiCad's DRC (`pcbnew.WriteDRCReport`) is the authority: clearances,
connectivity including the pours, courtyards, holes, silkscreen, keep-outs.
KiCad 7's `kicad-cli` has no DRC command, which for a while was taken to mean
no DRC was available. It was, through the Python bindings.

The custom checks cover what DRC cannot know: design intent. Each one has
been shown to **fail** on a deliberately broken board, not only to pass:

| Break | Caught by | Result |
|---|---|---|
| Diode pins mapped A=1 (the original bug) | `check_netlist.py` | 4 polarity failures |
| Delete the longest BCLK1 track | `drc.py` | 1 unconnected, 2 dangling |
| Empty both GND pours | `drc.py` | 66 unconnected |
| Drop a GND via onto an LRCK track | `drc.py` | clearance and hole errors |
| Track 0.3 mm from the edge | `drc.py` | edge clearance |
| Router with no grid margin, 0.15 mm clearance | `drc.py` | 152 clearance errors |
| Power traces at 0.4 mm | `check_routing.py` | every thin RAIL segment listed |
| ESP32 USB-C end flush (no overhang) | `check_pcb.py` | fails |
| Antenna overhang 3 mm | `check_pcb.py` | fails |

`drc-report.txt` holds the last report. Its only entries are 22
"library not in this configuration" notes: the container has no global KiCad
library table. They say nothing about the copper.

## Pin numbering

We draw both the symbol and the footprint, so the numbering is ours.

**RP2350-USB-C** — component side, programming port (the proud one) at the top:

- pads 1–9, left edge top to bottom: `5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9`
- pads 10–18, right edge top to bottom: `GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8`

**ESP32-DEV-KIT** — pads 1–19 are header J3, pads 20–38 are J4 (so J4 pin *n*
is our pad 19 + *n*). Pads 1, 2, 20 and 21 have no land: they sit under the
antenna overhang.

## Land patterns

Both modules are castellated, so they solder flat with the iron on the
**outside** of every joint: visible, inspectable, reworkable, no reflow.

Each pad is 1.30 mm along the edge × 3.00 mm across, sticking out 1.10 mm past
the module outline. At 2.54 mm pitch that leaves 1.24 mm between pads. The
pads reference the board **outline**, so the ESP32's header row spacing never
enters the footprint.

| Footprint | +Y is |
|---|---|
| `RP2350-USB-C` | the **programming** port. −Y is the exposed port at the front edge |
| `ESP32-DEV-KIT` | header **J3** (pads 1–19). −X is the antenna end |

Passives use stock KiCad footprints: axial resistors and DO-41 diodes at
7.62 mm, disc caps at 5.00 mm, the bulk cap radial at 2.50 mm.

## Dimensions: use what is recorded

Both modules are dimensioned by Waveshare drawings, already written down in
`enclosure/boards.scad`. **Do not ask the owner to re-measure them.** Both
modules are flat underneath (owner, boards in hand).

## Soldering: not every pad

Solder only the pads that carry a net, plus a few corners so nothing can peel.
**43 joints instead of 70.** `CONNECTIONS.md` has the per-pad map.
`check_netlist.py` asserts every mechanical pad floats; several are the
ESP32's flash and strapping pins, and tying those to live copper would be
worse than leaving them bare.

The full land pattern is still made, so any pad can be soldered later.

### Plug forces are not held by solder

Each input board's pads stop **9.8 mm short of its USB-C shell**. Pulling a
cable applies a peel moment that solder was never taking. Whatever enclosure
holds the carrier must bear on the modules near the port, as the current
lid's press posts do.

## Deliberate design choices

- **The two 3V3 rails are never tied together.** Each module has its own
  regulator. Asserted in `NO_CONNECT`.
- **Each input board reaches the rail only through its own Schottky**, so the
  two hosts' 5 V supplies never meet.
- **1 kΩ in series with every line the ESP32 drives into an input board**
  (BCLK, LRCK, UART TX). With one host connected, the other input board is
  unpowered; this keeps injection to ~3 mA per pin.
- **Clock loop-backs on IO13 and IO32**, not IO36/IO39, which glitch when the
  ADC powers up (Espressif erratum; reported during A2DP streaming).
- **GP29 pulled down through 4.7 kΩ** (R8/R9), not a solder bridge. Leave the
  resistor out to free the pin.
- **100 kΩ pull-down on AUD1**: GPIO35 has no internal pull and would float
  with input 1 absent.
- **TP1/TP2** (rail and ground, 3.8 mm apart) because the rail voltage is an
  estimate that must be measured on the built box (review-notes #18).

## Still open

| Item | State |
|---|---|
| Antenna clearance, front side | **Accepted as is** (owner). If Bluetooth range disappoints, option C in [AUDIT.md #21](AUDIT.md#21-antenna-clearance-on-the-front-side-new) is the fix |
| Where the antenna sits on the devkit | **Settled** from Waveshare's drawing: 18.00 mm across, centred, 6.35–6.80 mm deep (`esp_ant_w`, `esp_ant_l` in `boards.scad`) |
| I2S loop-back and UART relay | **Untested** in hardware. Bench test before ordering (recommended) |
| Enclosure for the carrier | Not designed. The carrier needs standoffs: through-hole leads protrude underneath |
| ESP32 sources | The dimensioned drawing is archived (`docs/sources/esp32-dev-kit-drawing.png`). The schematic PDF is still not in the repo. Not a blocker |
