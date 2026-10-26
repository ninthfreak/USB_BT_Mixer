# Carrier board

> **⚠ DO NOT ORDER.** The 2026-10-26 audit found two errors that would stop
> this board working — both diodes reversed on the footprint, and nine open
> connections including input 2's path to the rail — plus several fab and
> in-use faults. Claims below that the board is "verified clean" predate it.
> See [`AUDIT.md`](AUDIT.md). KiCad's real DRC: `/usr/bin/python3 drc.py`.

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
| `gen_pcb.py` | Emits `carrier.kicad_pcb`: outline and placement |
| `route.py` | Grid A* router over two layers; writes tracks and vias into it |
| `gen_table.py` | Emits `CONNECTIONS.md` |
| `check_netlist.py` | Reads the netlist back *out* of the schematic and diffs it against `netlist.py`; also resolves every footprint and checks its pad numbers |
| `check_footprints.py` | Recomputes every pad coordinate from `boards.scad`; checks each courtyard encloses its fab outline and is symmetric |
| `check_pcb.py` | Courtyards inside the outline, none overlapping, no part on a mounting hole, exposed ports on the front edge |
| `check_routing.py` | Net lengths, I2S against the <100 mm rule, copper headroom, nothing live in the antenna keep-out |
| `check_pads_vs_kicad.py` | **Independent.** Rasterises F.Cu and compares every pad centroid to where we think it is |
| `check_clearance.py` | Every same-layer pair of different nets, measured edge to edge against the 0.25 mm rule |
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

## Layout: 64 x 74 mm, routed

**23/23 nets, 358 segments, 74 vias, 1185 mm of track.** Design rules are
0.40 mm trace on 0.25 mm clearance, vias 0.8 mm on a 0.4 mm drill — loose for
any fab (JLCPCB allows 0.127 mm), so the board is cheap and tolerant.

### Why 64 mm and not 58

At 58 mm the two input boards left a **2.2 mm channel** between them, and
*six* of input 2's nets need access from that side, because both modules face
the same way and so its power and I2S edge points into the gap. The router
could not fit them and neither could a person. Widening the board to 64 gives
an 11.4 mm channel and everything routes.

This was the right fix rather than a cleverer route: the box is ours to size.
**The enclosure needs about 5 mm more width to suit.**

### What this route is and is not

It is machine-routed and verified: every net connected, every same-layer pair
of different nets at least 0.25 mm apart, nothing in the antenna keep-out,
nothing off the edge. It is **not pretty** — long diagonals, 74 vias, and
traces that wander where a person would go straight. A pass in the editor
would tidy it considerably without changing anything electrical.

There is **no ground pour**. A zone's filled shape is computed by KiCad and
cannot be verified here, so ground is routed as ordinary traces instead.
Adding a B.Cu pour in the editor afterwards is one action and KiCad will DRC
it; that would improve clock return paths.

**A DRC pass in the KiCad editor is still required before ordering.**
`check_clearance.py` covers copper-to-copper on the same layer, board edge and
keep-out. It does not cover soldermask slivers, drill-to-drill spacing,
annular ring, or anything about zones.

Placement is by **courtyard centre**, not footprint origin: several stock
footprints put their origin on pad 1, so a literal `(x, y)` meant something
different for every part.

### Why there is an independent check

`check_pcb.py` reuses `gen_pcb`'s geometry on purpose, so the generator and
the check cannot drift apart. The cost is that a bug in the **shared** code is
invisible to both, and that is exactly what happened.

The transform placing a rotated footprint was wrong for 90 degrees — it used
`y' = +x` where KiCad uses `y' = -x`. Five parts were up to **7.6 mm** out of
position, D1 and D2 partly off the board, and every check reported OK because
the check did the same wrong arithmetic.

`check_pads_vs_kicad.py` closes that hole by taking KiCad's word for it: it
renders F.Cu, finds the centroid of every copper blob, and compares. The board
outline is rendered too, so the pixel-to-mm mapping is self-calibrating and no
assumption about page size enters. Reintroduce the old transform and the two
checks disagree, which is the point:

```
check_pcb  -> OK: all courtyards inside the outline, none overlapping
vs KiCad   -> FAIL: C1.2 we say (3.40,27.62); nearest KiCad shape (3.37,25.09)
```

### What the checks caught

| Found by | What |
|---|---|
| `check_pcb.py`, first run | ~20 real collisions in my first placement, including every part in the 6 mm service strip sitting inside the ESP32's courtyard |
| the render | both front mounting holes drilled through D1 and D2 — invisible to the courtyard test, because holes are Edge.Cuts circles with no courtyard. The check now covers them |
| `check_clearance.py`, first run | 22 clearance violations in the first route, worst −0.400 mm. Three router bugs: clearance stamped for a trace but not for a via landing beside one; releasing a net's own pads also erased other nets' traces in that box; and a net's own traces were stamped as obstacles against itself, stranding its last pad |
| `check_footprints.py` | an asymmetric courtyard left by a careless `sed`, 1.3 mm on one side and 0.5 on the other, which shifted placement by 0.4 mm |

### Routing headroom

An earlier revision of this file called the board dense and routing unproven,
citing "81% courtyard area". **That figure was being misread.** A courtyard is
keep-out for other *components*, not for copper. Each module touches the board
only at its edge pads and is flat underneath, so the whole area beneath both
RP boards and the ESP32 is free for traces on *both* layers.

`check_routing.py` measures it from the real placement:

| | |
|---|---|
| Total minimum trace length | ~930 mm over 23 nets |
| At 0.4 mm trace / 0.4 mm clearance | ~9% of the available copper |
| Worst I2S net (BCLK) | 37 mm, against the <100 mm rule in `wiring.md` |
| Longest net | GND at 142 mm, and GND will be a pour rather than traces |
| Connected pads in the antenna keep-out | none |

So there is plenty of room. The one genuinely tight spot is the **2.2 mm gap
between the two input boards**, where input 2's power and I2S pads face
because both modules point the same way — but those nets drop to the bottom
layer through a via rather than squeezing through the gap.

The service strip is 4.1 mm, so only parts under ~4 mm tall fit there, which
is why the bulk cap C1 sits in the left column rather than beside the ESP32's
5V pad.

## Soldering: not every pad

Only the pads that carry a net, plus a corner or two per module so nothing can
peel from one end. **43 joints instead of 74.** `CONNECTIONS.md` has the
per-pad map; `SOLDER_MECHANICAL` in `netlist.py` lists the mechanical ones and
`check_netlist.py` asserts every one of them is electrically floating — several
are the ESP32's flash and strapping pins, and tying those to live copper would
be worse than leaving them unsoldered.

The full land pattern is still fabricated, so any pad can be soldered later
without a new board.

### Plug forces are not held by solder

Worth stating plainly, because it is easy to assume otherwise. Each input
board's pads stop **9.8 mm short of its USB-C shell** — `boards.scad` calls
that the port-end pad-free zone. There is no solder anywhere near the
connector, with a full land pattern or a partial one.

Pulling a cable therefore applies a peel moment that solder was never taking.
The enclosure already handles it: the lid's `press_out` posts bear on the
module's top face 0.6–3.1 mm from the port edge, and the retention nubs sit in
the edge notches. **A carrier build must keep both**, which means the lid posts
stay as they are (the module sits 0.1 mm higher on a 1.6 mm carrier, so they
need no change) and the carrier must not block the nubs.

## Still open

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
