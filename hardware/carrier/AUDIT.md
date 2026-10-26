# Carrier board audit — 2026-10-26

## Status after the fix pass (same day)

All 20 findings below were worked through in the suggested order. KiCad's own
DRC is now clean on the routed board and is the gate in `build.sh`.
**One new item (#21) was found; the owner accepted the layout as is.**

| # | Finding | Now | Verified by |
|---|---|---|---|
| 1 | Diodes reversed | **Fixed.** `"d": {"K": 1, "A": 2}`; symbol redrawn | `check_netlist.py` polarity check: the old mapping fails it 4 ways |
| 2 | Nine open connections | **Fixed.** Router rewritten on pcbnew with real pad shapes; THT pads on both layers | DRC: 0 unconnected. Removing one track makes it fail |
| 3 | Back-feed into the unpowered board | **Fixed** (resistor option). R1–R4 now 1 kΩ; R5/R6 1 kΩ in each UART TX | Netlist; CONNECTIONS.md |
| 4 | Loop-backs on GPIO36/39 | **Fixed.** BCLK loops to IO13, LRCK to IO32. IO36/39 declared no-connect | `check_netlist.py` (they must float) |
| 5 | Drill spacing | **Fixed.** ESP32 NPTH removed; router keeps 0.5 mm drill to drill | DRC with `hole_to_hole` 0.5 mm |
| 6 | Copper under the antenna | **Improved, see #21.** Antenna end overhangs a notch by 7.5 mm; 4 ESP32 pads (3V3, EN, a GND, IO23) have no land | `check_pcb.py` (overhang ≥ 6 mm); DRC rule area |
| 7 | No pad nets / schematic link | **Fixed.** `gen_pcb.py` now builds the board with pcbnew: 72/72 pads netted, 21/21 linked, library IDs set | `drc.py` compares every pad's net with `netlist.py` |
| 8 | No ground plane | **Fixed.** GND pour on both layers, 56 stitching vias. Bottom pour covers 87 % of the board | `check_routing.py` (≥ 80 %, ≥ 20 vias) |
| 9 | ESP32 USB-C cable fouls the carrier | **Fixed.** That end overhangs the left edge by 1 mm | `check_pcb.py` (≥ 0.5 mm) |
| 10 | Stale placement | **Fixed.** Re-placed: D2 9.0 mm and C4 4.5 mm from U2's 5V pad (were 27 and 24); GP29 pull-downs beside their pins | Render; pad coordinates |
| 11 | Hole webs 0.5 mm | **Fixed.** 1.61–1.65 mm | `check_pcb.py` (≥ 1.5 mm) |
| 12 | Courtyards touching | **Fixed** | DRC courtyard test |
| 13 | GPIO35 floats | **Fixed.** R7 100 kΩ pull-down | Netlist |
| 14 | All traces 0.4 mm | **Fixed.** VBUS1/2 and RAIL 0.8 mm | `check_routing.py` |
| 15 | Many vias, untidy | **Better.** Tracks string-pulled (any angle); 59 routing vias. Still machine-routed | Render |
| 16 | Silkscreen | **Fixed.** Labels for inputs, RAIL/GND, J1 pins, version | DRC silk tests |
| 17 | GP29 hard-shorted | **Fixed.** 4.7 kΩ pull-downs R8/R9 (fit or omit) | Netlist |
| 18 | Test points 57 mm apart | **Fixed.** 3.8 mm apart | Placement |
| 19 | Leads protrude underneath | Unchanged: inherent to THT. Mount on standoffs | — |
| 20 | Hosts' grounds tied | Unchanged: inherent, benign | — |
| **21** | **Antenna clearance on its front side** | **Accepted as is** (owner, option A) | Board file + antenna position from Waveshare's drawing |

### 21. Antenna clearance on the front side (new)

The notch clears the antenna behind it and to its right. In front, the
carrier's front-right block (U2, J1, GND pour) ends **1.15 mm** from the
devkit's front edge.

Antenna position, from Waveshare's drawing with the owner's markup
(`docs/sources/esp32-dev-kit-drawing.png`): **18.00 mm** across, centred
(dimensioned), reaching **6.35–6.80 mm** in from the end edge (measured off
the drawing at 11.02 px/mm). So the 7.5 mm overhang puts the whole antenna in
free air with 0.7–1.15 mm to spare.

Measured from the board file, the nearest carrier copper is:

| Where | Distance | Comment |
|---|---|---|
| In front of the antenna (front-right block's GND pour) | **6.55 mm** | The problem: guideline is 15 mm |
| Behind its inner end (pour beyond the 2.3 mm keep-out strip) | 3.0 mm | Expected: this is the feed end, beside the module's own ground |

Espressif's guidance: put the antenna outside the base board; where it cannot
be, keep **15 mm** clear around it with no copper, tracks or parts. So the
current layout meets the first half and not the second.

| Option | Change | Difficulty |
|---|---|---|
| A. Keep as is | Nothing. Probably fine for room-range Bluetooth (~60 %) | 0/10 |
| B. Rectangle, copper-free corner | Bare FR4 under the antenna: worse | 1/10 |
| C. Deeper L | ESP32 ~8.5 mm further back (board ~79.6 → ~88 mm deep) | 2/10 |
| D. Antenna off the rear edge | ESP32 turned; board ~25 mm deeper; flashing-port access rethought | 5/10 |

Recommendation was **C** (~75 % confident). **Owner's decision: A, keep the
layout as is** (2026-10-26). No cost difference either way at a flat-priced
fab. If Bluetooth range proves short on the built box, C is the known fix.

Source: Espressif, *PCB Layout Design* (antenna placement),
https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s2/pcb-layout-design.html

---

## The original audit

*As written before the fix pass. Verdict at the time: do not order.*

**Verdict: do not order this board.** Two errors would stop it working at all,
and several more would cause faults in use or at the fab. All are fixable before
ordering; none needs a new approach.

Method: KiCad 7's own DRC (`/usr/bin/python3 drc.py`), measurement of the placed
geometry, and a line-by-line review of the netlist against the parts' datasheets
and the footprints' own markings. Reviewed adversarially — the same author built
every part of this, so prior conclusions were treated as suspect.

## The headline finding about the process

**KiCad's DRC was available all along.** `kicad-cli` in KiCad 7 has no DRC
subcommand, but `pcbnew.WriteDRCReport` has existed since 7.0 and is importable
from `/usr/bin/python3`. For several sessions this project said "no DRC is
available here" because only the CLI had been checked.

Nearly every serious error below was invisible to the project's eight custom
checks and visible to KiCad's DRC in seconds. The custom checks are not useless —
the copper-to-copper clearance check was right, which DRC confirmed — but each
had a blind spot shared with the code it was checking:

| Check | Blind spot | What it missed |
|---|---|---|
| `check_netlist.py` | compares pad-number **sets**, not what each pin **is** | both diodes reversed |
| `route.py` + `check_clearance.py` | treat every pad as its bounding **rectangle** | 9 open connections on round pads |
| `check_clearance.py` | tests the keep-out at track **endpoints** only | a via inside the antenna keep-out |
| `check_pcb.py` | overlap test is strict, so **touching** passes | two courtyard pairs with zero gap |
| *(none)* | no hole-to-hole spacing check | 3 vias drilled beside through-holes |
| `route.py` | reports its own success | claimed 23/23 nets routed; 9 links are open |

**Recommendation:** make `drc.py` the authority in `build.sh` and keep the
custom checks as fast pre-checks.

## Severity summary

| # | Finding | Severity | Fix difficulty |
|---|---|---|---|
| 1 | Both Schottky diodes reversed on the footprint | **Critical** | 1/10 |
| 2 | Nine connections open, including input 2 → rail | **Critical** | 3/10 |
| 3 | Unpowered input board back-fed by the ESP32 | **High** | 2/10 |
| 4 | Clock loop-backs on GPIO36/39, which glitch with BT | **High** | 2/10 |
| 5 | Drill-spacing fab violations | **High** | 2/10 |
| 6 | Copper under the antenna; keep-out too small | **High** | 3/10 |
| 7 | Board file has no pad nets or schematic link | **High** | 3/10 |
| 8 | No ground plane | Medium | 5/10 |
| 9 | ESP32 USB-C cable likely fouls the carrier | Medium | 3/10 |
| 10 | Placement stale after the board widened | Medium | 3/10 |
| 11 | Rear mounting holes leave 0.5 mm of FR4 | Medium | 1/10 |
| 12 | Two courtyard pairs touch | Medium | 1/10 |
| 13 | GPIO35 floats when input 1 is absent | Medium | 1/10 |
| 14–20 | Polish: widths, vias, silkscreen, labels, GP29, test points, standoffs | Low | 1–3/10 |

---

## Critical

### 1. Both Schottky diodes are reversed

KiCad's `D_DO-41_SOD81_P7.62mm_Horizontal` marks **pad 1 as the cathode**: the
silkscreen "K" and the cathode band both sit at pad 1. `netlist.py` maps
`"d": {"A": 1, "K": 2}`, putting the **anode** on pad 1.

So on the board, VBUS1 lands on the pad marked "K" and the rail on the other.
A builder following the silkscreen band installs each diode cathode-to-VBUS,
anode-to-rail: reverse-biased. **The rail never receives power and the ESP32
never starts.** Nothing is damaged; the box is simply dead.

The schematic and netlist are self-consistent — the error is the mapping from
pin function to footprint pad. `check_netlist.py` compared `{1, 2}` with
`{1, 2}` and could never see it.

- **Fix:** `"d": {"K": 1, "A": 2}`, and redraw the diode symbol with pin 1 on
  the bar. Then add a check that polarised parts' pin *names* agree with the
  footprint's markings.
- `C1` was checked the same way and is **correct**: `CP_Radial` pad 1 is
  positive, matching `"cpol": {"+": 1, "-": 2}`.
- **Confidence:** 99%. Read directly from the footprint file.

### 2. Nine connections are open

KiCad reports 9 unconnected items. Every one is on a **round or oval** pad
(pin-header pins 2–6, disc capacitors, the radial cap's pad 2, the DO-41 pad 2,
the test point). `route.py`'s `pad_cells()` uses the pad's bounding rectangle,
so the router sometimes ended a track in a corner of that rectangle — outside
the actual round copper.

| Open link | Consequence |
|---|---|
| RAIL track ↔ **D2** cathode | **input 2 cannot power the box**, even with the diodes fixed |
| VBUS2 ↔ **C4** pad 1 | input 2's bypass cap floating |
| VBUS1 tracks dangling beside **C3** pad 1 | input 1's bypass cap floating |
| GND tracks dangling beside **C1** pad 2 | rail bulk cap's ground side |
| GND ↔ **TP2** | ground test point dead |
| DBG1 ↔ **J1** pin 2 | input 1 debug serial |
| SP2 ↔ **J1** pin 5 | a spare GPIO |

The router also knows a through-hole pad only on the top layer, so to reach
the bottom it drilled a via right beside the pad — 7 such vias.

- **Fix:** model pad shapes properly (circle / oval / rect) in the router and the
  clearance check; treat through-hole pads as present on both layers.
- **Confidence:** 99%. KiCad DRC, reproducible with `drc.py`.

## High

### 3. The ESP32 back-feeds whichever input board is unpowered

`hardware/wiring.md` says the GPIO34–39 pull-up gap is "fine here because every
board is always powered together". **That is false under this power design.**
With only host 1 connected, input 1 and the ESP32 are powered (via D1) but input
2 is not — D2 stops the rail reaching it, by design.

The ESP32 then keeps driving BCLK and LRCK into input 2 through only **33 Ω**,
and UART TX into its GP5 through **nothing**. Current flows through input 2's
ESD diodes into its unpowered 3V3 rail: out of spec, and it can leave the chip
in a half-powered state.

- **Fix (recommended):** raise R1–R4 from 33 Ω to **1 kΩ**, and add 1 kΩ in
  series with each UART TX line (IO17 → U1.GP5, IO19 → U2.GP5). Injection drops
  to ~3 mA per pin. At 2.8 MHz with ~10 pF of load, 1 kΩ gives ~22 ns edges
  against a 177 ns half-period — and the RP2350's inputs are Schmitt-triggered.
- **Fix (robust):** a 74LVC buffer per board, powered from *that* board's 3V3.
  LVC parts are rated for partial power-down (Ioff), so an unpowered buffer
  neither loads nor feeds anything. Costs SMD parts.
- **Confidence:** 90% that the mechanism is real (standard CMOS behaviour);
  the RP2350's exact injection limit is not verified.

### 4. The I2S1 clock loop-backs use GPIO36 and GPIO39

Espressif documents that powering the SAR ADCs pulls **GPIO36 and GPIO39** low
for about 80 ns, and advises against relying on these pins while ADC or Wi-Fi/BT
is active. Forum reports describe the glitches changing **with A2DP streaming
state** — this project's exact use.

An 80 ns pulse on BCLK (354 ns period) is a spurious clock edge. I2S1 would lose
sync and input 2 would click or drop out, only while Bluetooth is streaming —
the hardest kind of fault to find.

- **Fix (free before ordering):** move the loop-backs to ordinary GPIOs. IO32
  (currently spare SP1) and IO13 are on the same header row as IO25/IO33. Note
  IO13/IO14 are JTAG pins, which only matters if JTAG debugging is wanted.
- **Firmware alternative:** call `adc_power_acquire()` at start-up to hold the
  ADC domain on, at ~1 mA.
- **Confidence:** the erratum is verified from Espressif's documentation;
  ~70% that it would bite here without mitigation.

### 5. Drill-spacing violations

- **3 vias** drilled 0.19–0.21 mm from a through-hole pad's hole (DRC
  `hole_near_hole`), beside C1, C4 and J1 pin 1. Same net, so electrically
  harmless, but most fabs want ≥0.5 mm between PTH holes. All three are the
  pointless "via beside a THT pad" from finding 2.
- **4 ESP32 corner land pads** within hole clearance of the footprint's own
  3 mm NPTH holes (DRC `hole_clearance`) — a pad corner ~0.01 mm from a drilled
  hole. Those NPTH holes are not needed now that the carrier mounts by its own
  screws.
- **Fix:** delete the NPTH from `gen_fp.py`; fix 2 removes the vias.

### 6. Copper under the antenna, and the keep-out is too small

The keep-out covers `x 54..64`, but the ESP32 module ends at `x 58.9`, so it
protects only the last 4.9 mm. A WROOM antenna occupies roughly the last 7–8 mm
of the dev board. In that region there is a **GND via** (DRC flags it inside the
keep-out), a GND track, and the **U2_RX UART line**. The carrier also extends
5.1 mm beyond the antenna end.

- **Fix:** let the antenna end **overhang** the carrier edge — Espressif's
  preferred arrangement. An ~8 mm overhang costs four ESP32 pads at that end:
  EN, IO23 (both unused), one of three GND pads (redundant), and 3V3 (currently
  a mechanical anchor; pick another). A ~3 mm overhang keeps all pads.

### 7. The board file can't be handed to KiCad as-is

`gen_pcb.py` writes footprints with **no net on any pad (106/106)**, **no link to
the schematic (0/18)**, and **no library link**. Opened in KiCad, DRC reports
**305** violations, of which 256 are bookkeeping — they would bury the real ones.
"Update PCB from Schematic" would not recognise the footprints.

- **Fix:** have `gen_pcb.py` write `(net N "NAME")` on each pad, a `(path …)`
  matching the schematic symbol UUIDs, and `lib:name` footprint IDs.

## Medium

| # | Finding | Fix |
|---|---|---|
| 8 | **No ground plane.** GND is 202 mm of 0.4 mm trace. Clocks have no reference plane, beside a 2.4 GHz radio. 185 of 358 segments are on B.Cu, so a pour there would be shredded. `pcbnew.ZONE_FILLER` can fill a pour here, so it is verifiable after all | Signals on F.Cu, solid GND pour on B.Cu, stitching vias |
| 9 | **ESP32 USB-C**: the carrier extends 5.1 mm past the receptacle mouth. The shell centre sits ~3.2 mm above the carrier; a typical overmold is 6.5–8 mm tall, so its underside meets or passes the carrier surface. The flashing cable may not seat. ~70%, cable-dependent | Put that end flush with or past the carrier edge |
| 10 | **Placement went stale** when the board widened to 64 mm. D2 is 27 mm and C4 24 mm from U2's 5V pad — C4 is no bypass at that distance. **SJ1 is 51 mm from U1's GP29, on the wrong side of the board.** The new 11.4 mm channel has room for D2, C4 and SJ2 beside U2's pads | Re-place; SJ1 beside U1 |
| 11 | **Rear mounting holes** leave 0.5 mm of FR4 to the edge; they will crack when screwed | Board 2 mm deeper, or move them |
| 12 | **C3/C1 and C4/TP2 courtyards touch** (zero gap) | 0.5 mm spacing; make the check non-strict |
| 13 | **GPIO35 is input-only with no internal pull**, and floats when input 1 is absent | 100 kΩ pull-down on AUD1 |

## Low / polish

| # | Finding |
|---|---|
| 14 | All traces 0.4 mm, power included. Total drop ~60–70 mV at 300 mA — harmless against the rail budget, but 0.8–1.0 mm is better practice |
| 15 | 74 vias; 183 of 358 segments diagonal. Functional, untidy |
| 16 | 19 silkscreen DRC warnings (module outline clipped at the front edge, refdes over pads). No useful labels: J1 pin names, INPUT 1 / INPUT 2, RAIL / GND at the test points, port edge, version |
| 17 | GP29 is **hard-shorted** to GND by a solder bridge. A firmware mistake driving it high shorts the pin. A 10 kΩ pull-down is safer and still optional |
| 18 | TP1 (rail) and TP2 (ground) are 57 mm apart — awkward with a meter |
| 19 | Through-hole leads protrude underneath, so the carrier must sit on standoffs, not flat on the floor. The four holes suit that |
| 20 | Two hosts' grounds are tied through the board. Inherent to the design, and benign with a Bluetooth output (no third conductive ground) |

## What was checked and is fine

- Copper-to-copper clearance: **0 violations** once pad nets are assigned
  (`check_clearance.py` agreed). The 112 clearance hits in the raw file were
  bookkeeping.
- Netlist versus `hardware/wiring.md`: every I2S, UART and power net matches.
- No connected ESP32 pin is a strapping pin; strapping pins are left floating
  on their internal pulls.
- `C1` polarity correct. Vias tented by default.
- Module land patterns follow `enclosure/boards.scad`; pad positions agree with
  KiCad's own rendering.
- I2S runs are short (worst 39 mm, rule <100 mm).

## Suggested fix order

1. Diode pin mapping (1) and pad-net / schematic links (7) — tiny, and they
   make KiCad DRC trustworthy.
2. Loop-back pins (4) and series resistors (3) — netlist changes; cheapest
   before anything is re-placed.
3. Re-place for the 64 mm board, antenna overhang and USB-C edge (6, 9, 10, 11,
   12), drop the ESP32 NPTH (5).
4. Router: real pad shapes, through-hole on both layers (2); then re-route with
   signals on top and a GND pour on the bottom (8).
5. `drc.py` into `build.sh` as the gate. Polish (14–20).

## Sources

- Espressif, *GPIO & RTC GPIO*, ESP-IDF docs — GPIO36/39 warning:
  https://docs.espressif.com/projects/esp-idf/en/v5.0.3/api-reference/peripherals/gpio.html
- esp32.com, *Issue with GPIO36 Interrupt When Using BLE on ESP32* — field reports:
  https://esp32.com/viewtopic.php?p=136537
- RP2350 GPIO tolerance when unpowered (secondhand; datasheet §14.8.2 not read directly):
  https://www.classiccmp.org/mailman3/hyperkitty/list/cctalk@classiccmp.org/message/T7O2333A7QF6TS2ND2H47SUEY3LTH7VS/
