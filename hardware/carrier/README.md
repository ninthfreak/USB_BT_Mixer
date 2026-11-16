# Carrier board

> **Status: KiCad DRC clean, routed, not built, not ordered.**
>
> - **Re-laid 2026-11-16.** The input boards' land pattern had been the
>   mirror image of the real board since it was first drawn. It is corrected,
>   and the build now holds the placed board against Waveshare's own pictures
>   ([`docs/project-review-2026-11.md`](../../docs/project-review-2026-11.md) #1).
> - **Before ordering, print [`carrier-fit-check.pdf`](carrier-fit-check.pdf)
>   at 100 % and lay the three real modules on it.** Every land is named; the
>   names must match the labels on the modules.
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
| Parts | U1, U2 input boards; U3 ESP32 devkit; 2 Schottky diodes; 8 resistors, all 1 kΩ (R1–R6 standing, R10/R11 lying); 1 capacitor; two 2-pin debug headers; 2 test pads |
| Nets | 20: 16 signal, 3 power (VBUS1, VBUS2, RAIL), GND |
| Rules | 0.40 mm track, 0.25 mm clearance, 0.8/0.4 mm vias, 0.5 mm copper to edge, 0.5 mm drill to drill. Loose for any fab |
| Top layer | **Every signal.** No signal changes layer: 0 signal vias |
| Bottom layer | Ground plane (91 % of the board) plus the rail only |
| Routing | Freerouting: 81 signal segments; the rail, ground stubs and three short links by hand; 568 mm of track; 5 vias, all ground |
| Joints to solder | 36 of 70 module lands, plus the passives |

## How the board is laid out

The rules, so it reads the way it works (owner, 2026-10-27):

- **Top layer: signals.** Every signal stays on top from end to end.
- **Bottom layer: ground and power.** A solid ground plane. The rail is the
  only track on it: from input 2's diode across the front, **in front of
  input 1's ground pad**, then down the left edge to the ESP32's 5V pad. No
  signal runs along it, and every module's ground via lands in the one main
  plane (review #2).
- **Related lines run together.** Each board's I2S lines and its UART pair
  travel as groups.

Each module lies exactly as in its picture in `docs/sources/`:

| Module | As placed | Picture |
|---|---|---|
| Input boards | **Native USB port at the front**, hanging 1 mm past the edge. 5V is the front-left pad. Power and I2S run down the **left** edge, UART and debug down the **right**. The PIO-USB port faces inward, unused | `rp2350-usb-c-pinout.png` |
| ESP32 | USB-C end 1 mm past the **left** edge, antenna past the notch on the **right**. The row facing the input boards is J3: 5V at the left … 3V3 at the antenna end | `esp32-dev-kit-drawing.png` |

Seen from the ESP32's front row, west to east:

| ESP32 pin | Carries | Goes to |
|---|---|---|
| IO13 | Input 1 audio | Down the left margin from input 1's left edge |
| IO14, IO26 | LRCK out, BCLK out, through R3 and R1 | Under input 1 to its left edge |
| IO25, IO33 | Input 1's UART (TX through R5, RX) | Up the channel to input 1's right edge |
| IO32, IO35 | BCLK in, LRCK in (the loop-backs), and on through R2 and R4 | To input 2's left edge |
| gaps east of IO35 | Input 2's audio, TX, and RX (through R6) | Under the ESP32 to IO18, IO19, IO21 on its rear row |

The clocks' output pins face input 1 and their loop-back pins face input 2,
so the two links under the ESP32 **nest instead of crossing**, and input 1's
UART ends on the two pads between them. Three lines pass between the pads of
a standing resistor (BCLK to input 1 under R3; input 2's audio under R2 and
R4). That is the only "crossing" on the board, and it is why no signal needs
the bottom layer.

| Where | What |
|---|---|
| Left margin | Input 1's diode D1 and bleed R10 at its 5V pad; the rail (bottom); test points; rail bulk C1 at the ESP32's 5V pad |
| Channel between the boards | Input 2's diode D2 and bleed R11 at its 5V pad; input 1's debug header J1; input 1's UART lanes |
| Strip in front of the ESP32 | R3, R1, R5, R2, R4, R6 standing in a row, each at the pin or gap it serves |
| Right margin | Input 2's debug header J2 |

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
KiCad 7's `pcbnew` bindings. Every step must pass.

The build does **not** run Freerouting: its output varies from run to run.
It lays the committed result, `carrier.ses`. If the placement or netlist has
changed since that route was made, `route.py` stops and says to reroute.
Rerouting downloads Freerouting 2.1.0 once (SHA-256 checked, analytics off)
and needs Java 17 or later; it takes a few seconds. Whether a route is
complete is decided by KiCad's connectivity, not by Freerouting's own count.

`carrier.kicad_sch`, `carrier.kicad_pcb`, `carrier.pretty/`,
`CONNECTIONS.md` and the PDFs are generated. Edit `netlist.py` (connectivity),
`gen_pcb.py` (placement) or `route.py` (hand-laid copper) and rebuild. Never
hand-edit the outputs.

## Files

| File | What |
|---|---|
| `netlist.py` | **Single source of truth** for connectivity: parts, pin maps, nets, footprints, and what is deliberately unconnected |
| `gen_fp.py` | The two module land patterns, from `enclosure/boards.scad`, each drawn as its picture |
| `gen_sch.py` | `carrier.kicad_sch` |
| `gen_table.py` | `CONNECTIONS.md`: every net, and which pads to solder |
| `gen_pcb.py` | `carrier.kicad_pcb`, built with pcbnew: outline, placement, pad nets, schematic links, labels, the ground pour |
| `route.py` | Lays the rail, ground stubs and three links by hand, every other signal from `carrier.ses`; `--reroute` runs Freerouting to make a new one |
| `specctra.py` | Design export edits and session import between KiCad and Freerouting |
| `carrier.ses`, `carrier-route.json` | The committed route, and the hash of the design it was made for |
| `drc.py` | **The gate.** KiCad's own DRC with this board's rules, plus every pad's net against `netlist.py` |
| `check_footprints.py` | Recomputes every pad coordinate from `boards.scad` |
| `check_netlist.py` | Reads the netlist back out of the schematic and diffs it; checks diode and capacitor polarity against the footprint's own markings |
| `check_pcb.py` | **Each module lies as in its picture, not mirrored**; native USB ports over the front edge; ESP32 overhangs at both ends; hole webs |
| `check_routing.py` | Routed intent: power widths, I2S chain lengths, bottom pour coverage, every signal on top, and a ground path at least 2 mm wide from each input board to the ESP32 |
| `fit_check.py` | `carrier-fit-check.pdf`: the board at 1:1 with every module pad named, to print and lay the real modules on. Also the soldering map |
| `AUDIT.md` | The 2026-10-26 audit and what was done about each finding |

## How it is verified

KiCad's DRC (`pcbnew.WriteDRCReport`) is the authority: clearances,
connectivity including the pour, courtyards, holes, silkscreen, keep-outs.

The custom checks cover what DRC cannot know: design intent. Each one has
been shown to **fail** on a deliberately broken board, not only to pass:

| Break | Caught by | Result |
|---|---|---|
| Input boards' pattern mirrored (pads 1–9 on the right: **the bug this board had**) | `check_pcb.py` | every corner pad listed: "the picture has it west/front, the board has it east/front" |
| Input 1 turned half a turn | `check_pcb.py` | corners listed; no proud shell at the front |
| ESP32's two rows swapped | `check_pcb.py` | 5V, IO36, CLK, IO22 listed |
| Diode pins mapped A=1 (the 2026-10 bug) | `check_netlist.py` | polarity failures |
| Delete a track | `drc.py` | unconnected, dangling |
| Empty the GND pour | `drc.py` | many unconnected |
| Track 0.3 mm from the edge | `drc.py` | edge clearance |
| Power traces at 0.4 mm | `check_routing.py` | every thin segment listed |
| A signal track on the bottom, a via on a signal | `check_routing.py` | both listed |
| Rail run behind the input boards' ground pads (DRC still clean, 89 % fill) | `check_routing.py` | ground path narrower than 2 mm, all four pairs listed |
| ESP32 USB-C end flush (no overhang) | `check_pcb.py` | fails |
| Antenna overhang 3 mm | `check_pcb.py` | fails |
| R10 moved 1 mm, old route laid | `route.py` | refuses: "routed for a different placement" |

**What no check here can do** is confirm the pictures match the boards in
your hand. That is what the paper fit check is for.

One KiCad behaviour worth knowing when testing: saving a board reassigns a
track that is not connected to its own net to whatever copper it touches (in
practice, the ground pour). A test track must therefore join two pads of its
net. DRC still catches the missing connection a reassigned track leaves.

`drc-report.txt` holds the last report. Its only entries are
"library not in this configuration" notes: the container has no global KiCad
library table. They say nothing about the copper.

## Pin numbering

We draw both the symbol and the footprint, so the numbering is ours. Each is
defined against a picture, because "left" means nothing without one.

**RP2350-USB-C** — `docs/sources/rp2350-usb-c-pinout.png`: component side
up, native USB port (beside BOOT and RST) at the top:

- pads 1–9, **left** edge top to bottom: `5V GND 3V3 GP29 GP28 GP27 GP26 GP10 GP9`
- pads 10–18, **right** edge top to bottom: `GP0 GP1 GP2 GP3 GP4 GP5 GP6 GP7 GP8`

**ESP32-DEV-KIT** — `docs/sources/esp32-dev-kit-drawing.png`: component side
up, USB-C left, antenna right:

- pads 1–19 are header J3, the **top** row, numbered from the antenna end:
  pad 1 = 3V3 (right) … pad 19 = 5V (left)
- pads 20–38 are J4, the **bottom** row, also from the antenna end (so J4 pin
  *n* is our pad 19 + *n*): pad 20 = GND … pad 38 = CLK
- pads 1, 2, 20 and 21 have no land: they sit past the notch.

## Land patterns

Both modules are castellated, so they solder flat with the iron on the
**outside** of every joint: visible, inspectable, reworkable, no reflow.

Each pad is 1.30 mm along the edge × 3.00 mm across, sticking out 1.10 mm past
the module outline. At 2.54 mm pitch that leaves 1.24 mm between pads. The
pads reference the board **outline**, so the ESP32's header row spacing never
enters the footprint.

Each footprint is drawn as its picture looks in KiCad's footprint editor,
where +Y points **down**:

| Footprint | Drawn | Placed |
|---|---|---|
| `RP2350-USB-C` | Native USB port at the top (−Y), 5V top-left | Unrotated |
| `ESP32-DEV-KIT` | The drawing turned half a turn: antenna left (−X), J3 at the bottom (+Y) | Turned 180°, which makes it the drawing again |

Passives use stock KiCad footprints: DO-41 diodes and the two bleed resistors
at 7.62 mm, the six series resistors standing at 2.54 mm, the bulk cap radial
at 2.50 mm.

## Dimensions: use what is recorded

Both modules are dimensioned by Waveshare drawings, already written down in
`enclosure/boards.scad`, with the pictures in `docs/sources/`. **Do not ask
the owner to re-measure them.** Both modules are flat underneath (owner,
boards in hand).

## Soldering: not every pad

Solder only the pads that carry a net, plus a few corners so nothing can peel.
**36 joints instead of 70.** `CONNECTIONS.md` has the per-pad map and
`carrier-fit-check.pdf` shows it at 1:1. `check_netlist.py` asserts every
mechanical pad floats; several are the ESP32's flash and strapping pins, and
tying those to live copper would be worse than leaving them bare.

Suggested order: the three modules first, while the board lies flat and
every pad is easy to reach; then the through-hole parts, soldered from
underneath.

The full land pattern is still made, so any pad can be soldered later.

### Plug forces

Each input board's first pads are 2.88 mm from its native USB-C shell, and
the soldered 5V, GND and GP0 joints sit at that end. They take some of a
cable's peel moment, but solder is still the wrong thing to rely on: whatever
enclosure holds the carrier should bear on the modules near the port.

## Programming with everything soldered

- **Input boards:** through the front USB-C port (native USB). First flash:
  hold BOOT while plugging in and copy the UF2. BOOT is on the board's top
  face, beside that port (Waveshare's picture). After that, firmware can
  reboot into its bootloader on command.
- **ESP32:** through its own USB-C, hanging past the left edge; no buttons
  needed, and the box can stay powered.

Details: `hardware/wiring.md`, "Programming with everything soldered".

## Deliberate design choices

- **The two 3V3 rails are never tied together.** Each module has its own
  regulator. Asserted in `NO_CONNECT`.
- **Each input board reaches the rail only through its own Schottky**, so the
  two hosts' 5 V supplies never meet.
- **A 1 kΩ bleed on each input board's VBUS** (R10, R11). An input board with
  no host is fed its diode's reverse leakage from the rail; a USB-C host will
  not switch a port on until VBUS is below 0.8 V.
- **The clocks go to GP9 and GP10, the UART to GP5**: fault-tolerant pads,
  which pass almost no current when their board is unpowered. GP26–GP29 (the
  ADC pads, which have a diode to that board's 3V3 rail) take no signal from
  the ESP32.
- **1 kΩ in series with every line the ESP32 drives into an input board**
  (BCLK, LRCK, UART TX): edge-rate control beside the radio, and a limit if a
  pin is ever turned the wrong way round.
- **Never IO36/IO39** for I2S: they glitch when the ADC powers up (Espressif
  erratum; reported during A2DP streaming). The loop-backs are IO26→IO32 and
  IO14→IO35.
- **Both audio inputs (IO13, IO18) have an internal pull-down** for firmware
  to switch on, so a board with no host contributes silence.
- **TP1/TP2** (rail and ground, 3 mm apart in the left margin) because the
  rail voltage is an estimate that must be measured on the built box
  (review-notes #18).

Retired 2026-11-16 as not needed (review #5): R7 (AUD2 pull-down), R8/R9
(GP29 pull-downs), C2–C4 (0.1 µF bypasses). The designators are not reused.

## Still open

| Item | State |
|---|---|
| **Paper fit check** | **Not done.** Print `carrier-fit-check.pdf` at 100 %; the names must match the modules' own labels |
| Antenna clearance, front side | **Accepted as is** (owner). If Bluetooth range disappoints, option C in [AUDIT.md #21](AUDIT.md#21-antenna-clearance-on-the-front-side-new) is the fix |
| I2S loop-back and UART relay | **Untested** in hardware. Bench test before ordering (recommended) |
| Bleed and back-feed | Two five-minute multimeter tests settle them (review #3, #4) |
| Enclosure for the carrier | Not designed. Its port wall must take the native port's **proud** shell; the left wall needs an opening (or a removable plug) at the ESP32's USB-C; the carrier needs standoffs because through-hole leads protrude underneath; C1 and the standing resistors set the height |
| Native-USB shell overhang | 1.00 mm assumed (`usb_over_in`); worth a caliper check before the enclosure |
| ESP32 sources | The dimensioned drawing is archived. The schematic PDF is still not in the repo. Not a blocker |
