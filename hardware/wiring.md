# Wiring: ESP32 hub design

2× **Waveshare RP2350-USB-C** (USB audio inputs) → **Waveshare ESP32-DEV-KIT-WROOM-32E-N4** (clock master, mixer, Bluetooth A2DP source).

Replaces the earlier RP2040-chain pin map and `docs/HANDOFF.md` §4. Board decisions: `docs/decisions.md` (2026-09-29). The earlier QT Py RP2040 + Feather V2 pin map is superseded; see review-notes #20 for why the boards changed.

**Status:** proposed, not yet built. Pin numbers come from the boards' schematics, checked. Whether the I2S and UART setup works is untested.

**Build route:** the three modules now solder flat onto a carrier PCB (`hardware/carrier/`; chosen 2026-10-26, see `docs/decisions.md`). The connections below are the same either way. `hardware/carrier/netlist.py` is the source of truth for them; this page explains the reasons. Changed on 2026-10-26 after the carrier audit: clock loop-backs moved to IO13/IO32, series resistors raised to 1 kΩ and added on UART TX, pull-downs added. See `hardware/carrier/AUDIT.md`.

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
- BCLK and LRCK are **wired back into two spare GPIOs** (IO13, IO32) for I2S1. Routing them internally is probably possible too (~70% confident), but a physical loop-back removes that uncertainty for the cost of two otherwise-idle pins.

## ESP32 board pins (Waveshare ESP32-DEV-KIT-WROOM-32E-N4)

From Waveshare's schematic `ESP32-DEV-KIT-XX.pdf` (Altium, dated 2026-09-09). Header J3 is the left side, J4 the right.

| Signal | ESP32 GPIO | Header | Direction | Notes |
|---|---|---|---|---|
| BCLK out (I2S0 master) | 25 | J3 | Out | Through 1 kΩ to each input board (R1, R2) |
| LRCK out (I2S0 master) | 33 | J3 | Out | Through 1 kΩ to each input board (R3, R4) |
| BCLK loop-back in (I2S1 slave) | 13 | J3 | In | Short link from GPIO25, before the resistors. GPIO13 is also JTAG MTCK; only matters if JTAG is wanted |
| LRCK loop-back in (I2S1 slave) | 32 | J3 | In | Short link from GPIO33, before the resistors |
| Data in from input 1 (I2S0) | 35 | J3 | In (input-only pin) | 100 kΩ pull-down (R7): no internal pull on this pin |
| Data in from input 2 (I2S1) | 26 | J3 | In | Enable the internal pull-down in firmware |
| UART1 TX → input 1 RX | 17 | J4 | Out | Through 1 kΩ (R5) |
| UART1 RX ← input 1 TX | 16 | J4 | In | |
| UART2 TX → input 2 RX | 19 | J4 | Out | Through 1 kΩ (R6) |
| UART2 RX ← input 2 TX | 18 | J4 | In | |
| Power in | `5V` (net VSYS) | J3 pin 19 | — | From the shared rail. See **Power** below |
| Ground | GND | J3 / J4 | — | |

All I2S signals land on J3 and both UARTs on J4, so the two harnesses stay separate.

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

**Not every board is always powered.** With only one host connected, that input board and the ESP32 run (through its diode), but the other input board is unpowered: its diode stops the rail reaching it, by design. Two consequences, both handled:

- **Back-feed.** The ESP32 keeps driving BCLK, LRCK and UART TX into the unpowered board. Without limiting, current flows through that chip's ESD diodes into its dead 3V3 rail. The 1 kΩ series resistors cut this to about 3 mA per pin. At 2.8 MHz with ~10 pF of load, 1 kΩ still gives ~22 ns edges against a 177 ns half-period. (~90% confident in the mechanism; the RP2350's exact injection limit is not verified.)
- **Floating data inputs.** The unpowered board's DOUT floats. GPIO35 is input-only with no internal pull, so it gets a 100 kΩ pull-down; GPIO26 can use its internal one.

GPIO16 and GPIO17 are free: the schematic names U1 as **ESP32-WROOM-32E-N4** (no PSRAM, so nothing claims those pins), and both appear on J4 with nothing else attached. ~95% confident; the remaining doubt is only that I haven't read the module datasheet itself.

## Input board pins (Waveshare RP2350-USB-C, identical on both)

From Waveshare's schematic `RP2350-USB-C.pdf` (github.com/waveshareteam/RP2350-USB-C). The 18-pin header exposes GPIO0–10, GPIO26–29, 3V3, GND and the raw-VBUS pin.

**Naming:** the schematic calls this net `VSYS`, but **the silkscreen reads `5V`** — and the owner has confirmed the same is true on the ESP32 board. So **both boards are silkscreened `5V`** for what the schematics call VSYS. Below, "the `5V` pin" means that net on either board. It is the raw supply, not regulated 3.3 V.

| Signal | GPIO | Direction | Notes |
|---|---|---|---|
| BCLK in | 26 | In | From ESP32 GPIO25 via 1 kΩ |
| LRCK in | 27 | In | From ESP32 GPIO33 via 1 kΩ |
| DOUT | 28 | Out | To the ESP32 data-in pin (35 for board 1, 26 for board 2) |
| DIN (chain input) | 29 | In | For future expansion (another input board or an ADC). Pulled to GND through 4.7 kΩ (R8/R9) until used; leave the resistor out to free the pin |
| UART TX | 4 | Out | UART1 TX → the ESP32 UART RX |
| UART RX | 5 | In | UART1 RX ← the ESP32 UART TX, via 1 kΩ |
| Debug serial TX (PIO) | 3 | Out | Optional, to a USB-serial adapter |
| VBUS sense (optional) | any spare (0, 1, 2, 6–10) | In | From the board's `5V` pin via a 10k/20k divider. That pin is raw VBUS here, so no solder jumper is needed. Probably unnecessary |

Not on the header, so no conflict: GPIO12/13 (second USB-C port, PIO-USB), GPIO16 (RGB LED).

**Erratum RP2350-E9** (input-mode pull-down latching / leakage) does not apply to the driven pins above. GP29 is the one idle input; its external 4.7 kΩ pull-down holds it low against the erratum's leakage (up to ~120 µA → ~0.56 V). Confirm during bring-up.

## Power

**The RP2350-USB-C has no VBUS diode.** Its USB-C VBUS connects straight to the `VSYS` net and the header pin silkscreened `5V` (verified from the schematic). Both of its USB-C ports share that net. So each input board needs **its own external Schottky** before the shared rail, or the two hosts' 5 V rails would be tied together.

```
Host 1 ─USB-C─▶ board 1 `5V` ──▶|── ┐
                                    ├── shared rail ──▶ ESP32 `5V` pin (J3-19)
Host 2 ─USB-C─▶ board 2 `5V` ──▶|── ┘
                (D1, D2: your Schottkys, cathode to the rail)
```

| From | To |
|---|---|
| Input board 1 `5V` pin | D1 anode |
| Input board 2 `5V` pin | D2 anode |
| D1 + D2 cathodes | Shared rail → ESP32 `5V` pin (J3-19), 22 µF (C1) + 0.1 µF (C2) near the ESP32 |
| Each input board's `5V` pin | 0.1 µF to GND (C3, C4), beside the diode |
| All GND | All GND |

- **Diode orientation matters:** the banded end (cathode) goes to the rail. On the carrier, the band goes on the end with the square pad and the "K" mark. Check with a multimeter's diode range before powering anything.
- Each input board's own 3.3 V regulator (RT9013) is fed from its USB VBUS *before* the diode, so it keeps full headroom.
- The rail is about 4.25–5.2 V, typically ~4.65 V (estimate; review-notes #18): VBUS minus cable drop minus one Schottky drop. Measure it on the built box.
- **The ESP32 board's own USB-C is protected:** its VBUS reaches VSYS through D3 (MBR230, onboard). Plugging a laptop into it for flashing does not back-feed the rail past the input boards' diodes, and the rail does not appear on its USB-C. **You can flash the ESP32 with the box powered.**
- The ESP32 board's MP1605 converter accepts 2.3–5.5 V in (schematic note), covering the whole rail range with ~0.3 V to spare at the top.
- The ESP32 board's ETA6098 charger sits on the same VSYS net. With no battery fitted it should stay idle (estimate ~85%; its absolute-maximum ratings are unverified). Never fit a battery to its GH1.25 connector.
- **The second USB-C port on each input board is live on that same net.** Anything plugged into it lands on that board's VBUS, on the host side of the diode. Leave both inner ports unused and unreachable inside the case.

## ESP32 board mechanical (from Waveshare's dimensioned drawing)

| Dimension | Value |
|---|---|
| Board | 53.80 × 27.94 mm |
| Mounting holes | **Four**, at 50.04 mm (X) × 25.40 mm (Y) centres. Diameter not dimensioned — MEASURE |
| Headers | 19 pins per row, 2.54 mm pitch, 45.72 mm span; rows 24.94 mm apart |
| USB-C | 8.95 mm wide, on one short edge |
| Antenna | PCB antenna at the **opposite** short edge from the USB-C. Its exact extent is not dimensioned |

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
| **Retention notches** | Two rectangular cutouts, one in each long edge, **at the port end only**: 1.50 mm deep × 2.00 mm long, near edge 3.45 mm from the port edge | Measured off the drawing pixel by pixel, ±0.15 mm. **Waveshare does not dimension them** |
| Port-end corners | R2.00 (confirmed against the measured profile) | Drawing (verified) |
| Inner end | **No notches.** What looks like notches there is the row of castellated pads, about 0.5 mm deep | Measured |
| PCB thickness | **MEASURE** (assume 1.6 mm) | — |
| USB shell height | **MEASURE** (3.26 mm typical) | — |
| USB shell overhang past the board edge | **MEASURE** (1.03 mm on the QT Py) | — |

**Edge layout:** the `5V`, `GND`, `3V3` and GPIO26–29 pads are all on **one** long edge; GPIO0–10 are on the other. So power and I2S leave one side of the board and the UART leaves the other.

## Mounting

**Carrier build:** all three modules solder to the carrier, which mounts on four M2.5 holes (2.7 mm). The ESP32's own holes go unused. The rest of this section describes the loom build.

- **Input boards are held by the enclosure's USB-C wall and cradle, not screws.** Neither the QT Py RP2040 (verified: no mounting holes in Adafruit's board file) nor the RP2350-USB-C is screw-mounted. This is unchanged by the board swap; only the cradle dimensions change.
- **ESP32 board: four mounting holes**, 50.04 × 25.40 mm centres (verified from the drawing). Hole diameter is not dimensioned; measure before choosing screws or inserts.

## Passives

Reference designators match the carrier (`hardware/carrier/CONNECTIONS.md`). All through-hole.

| Ref | Part | Job |
|---|---|---|
| D1, D2 | Schottky, DO-41 (1N5817 / 1N5819) | Each input board's `5V` → rail. SS14 is surface-mount and does not fit the carrier |
| R1–R4 | 1 kΩ | Series on BCLK and LRCK to each input board, at the ESP32 end |
| R5, R6 | 1 kΩ | Series on each UART TX (ESP32 → input board) |
| R7 | 100 kΩ | Pull-down on AUD1 (GPIO35) |
| R8, R9 | 4.7 kΩ | Pull-down on each input board's GP29. Optional |
| C1 | 22 µF ≥ 10 V electrolytic, 5 mm, 2.5 mm pitch | Rail bulk, near the ESP32 |
| C2 | 0.1 µF ceramic | Rail decoupling at the ESP32 |
| C3, C4 | 0.1 µF ceramic | Each input board's `5V` pin |

- The loop-backs (GPIO25 → 13, GPIO33 → 32) connect before the resistors, right at the ESP32.
- Keep I2S runs under ~10 cm. On the carrier the longest chain is under 65 mm.
