# Whole-project review — 2026-11-16

Asked for: review the whole project, make sure it is meeting its goals, make
sure the recommended passives are necessary and sufficient, look for problems.

**Evidence labels:** *verified* = read from a file in this repo, a committed
picture, or measured on the board file. *Sourced* = third-party text reached
through search. *Estimate* = my judgement.

## Verdict

| Question | Answer |
|---|---|
| Was the carrier, as it stood, buildable? | **No.** The land pattern for both input boards was the mirror image of the real board (#1). Ordering it would have produced a dead board. *Verified.* |
| Is it now? | The pattern is corrected and the board re-laid: KiCad DRC clean, every signal on one layer. **Not yet confirmed against the boards in your hand**: print the fit-check sheet first. |
| Were the passives necessary and sufficient? | **Neither.** Six did nothing needed, and two that were needed were missing (#5). Now 11 parts instead of 15, one resistor value. |
| Is the project meeting its goals? | The hardware design now is, on paper. Nothing is built. Firmware is not started and is most of the remaining risk. |

## Does it meet the goals?

| Goal | State | Confidence it can be met |
|---|---|---|
| Two USB-C inputs, each a UAC2 sound card | Carrier corrected, unbuilt. Native USB faces the hosts. Firmware not started | ~70 % (firmware: composite audio + network device) |
| Both inputs mixed in the box | ESP32 mixer on two I2S ports. The two-port clocking is untested | ~70 % until the loop-back bench test |
| One Bluetooth output | A2DP source, SBC, 44.1 kHz (verified from source, review-notes #16) | ~85 % |
| Powered by whichever cable is connected | Diode-OR. Two faults found and fixed here (#3, #4) | ~80 %, pending two five-minute bench tests |
| Set up from a browser, no buttons | Design only | ~65 % |
| Low game-audio latency | Capped by SBC and the headphones. Your decision of 2026-09-28; not a hardware matter | — |
| A small box | The enclosure must be redesigned for the carrier (#7) | — |

---

## Findings

| # | Finding | Severity | State |
|---|---|---|---|
| 1 | Input boards' land pattern mirrored | **Fatal** | **Fixed**, re-laid |
| 2 | Input boards' ground reached the plane through two 0.5 mm slivers | High | **Fixed** |
| 3 | The clocks drove the two pins that can back-power a board with no host | High | **Fixed** (pins moved) |
| 4 | Nothing held a host-less input's VBUS at 0 V | High for USB-C hosts | **Fixed** (bleed resistors) |
| 5 | Passives: six unneeded, two missing | Medium | **Fixed** |
| 6 | Five things firmware must do that no part can | Medium | Recorded |
| 7 | Enclosure: three inputs from this review | Medium | Yours to decide |
| 8 | The hand-wiring guide drew both board types mirrored | High if used | Guide flagged |
| 9 | Stale statements in the documents | Low | Corrected |

### 1. The input boards' land pattern was mirrored

**What.** Waveshare's pinout picture (now `docs/sources/rp2350-usb-c-pinout.png`)
shows the board component side up with the native USB port at the top: **5V
is the top-left pad**, GP0 the top-right. The carrier had the native port at
the front and **5V on the right**.

**Why.** `gen_fp.py` drew pads 1–9 at −X with the native port at +Y, as if +Y
pointed up. In KiCad +Y points down. `check_footprints.py` recomputed the pads
with the same convention, so it agreed. Turning the boards half a turn on
2026-10-27 did not help: a mirror image turned round is still a mirror image.

**What would have happened.** Each input board's 5V pad would have sat on the
carrier's GP0 land (soldered for strength, connected to nothing) and its GND
on a bare land. No power to the rail, no common ground, every signal on the
wrong pin. The modules solder flat, so it could not have been reworked.

**How it was missed.** Nothing in the repo showed the real board, so "left"
was only ever compared with itself. The pattern stood for three weeks
(2026-10-26 to 2026-11-16) and through one audit.

**Fix.**
- The footprint is drawn as the picture looks, and placed unrotated.
- `check_pcb.py` states where each module's corner pads must be **on the
  placed board** (west/east, front/rear), taken from the pictures. It fails
  on the old pattern, on a half-turned board, and on swapped ESP32 rows.
- Both of Waveshare's input-board pictures are committed.
- `carrier-fit-check.pdf`: the board at 1:1 with every land named.

**The ESP32's pattern was right.** Checked land by land against
`docs/sources/esp32-dev-kit-drawing.png`.

| | |
|---|---|
| Confidence the old pattern was mirrored | 99 % (*verified*: picture against board file) |
| Confidence the new one matches your boards | ~95 %. The picture is Waveshare's; the paper check closes the gap |

### 2. The input boards' ground reached the plane through two slivers

**What.** The rail ran on the bottom layer *behind* each input board's ground
pad. That left both boards' only ground connections on a front strip of
plane, joined to the rest by two necks: 0.5 mm wide above D1's cathode pad
and 0.55 mm beside C1. *Verified* by eroding the pour until it split.

**Effect.** Fine at DC (a few milliohms). But every signal's return current
took a ~100 mm detour, and the "solid ground plane under the signals" was not
connected to the boards the signals came from. Estimated ground bounce on a
fast edge: ~0.5 V for a few nanoseconds (*estimate*).

**How it was missed.** DRC was clean and the pour covered 89 %. Neither says
whether the plane is in one piece *where it matters*.

**Fix.** The rail now passes **in front of** the ground pads and hugs the
left edge. Each input board has a ground via straight into the main plane.
`check_routing.py` measures the narrowest pour between each input board's
via and the ESP32's: at least 4 mm now, and the build fails under 2 mm.

### 3. The clocks drove the two pins that can back-power a dead board

With one host connected, the other input board has no power, and the ESP32
keeps driving clocks and UART into it. The 1 kΩ series resistors were there
to limit that.

**What was wrong.** The RP2350 has two kinds of pad:

| Pads | With the chip unpowered | Evidence |
|---|---|---|
| GP0–GP25: fault-tolerant | "very little current flows into the pin whilst it is below 3.63 V" | *Sourced*: RP2350 datasheet, quoted on the Raspberry Pi forum |
| GP26–GP29: ADC-capable | "an internal reverse diode to the VDDIO (3V3) rail" | *Sourced*: Pico 2 datasheet, via search |

BCLK and LRCK went to **GP26 and GP27**: the only kind that conducts. Through
1 kΩ, each would still have pushed 1–3 mA into the dead board's 3.3 V rail,
and from there back through its regulator to its USB port (*estimate*).

**Fix.** BCLK → **GP9**, LRCK → **GP10**. Same edge, next pads along,
consecutive (one PIO input group). The UART was already on a fault-tolerant
pad. Audio out stays on GP28: it is an output, so nothing drives into it.

**Side benefit.** GP26, GP27 and GP29 are free, so three analogue inputs
remain for a volume knob one day (`design-envelope.md` had listed that as a
pin conflict).

| | |
|---|---|
| Confidence in the pad behaviour | ~85 %. I could not open the datasheet itself from this sandbox |
| Cost if I am wrong | None: GP9/GP10 are ordinary GPIOs either way |
| Settled by | Bench test A, below |

### 4. Nothing held a host-less input's VBUS at 0 V

**What.** A Schottky leaks in reverse. An input board with no host sits on
the far side of its diode from a live rail, so its VBUS is fed that leakage
with nothing to drain it, and floats up.

**Why it matters.** A USB-C host switches a port on only "when VBUS is at
vSafe0V" (under 0.8 V). *Sourced*: USB Type-C specification text as quoted in
Linux kernel commits; compliance testers hold VBUS high and expect the port
to wait. So the second host might never power its input while the first is
connected, which is the box's whole purpose. USB-A ports do not check.

**Fix.** R10, R11: **1 kΩ from each input board's VBUS to ground.** Holds it
under 0.8 V against up to 0.8 mA of leakage. Costs 5 mA while that host is
connected.

| | |
|---|---|
| Confidence the mechanism is real | ~85 % |
| Confidence it would have bitten on a real host | ~60 %. Depends on the host and the diode |
| Diode | **1N5819 preferred over 1N5817**: lower leakage. Its extra ~0.1 V drop does not matter; the ESP32's converter works down to 2.3 V |
| Settled by | Bench test B. If VBUS stays under ~0.3 V with no resistor, R10/R11 may be left out |

### 5. Passives: necessary and sufficient

| Part | Job | Verdict | Now |
|---|---|---|---|
| D1, D2 Schottky | Keep the two hosts' 5 V apart | **Necessary** | Kept |
| R1–R4, 1 kΩ | In series with the clocks | Useful, no longer what protects the chip (#3): edge-rate control beside the radio | Kept |
| R5, R6, 1 kΩ | In series with each UART TX | Useful: limits current if a pin is ever set the wrong way | Kept |
| R10, R11, 1 kΩ | Bleed on each VBUS | **Necessary** for USB-C hosts (#4). **Was missing** | **Added** |
| C1, 22 µF | Rail bulk at the ESP32 | Recommended: damps plug-in ringing, rides through a change of supplying host | Kept |
| R7, 100 kΩ | Pull-down on input 2's audio | **Not needed**: that line is now on a pin with an internal pull-down | Removed |
| R8, R9, 4.7 kΩ | Pull-down on each GP29 | **Not needed**: nothing reads GP29 | Removed |
| C2, 0.1 µF | Bypass at the ESP32's 5V pin | **Not needed**: the ESP32 board has its own | Removed |
| C3, C4, 0.1 µF | Bypass at each input board's 5V pin | **Not needed**: each board has its own | Removed |

- **Before:** 2 diodes, 9 resistors (3 values), 4 capacitors. **Now:** 2
  diodes, 8 resistors (all 1 kΩ), 1 capacitor.
- *Not verified:* the modules' own capacitor values. Their schematics are not
  in the repo and I could not reach Waveshare's site. If a module turns out
  to have no input capacitor, that is the case for putting C2–C4 back.
- If you want any removed part back, say so. They are footprints, not
  principles.

**Sufficient also depends on firmware**: see #6.

### 6. Five things firmware must do

No part on the board can do these. They are now in `docs/architecture.md` §2a.

| # | Requirement | Why |
|---|---|---|
| a | Pull-**ups** on the ESP32's UART RX pins (IO33, IO19) | A board with no host leaves its TX floating: garbage bytes |
| b | Pull-**downs** on the audio inputs (IO13, IO18) | A floating data line is noise in the mix |
| c | Mute an input whose board is not answering on its UART | Belt and braces for (b) |
| d | A slip buffer between I2S capture and the Bluetooth feed | Both clocks come from one crystal but through different dividers, so they differ by a few parts per million. `architecture.md` said "no resampling anywhere"; true, but samples must be dropped or repeated now and then or a buffer overflows after minutes to hours. Difficulty 2–3/10. *Estimate*, backed by ESP-IDF issue reports of I2S running off its nominal rate |
| e | Each input board is told which input it is by the ESP32 | One firmware image, but the two need different USB serial numbers and network addresses |

### 7. Enclosure: three inputs from this review

| Item | Detail |
|---|---|
| **ESP32 USB-C access** | Its port faces the left wall, 1 mm past the carrier's edge. No cable can be plugged in inside a box without an opening there, lid on or off. That conflicts with the 2026-10-11 decision to keep that port inside. Options: an opening with a printed blanking plug; or lift the carrier out to flash. **Your decision** |
| Height | The tallest parts are now C1 (about 11 mm) and the six standing resistors (about 9 mm). C1 can be laid over, or a 5 × 7 mm can used |
| BOOT buttons | On each input board's top face beside the front port (Waveshare's picture). Reachable with the lid off |

### 8. The hand-wiring guide drew both board types mirrored

`hardware/figures/pictorial.py` has the same error as #1, for both the input
boards **and** the ESP32. The guide was already marked out of date; its
banner now says its drawings are mirrored. The loom is no longer a usable
fallback as drawn.

### 9. Documents corrected

| Where | Was | Now |
|---|---|---|
| `docs/architecture.md` | UART on GPIO17/16 and 19/18 | Current pins; firmware requirements added |
| `hardware/wiring.md` | Old pin tables; "longest chain under 65 mm" | Current pins, pad types, bleed; 73 mm |
| `CONNECTIONS.md` | "nearest joint is 9.8 mm from the USB-C shell" | 2.9 mm |
| `README.md` | "Status: planning … coupon needs re-measuring" | Current status |
| `hardware/BOM.csv` | Old passives | Current |
| Code comments | "exposed port", "+Y is the programming port" | Described against the pictures |

---

## What changed on the board

| Signal | Was | Now |
|---|---|---|
| BCLK at each input board | GP26 | **GP9** |
| LRCK at each input board | GP27 | **GP10** |
| BCLK loop-back in | IO25 | **IO32** |
| LRCK loop-back in | IO33 | **IO35** |
| ESP32 TX → input 1 | IO4 | **IO25** |
| ESP32 RX ← input 1 | IO16 | **IO33** |
| Input 2 audio | IO35 | **IO18** |
| ESP32 TX → input 2 | IO21 | IO21 |
| ESP32 RX ← input 2 | IO19 | IO19 |
| Unchanged | BCLK out IO26, LRCK out IO14, input 1 audio IO13, audio out GP28, UART GP4/GP5, debug GP3 | |
| Debug | One 3-pin header | **One 2-pin header beside each input board** |

| | Before | Now |
|---|---|---|
| Track | 757 mm | 568 mm |
| Signal vias | 0 | 0 |
| Longest I2S chain | 81 mm | 73 mm |
| Ground path, input board to ESP32 | ~0.5 mm wide | ≥ 4 mm |
| Bottom pour | 89 % | 91 % |

---

## Two bench tests, five minutes each

Both need only the boards you have, a multimeter and a few jumper wires. No
firmware.

**A. Back-feed (#3).** Power input board X from USB. Leave board Y unplugged.
Join their GND pins.

1. Wire X's 3V3 pin through 1 kΩ to **Y's GP26**. Measure Y's 3V3 and 5V
   pins. Expect roughly 1–2 V: the diode path.
2. Move the wire to **Y's GP9**. Expect about 0 V.

**B. Bleed (#4).** Two Schottkys, cathodes joined (the "rail"). X's 5V pin to
one anode, Y's 5V pin to the other. Power X only.

1. Measure Y's 5V pin. Above 0.8 V means the bleed is needed.
2. Add 1 kΩ from Y's 5V pin to GND. Expect under 0.1 V.

## What I could not verify

`datasheets.raspberrypi.com` and Waveshare's sites are blocked from this
sandbox, so:

| Fact | Standing |
|---|---|
| RP2350 pad types (#3) | *Sourced* through search, not read |
| Modules' own capacitors, and what loads each VBUS (#4, #5) | Not verified |
| Schottky leakage at 5 V | *Estimate*; the datasheet curve was not read |
| USB-C vSafe0V rule | *Sourced* through kernel commit messages |
| The pictures match your boards | Yours to check |

## What needs you

| # | What | Time |
|---|---|---|
| 1 | **Print `hardware/carrier/carrier-fit-check.pdf` at 100 %.** Check the 50 mm bar, lay the modules on it, compare every name | 10 min |
| 2 | Say if you want any removed part back (#5), or object to the pin changes | — |
| 3 | Decide how the ESP32's USB-C is reached in the box (#7) | — |
| 4 | Bench tests A and B (optional, cheap) | 10 min |
| 5 | The I2S loop-back bench test, which needs a little firmware (still recommended before ordering) | An afternoon |

After 1 passes I can export the Gerber and drill files.
