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
| Parts | U1, U2 input boards; U3 ESP32 devkit; 2 Schottky diodes; 9 resistors (R1, R3 standing); 4 capacitors; 3-pin debug header; 2 test pads |
| Nets | 22: 18 signal, 3 power (VBUS1, VBUS2, RAIL), GND |
| Rules | 0.40 mm track, 0.25 mm clearance, 0.8/0.4 mm vias, 0.5 mm copper to edge, 0.5 mm drill to drill. Loose for any fab |
| Top layer | **Every signal.** No signal changes layer: 0 signal vias |
| Bottom layer | Ground plane (89 % of the board) plus power only |
| Routing | Freerouting: 108 signal segments; rail and ground stubs by hand; 754 mm of track; 4 vias, all ground |
| Joints to solder | 40 of 70 module lands, plus the passives |

## How the board is laid out

The rules, so it reads the way it works (owner, 2026-10-27):

- **Top layer: signals.** Every signal stays on top from end to end.
- **Bottom layer: ground and power.** A solid ground plane. The rail is the
  only long track on it, running round the front and left edges behind the
  input boards' port ends, where no signal crosses it.
- **Related lines run together.** Each board's three I2S lines and its UART
  pair travel as groups.

Each input board is **turned so its native USB port faces the hosts** (the
"programming" port, whose shell hangs 1 mm past the front edge). Its PIO-USB
port faces inward, unused. See review-notes #25.

Seen from the ESP32, west to east, the board carries input 1's UART pair,
input 1's I2S group, input 2's UART pair, input 2's I2S group. The ESP32 pins
are chosen in that order (`netlist.py`). The shared clocks reach input 2 by
passing **between the pads of R2 and R4**, which lie across input 2's UART
pair, so no signal needs the bottom layer.

| Where | What |
|---|---|
| Left margin | The rail (bottom), test points |
| Strip behind input 1 | Rail bulk and bypass at the ESP32's 5V pad; input 1's clock resistors R1, R3, standing on their lanes |
| Channel between the boards | Input 1's diode, bypass and GP29 pull-down at its power pads; debug header J1; input 2's RX resistor R6 on its lane |
| Strip behind input 2 | Input 2's clock resistors R2, R4, lying across its UART pair; its GP29 and audio pull-downs |
| Right margin | Input 2's diode and bypass at its power pads |
| Behind the ESP32 | Input 1's RX resistor R5, at the ESP32's TX pin |

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
./build.sh                          # regenerate and check everything
/usr/bin/python3 route.py --reroute # only after moving parts or changing nets
```

Everything runs under the **system** python (`/usr/bin/python3`), which has
KiCad 7's `pcbnew` bindings. Every step must pass. The output is
byte-identical across rebuilds, so a diff means something really changed.

The build does **not** run Freerouting: its output varies from run to run.
It lays the committed result, `carrier.ses`. If the placement or netlist has
changed since that route was made, `route.py` stops and says to reroute.
Rerouting downloads Freerouting 2.1.0 once (SHA-256 checked, analytics off)
and needs Java 17 or later; it takes about 10 seconds.

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
| `gen_pcb.py` | `carrier.kicad_pcb`, built with pcbnew: outline, placement, pad nets, schematic links, labels, the ground pour |
| `route.py` | Lays the rail and ground stubs by hand, every signal from `carrier.ses`; `--reroute` runs Freerouting to make a new one |
| `specctra.py` | Design export edits and session import between KiCad and Freerouting |
| `carrier.ses`, `carrier-route.json` | The committed route, and the hash of the design it was made for |
| `drc.py` | **The gate.** KiCad's own DRC with this board's rules, plus every pad's net against `netlist.py` |
| `check_footprints.py` | Recomputes every pad coordinate from `boards.scad` |
| `check_netlist.py` | Reads the netlist back out of the schematic and diffs it; checks diode and capacitor polarity against the footprint's own markings |
| `check_pcb.py` | Mechanical intent: native USB ports over the front edge, ESP32 overhangs at both ends, hole webs |
| `check_routing.py` | Routed intent: power widths, I2S chain lengths, bottom pour coverage, every signal on top |
| `AUDIT.md` | The 2026-10-26 audit and what was done about each finding |

## How it is verified

KiCad's DRC (`pcbnew.WriteDRCReport`) is the authority: clearances,
connectivity including the pour, courtyards, holes, silkscreen, keep-outs.
KiCad 7's `kicad-cli` has no DRC command, which for a while was taken to mean
no DRC was available. It was, through the Python bindings.

The custom checks cover what DRC cannot know: design intent. Each one has
been shown to **fail** on a deliberately broken board, not only to pass:

| Break | Caught by | Result |
|---|---|---|
| Diode pins mapped A=1 (the original bug) | `check_netlist.py` | 4 polarity failures |
| Delete the longest BCLK1 track | `drc.py` | 1 unconnected, 2 dangling |
| Empty the GND pour | `drc.py` | many unconnected |
| Drop a GND via onto an LRCK track | `drc.py` | clearance and hole errors |
| Track 0.3 mm from the edge | `drc.py` | edge clearance |
| Power traces at 0.4 mm | `check_routing.py` | every thin RAIL segment listed |
| A BCLK track on the bottom, a via on BCLK1 | `check_routing.py` | both listed |
| ESP32 USB-C end flush (no overhang) | `check_pcb.py` | fails |
| Antenna overhang 3 mm | `check_pcb.py` | fails |
| Input 1 turned back to 0° (PIO-USB to the hosts) | `check_pcb.py` | fails |
| R8 moved 1 mm, old route laid | `route.py` | refuses: "routed for a different placement" |

One KiCad behaviour worth knowing when testing: saving a board reassigns a
track that is not connected to its own net to whatever copper it touches (in
practice, the ground pour). A test track must therefore join two pads of its
net. DRC still catches the missing connection a reassigned track leaves.

`drc-report.txt` holds the last report. Its only entries are
"library not in this configuration" notes: the container has no global KiCad
library table. They say nothing about the copper.

## Pin numbering

We draw both the symbol and the footprint, so the numbering is ours.

**RP2350-USB-C** — component side, native ("programming") port at the top:

- pads 1–9, left edge top to bottom: `5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9`
- pads 10–18, right edge top to bottom: `GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8`

On the carrier each input board is turned 180°, so the native port faces the
front edge, power and I2S are on the board's right-hand edge and UART/debug
on its left.

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
| `RP2350-USB-C` | the **native USB** ("programming") port, proud of the edge. Placed at 180°, so +Y faces the front edge |
| `ESP32-DEV-KIT` | header **J3** (pads 1–19). −X is the antenna end |

Passives use stock KiCad footprints: axial resistors and DO-41 diodes at
7.62 mm, R1 and R3 standing at 2.54 mm, disc caps at 5.00 mm, the bulk cap
radial at 2.50 mm.

## Dimensions: use what is recorded

Both modules are dimensioned by Waveshare drawings, already written down in
`enclosure/boards.scad`. **Do not ask the owner to re-measure them.** Both
modules are flat underneath (owner, boards in hand).

## Soldering: not every pad

Solder only the pads that carry a net, plus a few corners so nothing can peel.
**40 joints instead of 70.** `CONNECTIONS.md` has the per-pad map.
`check_netlist.py` asserts every mechanical pad floats; several are the
ESP32's flash and strapping pins, and tying those to live copper would be
worse than leaving them bare.

The full land pattern is still made, so any pad can be soldered later.

### Plug forces

With the native port at the front, each input board's first pads are 2.88 mm
from its USB-C shell, and the soldered 5V, GND and GP0 joints sit at that
end. They take some of a cable's peel moment, but solder is still the wrong
thing to rely on: whatever enclosure holds the carrier should bear on the
modules near the port.

## Programming with everything soldered

- **Input boards:** through the front USB-C port (native USB). First flash:
  hold BOOT while plugging in and copy the UF2. BOOT is on the board's top
  face. After that, firmware can reboot into its bootloader on command.
- **ESP32:** through its own USB-C, hanging past the left edge; no buttons
  needed, and the box can stay powered.

Details: `hardware/wiring.md`, "Programming with everything soldered".

## Deliberate design choices

- **The two 3V3 rails are never tied together.** Each module has its own
  regulator. Asserted in `NO_CONNECT`.
- **Each input board reaches the rail only through its own Schottky**, so the
  two hosts' 5 V supplies never meet.
- **1 kΩ in series with every line the ESP32 drives into an input board**
  (BCLK, LRCK, UART TX). With one host connected, the other input board is
  unpowered; this keeps injection to ~3 mA per pin.
- **Never IO36/IO39** for I2S: they glitch when the ADC powers up (Espressif
  erratum; reported during A2DP streaming). The loop-backs are IO26→IO25 and
  IO14→IO33.
- **GP29 pulled down through 4.7 kΩ** (R8/R9), not a solder bridge. Leave the
  resistor out to free the pin.
- **100 kΩ pull-down on AUD2**: GPIO35 has no internal pull and would float
  with input 2 absent. AUD1 (GPIO13) uses its internal pull-down.
- **TP1/TP2** (rail and ground, 3 mm apart in the left margin) because the
  rail voltage is an estimate that must be measured on the built box
  (review-notes #18).

## Still open

| Item | State |
|---|---|
| Antenna clearance, front side | **Accepted as is** (owner). If Bluetooth range disappoints, option C in [AUDIT.md #21](AUDIT.md#21-antenna-clearance-on-the-front-side-new) is the fix |
| I2S loop-back and UART relay | **Untested** in hardware. Bench test before ordering (recommended) |
| Enclosure for the carrier | Not designed. Its port wall must take the native port's **proud** shell (the old box expected a flush one); the carrier needs standoffs because through-hole leads protrude underneath |
| Native-USB shell overhang | 1.00 mm assumed (`usb_over_in`); worth a caliper check before the enclosure |
| ESP32 sources | The dimensioned drawing is archived (`docs/sources/esp32-dev-kit-drawing.png`). The schematic PDF is still not in the repo. Not a blocker |
