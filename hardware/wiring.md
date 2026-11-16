# Wiring: ESP32 hub design

2× **Waveshare RP2350-USB-C** (USB audio inputs) → **Waveshare ESP32-DEV-KIT-WROOM-32E-N4** (clock master, mixer, Bluetooth A2DP source).

Replaces the earlier RP2040-chain pin map and `docs/HANDOFF.md` §4. Board decisions: `docs/decisions.md` (2026-09-29). The earlier QT Py RP2040 + Feather V2 pin map is superseded; see review-notes #20 for why the boards changed.

**Status:** proposed, not yet built. Pin numbers come from the boards' schematics, checked. Whether the I2S and UART setup works is untested.

**Build route:** the three modules solder flat onto a carrier PCB (`hardware/carrier/`; chosen 2026-10-26, see `docs/decisions.md`). `hardware/carrier/netlist.py` is the source of truth for the connections; this page explains the reasons.

**Changes:**
- **2026-10-26 (carrier audit):** series resistors raised to 1 kΩ and added on UART TX, pull-downs added, loop-backs moved off GPIO36/39 (`hardware/carrier/AUDIT.md`).
- **2026-10-27:** the input boards turn round so their **native USB port faces the hosts** (review-notes #25), and the ESP32 pins were re-chosen so the carrier routes on one layer. The hand-wired guide (`hardware/wiring-guide.html`) predates this and is marked out of date.
- **2026-11-16 (project review):** the carrier's input-board land pattern was the mirror image of the real board; corrected, and the ESP32 pins re-chosen for the true geometry. Clocks moved to **GP9/GP10** on the input boards. Bleed resistors added on each VBUS; six unneeded passives removed (`docs/project-review-2026-11.md`).

```
                     BCLK, LRCK (ESP32 is clock master)
            ┌───────────────────────┬──────────────────────┐
            │                       │                      │
 Host 1 ─USB─▶ RP2350 1 ──DOUT──▶ ESP32 I2S0 (RX, master)   │
               UART ◀──────────▶ ESP32 UART1               │
                                                           │
 Host 2 ─USB─▶ RP2350 2 ──DOUT──▶ ESP32 I2S1 (RX, slave) ◀──┘ (BCLK/LRCK looped back)
               UART ◀──────────▶ ESP32 UART2

 ESP32: mix + gain + limiter → Bluetooth A2DP (SBC) → headphones
```

## Why the ESP32 uses two I2S peripherals

- The original ESP32 has **two I2S peripherals, each with one data input** in standard mode (TDM support on the original ESP32 is unlikely, ~75% confident).
- **I2S0** runs as **master**: it generates BCLK/LRCK and receives input 1.
- **I2S1** runs as **slave** on the same clocks and receives input 2.
- BCLK and LRCK are **wired back into two spare GPIOs** for I2S1 (BCLK: GPIO26 → GPIO32; LRCK: GPIO14 → GPIO35). Routing them internally is probably possible too (~70% confident), but a physical loop-back removes that uncertainty for the cost of two otherwise-idle pins.
- Which pin of each pair is the output and which the loop-back input is firmware's choice; the table below is the recommended one. I2S signals go through the ESP32's GPIO matrix, so any of these pins can carry them.

## ESP32 board pins (Waveshare ESP32-DEV-KIT-WROOM-32E-N4)

From Waveshare's schematic `ESP32-DEV-KIT-XX.pdf` (Altium, dated 2026-09-09). Header J3 is the left side, J4 the right.

| Signal | ESP32 GPIO | Header | Direction | Notes |
|---|---|---|---|---|
| BCLK out (I2S0 master) | 26 | J3 | Out | Through 1 kΩ to each input board (R1, R2) |
| LRCK out (I2S0 master) | 14 | J3 | Out | Through 1 kΩ to each input board (R3, R4). GPIO14 is a JTAG pin some sources say emits PWM at boot; harmless on a clock output |
| BCLK loop-back in (I2S1 slave) | 32 | J3 | In | Linked to GPIO26 under the ESP32, before the resistors |
| LRCK loop-back in (I2S1 slave) | 35 | J3 | In (input-only pin) | Linked to GPIO14 under the ESP32, before the resistors. Always driven, so its lack of a pull does not matter |
| Data in from input 1 (I2S0) | 13 | J3 | In | **Firmware: enable the internal pull-down.** GPIO13 is also JTAG MTCK; only matters if JTAG is wanted |
| Data in from input 2 (I2S1) | 18 | J4 | In | **Firmware: enable the internal pull-down** |
| UART1 TX → input 1 RX | 25 | J3 | Out | Through 1 kΩ (R5) |
| UART1 RX ← input 1 TX | 33 | J3 | In | **Firmware: enable the internal pull-up** |
| UART2 TX → input 2 RX | 21 | J4 | Out | Through 1 kΩ (R6) |
| UART2 RX ← input 2 TX | 19 | J4 | In | **Firmware: enable the internal pull-up** |
| Power in | `5V` (net VSYS) | J3 pin 19 | — | From the shared rail. See **Power** below |
| Ground | GND | J3 / J4 | — | |

Spare: GPIO4, 16, 17, 22.

**Why these pins.** They are chosen for the carrier's layout. Along the ESP32's front row (J3), from its USB-C end to its antenna end: input 1's audio (13), LRCK out (14), BCLK out (26), input 1's UART (25, 33), BCLK in (32), LRCK in (35). The clocks' output pins face input 1 and their loop-back pins face input 2, so the two links under the ESP32 nest instead of crossing. Input 2's audio and UART pass between the pads east of GPIO35 to the rear row (J4). That is what lets every signal stay on one layer (`hardware/carrier/README.md`).

**Pins deliberately avoided on this board:**

| Pin | Why |
|---|---|
| GPIO36, GPIO39 | Espressif erratum: pulled low for ~80 ns when the SAR ADC powers up, reported to coincide with A2DP streaming. A spurious clock edge would knock I2S1 out of sync. These were the loop-back pins until 2026-10-26 |
| GPIO27 | Drives the onboard WS2812 RGB LED through R1 (0 Ω). Free it by removing R1 if ever needed |
| GPIO34 | Battery-voltage divider (200 k / 100 k) through R28 (0 Ω) |
| GPIO12, GPIO15 | Strapping pins (MTDI, MTDO); external levels at boot change boot behaviour |
| GPIO0, GPIO2, GPIO5 | Strapping pins, and GPIO0 is on the auto-download circuit |
| TXD0 / RXD0 | Console UART to the CH343P USB-serial chip; keep free for logs and flashing |
| SD0–SD3, CMD, CLK | Module flash |

**Not every board is always powered.** With only one host connected, that input board and the ESP32 run (through its diode), but the other input board is unpowered: its diode stops the rail reaching it, by design. Three consequences, all handled:

- **Back-feed.** The ESP32 keeps driving BCLK, LRCK and UART TX into the unpowered board. Those lines land on GP9, GP10 and GP5, which are the RP2350's **fault-tolerant** pads: with the chip unpowered, "very little current flows into the pin whilst it is below 3.63 V" (RP2350 datasheet; sourced, not read directly). The four ADC-capable pads, GP26–GP29, are different: they have a diode to the board's 3V3 rail, and a clock driven into one would power the dead board through the pin. That is where the clocks were until 2026-11-16 (`docs/project-review-2026-11.md` #3). ~85 % confident in the pad behaviour; a five-minute bench test settles it.
- **Floating outputs.** The unpowered board's DOUT and UART TX float. Firmware switches on the ESP32's pull-downs on the two audio inputs and pull-ups on the two UART RX pins, and mutes an input whose board is not answering.
- **Leakage into its VBUS.** The unpowered board's diode leaks a little of the rail back into that board's VBUS. A USB-C host will not switch a port on until VBUS is under 0.8 V, so each VBUS has a 1 kΩ bleed to ground (R10, R11; review #4).

## Input board pins (Waveshare RP2350-USB-C, identical on both)

From Waveshare's schematic `RP2350-USB-C.pdf` (github.com/waveshareteam/RP2350-USB-C). The 18-pin header exposes GPIO0–10, GPIO26–29, 3V3, GND and the raw-VBUS pin.

**Which USB port is which (owner, boards in hand):** the **internal "programming" port, the one whose shell stands proud of the board edge, is the RP2350's native USB**: the only port its bootloader works on, and the one USB audio needs. The other port, flush with the board edge, is PIO-USB on GPIO12/13. So each board is mounted with the **native port facing the hosts** and the PIO-USB port facing inward, unused (review-notes #25).

**Which edge is which.** Waveshare's pinout picture is `docs/sources/rp2350-usb-c-pinout.png`. Component side up, native port (beside BOOT and RST) at the top:

| Edge | Top to bottom |
|---|---|
| **Left** | `5V GND 3V3 29 28 27 26 10 9` |
| **Right** | `0 1 2 3 4 5 6 7 8` |

So power and I2S leave the **left** edge and the UART and debug pins the **right**. The carrier had this mirrored until 2026-11-16 (review #1).

**Naming:** the schematic calls this net `VSYS`, but **the silkscreen reads `5V`** — and the owner has confirmed the same is true on the ESP32 board. So **both boards are silkscreened `5V`** for what the schematics call VSYS. Below, "the `5V` pin" means that net on either board. It is the raw supply, not regulated 3.3 V.

| Signal | GPIO | Direction | Notes |
|---|---|---|---|
| BCLK in | 9 | In | From ESP32 GPIO26 via 1 kΩ. Fault-tolerant pad |
| LRCK in | 10 | In | From ESP32 GPIO14 via 1 kΩ. Fault-tolerant pad. GP9 and GP10 are consecutive: one PIO input group |
| DOUT | 28 | Out | To the ESP32 data-in pin (13 for board 1, 18 for board 2) |
| UART TX | 4 | Out | UART1 TX → the ESP32 UART RX |
| UART RX | 5 | In | UART1 RX ← the ESP32 UART TX, via 1 kΩ. Fault-tolerant pad |
| Debug serial TX (PIO) | 3 | Out | Optional, to a USB-serial adapter on J1 / J2 |
| Spare, ADC-capable | 26, 27, 29 | — | Free. Never drive these from the ESP32 (see above). GP29 was a chain input with a pull-down until 2026-11-16; nothing reads it |
| Spare | 0, 1, 2, 6, 7, 8 | — | Free |

Not on the header, so no conflict: GPIO12/13 (the PIO-USB port, facing inward), GPIO16 (RGB LED).

**Erratum RP2350-E9** (input leakage on stepping A2, fixed in A4) does not matter here: every input in use is driven. Waveshare's picture shows an `RP2350A0A4` chip, the fixed stepping; the marking on your own chips will say which you have.

## Power

**The RP2350-USB-C has no VBUS diode.** Its USB-C VBUS connects straight to the `VSYS` net and the header pin silkscreened `5V` (verified from the schematic). Both of its USB-C ports share that net. So each input board needs **its own external Schottky** before the shared rail, or the two hosts' 5 V rails would be tied together.

```
Host 1 ─USB-C─▶ board 1 `5V` ──▶|── ┐
                     │ 1k to GND    ├── shared rail ──▶ ESP32 `5V` pin (J3-19)
Host 2 ─USB-C─▶ board 2 `5V` ──▶|── ┘
                     │ 1k to GND
                (D1, D2: your Schottkys, cathode to the rail; R10, R11: bleed)
```

| From | To |
|---|---|
| Input board 1 `5V` pin | D1 anode; R10 (1 kΩ) to GND |
| Input board 2 `5V` pin | D2 anode; R11 (1 kΩ) to GND |
| D1 + D2 cathodes | Shared rail → ESP32 `5V` pin (J3-19), 22 µF (C1) near the ESP32 |
| All GND | All GND |

- **Diode orientation matters:** the banded end (cathode) goes to the rail. On the carrier, the band goes on the end with the square pad and the "K" mark. Check with a multimeter's diode range before powering anything.
- Each input board's own 3.3 V regulator (RT9013) is fed from its USB VBUS *before* the diode, so it keeps full headroom.
- The rail is about 4.25–5.2 V, typically ~4.65 V (estimate; review-notes #18): VBUS minus cable drop minus one Schottky drop. Measure it on the built box.
- **The ESP32 board's own USB-C is protected:** its VBUS reaches VSYS through D3 (MBR230, onboard). Plugging a laptop into it for flashing does not back-feed the rail past the input boards' diodes, and the rail does not appear on its USB-C. **You can flash the ESP32 with the box powered.**
- The ESP32 board's MP1605 converter accepts 2.3–5.5 V in (schematic note), covering the whole rail range with ~0.3 V to spare at the top.
- The ESP32 board's ETA6098 charger sits on the same VSYS net. With no battery fitted it should stay idle (estimate ~85%; its absolute-maximum ratings are unverified). Never fit a battery to its GH1.25 connector.
- **The bleed resistors (R10, R11)** hold an input board's VBUS at 0 V while it has no host. Without them the diode's reverse leakage floats it up, and a USB-C host checks VBUS is under 0.8 V before it switches a port on (review #4). Prefer **1N5819** to 1N5817 for the diodes: lower leakage.
- **The PIO-USB port on each input board is live on that same net.** Anything plugged into it lands on that board's VBUS, on the host side of the diode. Both face inward: leave them unused and unreachable inside the case.

## Programming with everything soldered

| Board | How |
|---|---|
| Input boards | Through the **front USB-C port** (native USB). First flash: hold BOOT while plugging in, and the board appears as a USB drive; copy the UF2 onto it. BOOT sits on the board's top face, reachable with the lid off. After that, firmware can reboot itself into the bootloader on command (`picotool reboot -u` or the web page, `docs/architecture.md`), so updates need no button and no lid off |
| ESP32 | Through its own USB-C, which hangs 1 mm past the carrier's left edge so a cable fits. The board's auto-download circuit needs no button presses, and its onboard diode lets the box stay powered while flashing. Later: OTA over Bluetooth/Wi-Fi is possible but not designed |

## ESP32 board mechanical (from Waveshare's dimensioned drawing)

| Dimension | Value |
|---|---|
| Board | 53.80 × 27.94 mm |
| Mounting holes | **Four**, at 50.04 mm (X) × 25.40 mm (Y) centres. Diameter not dimensioned — MEASURE |
| Headers | 19 pins per row, 2.54 mm pitch, 45.72 mm span; rows 24.94 mm apart |
| USB-C | 8.95 mm wide, on one short edge |
| Antenna | PCB antenna at the **opposite** short edge from the USB-C. **18.00 mm** across the board, centred (drawing). Reaches **~6.4–6.8 mm** in from the end edge (measured off the drawing; Waveshare does not dimension it). Source image with the owner's markup: `docs/sources/esp32-dev-kit-drawing.png` |

All verified from the drawing. One unlabelled 1.27 mm dimension near the left edge is not identified; it doesn't affect anything we need.

**Enclosure consequence:** the antenna end must face a wall clear of wiring, diodes and USB cables, and no carbon-fibre-filled filament near it.

## Input board mechanical (from Waveshare's dimensioned drawing)

| Dimension | Value | Evidence |
|---|---|---|
| Board | 33.00 × 17.50 mm | Drawing (verified) |
| Corner radius | R2.00 | Drawing (verified) |
| USB-C shell width | 8.90 mm (17.50 − 2 × 4.30), centred on the board | Drawing (verified) |
| USB-C shell centre | X = 8.75 mm from either long edge | Calculated |
| Header pad pitch | 2.54 mm; first pad 2.88 mm from the end edge; pad centres 1.13 mm in from the long edge | Drawing (verified) |
| **Retention notches** | Two rectangular cutouts, one in each long edge, **at the PIO-USB (flush-shell) end only**: 1.50 mm deep × 2.00 mm long, near edge 3.45 mm from that edge. Since 2026-10-27 this end faces inward | Measured off the drawing pixel by pixel, ±0.15 mm. **Waveshare does not dimension them** |
| PIO-USB-end corners | R2.00 (confirmed against the measured profile) | Drawing (verified) |
| Native-USB end (faces the hosts) | **No notches.** What looks like notches there is the row of castellated pads, about 0.5 mm deep; the first pads are 2.88 mm from this edge | Measured |
| PCB thickness | **MEASURE** (assume 1.6 mm) | — |
| USB shell height | **MEASURE** (3.26 mm typical) | — |
| Native-USB shell overhang past the board edge | **MEASURE** (1.00 mm assumed in `boards.scad`; the PIO-USB shell is flush) | — |

**Edge layout:** native port up, the **left** edge carries `5V`, `GND`, `3V3`, GPIO29–26, GPIO10, GPIO9 and the **right** edge GPIO0–8 (`docs/sources/rp2350-usb-c-pinout.png`). So power and I2S leave the left side of the board and the UART leaves the right.

## Mounting

**Carrier build:** all three modules solder to the carrier, which mounts on four M2.5 holes (2.7 mm). The ESP32's own holes go unused. The rest of this section describes the loom build.

- **Input boards are held by the enclosure's USB-C wall and cradle, not screws.** Neither the QT Py RP2040 (verified: no mounting holes in Adafruit's board file) nor the RP2350-USB-C is screw-mounted.
- **Out of date since 2026-10-27 for the loom box:** `enclosure/box.scad` holds each board by nubs in its retention notches at the port wall and expects a flush shell there. With the native port facing the hosts, the wall sees the proud shell and the notches are at the inner end. Any enclosure now has to be designed for that (the carrier build needs a new one anyway).
- **ESP32 board: four mounting holes**, 50.04 × 25.40 mm centres (verified from the drawing). Hole diameter is not dimensioned; measure before choosing screws or inserts.

## Passives

Reference designators match the carrier (`hardware/carrier/CONNECTIONS.md`). All through-hole.

| Ref | Part | Job |
|---|---|---|
| D1, D2 | Schottky, DO-41 (1N5819 preferred; 1N5817 works) | Each input board's `5V` → rail. SS14 is surface-mount and does not fit the carrier |
| R1–R4 | 1 kΩ | Series on BCLK and LRCK to each input board, at the ESP32 end |
| R5, R6 | 1 kΩ | Series on each UART TX (ESP32 → input board) |
| R10, R11 | 1 kΩ | Bleed, each input board's `5V` pin to GND |
| C1 | 22 µF ≥ 10 V electrolytic, 5 mm, 2.5 mm pitch | Rail bulk, near the ESP32 |

Every resistor is 1 kΩ. Retired 2026-11-16 as not needed: R7, R8, R9, C2, C3, C4 (review #5).

- The loop-backs (GPIO26 → 32, GPIO14 → 35) connect before the resistors, under the ESP32.
- On the carrier, R1–R6 stand upright (2.54 mm pads), each at the ESP32 pin it serves; R10 and R11 lie flat.
- Keep I2S runs under ~10 cm. On the carrier the longest chain is 73 mm (input 2's audio).
