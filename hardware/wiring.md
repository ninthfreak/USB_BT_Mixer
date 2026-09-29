# Wiring: ESP32 hub design

2× **Waveshare RP2350-USB-C** (USB audio inputs) → **Waveshare ESP32-DEV-KIT-WROOM-32E-N4** (clock master, mixer, Bluetooth A2DP source).

Replaces the earlier RP2040-chain pin map and `docs/HANDOFF.md` §4. Board decisions: `docs/decisions.md` (2026-09-29). The earlier QT Py RP2040 + Feather V2 pin map is superseded; see review-notes #20 for why the boards changed.

**Status:** proposed, not yet built. Pin numbers come from the boards' schematics, checked. Whether the I2S and UART setup works is untested.

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
- BCLK and LRCK are **wired back into two input-only pins** for I2S1. Routing them internally is probably possible too (~70% confident), but a physical loop-back wire removes that uncertainty for the cost of two otherwise-idle pins.

## ESP32 board pins (Waveshare ESP32-DEV-KIT-WROOM-32E-N4)

From Waveshare's schematic `ESP32-DEV-KIT-XX.pdf` (Altium, dated 2026-09-09). Header J3 is the left side, J4 the right.

| Signal | ESP32 GPIO | Header | Direction | Notes |
|---|---|---|---|---|
| BCLK out (I2S0 master) | 25 | J3 | Out | Through 33 Ω to each input board |
| LRCK out (I2S0 master) | 33 | J3 | Out | Through 33 Ω to each input board |
| BCLK loop-back in (I2S1 slave) | 36 (SENSOR_VP) | J3 | In (input-only pin) | Short wire from GPIO25 at the board |
| LRCK loop-back in (I2S1 slave) | 39 (SENSOR_VN) | J3 | In (input-only pin) | Short wire from GPIO33 |
| Data in from input 1 (I2S0) | 35 | J3 | In (input-only pin) | |
| Data in from input 2 (I2S1) | 26 | J3 | In | |
| UART1 TX → input 1 RX | 17 | J4 | Out | |
| UART1 RX ← input 1 TX | 16 | J4 | In | |
| UART2 TX → input 2 RX | 19 | J4 | Out | |
| UART2 RX ← input 2 TX | 18 | J4 | In | |
| Power in | VSYS | J3 pin 19 | — | From the shared rail. See **Power** below |
| Ground | GND | J3 / J4 | — | |

All I2S signals land on J3 and both UARTs on J4, so the two harnesses stay separate.

**Pins deliberately avoided on this board:**

| Pin | Why |
|---|---|
| GPIO27 | Drives the onboard WS2812 RGB LED through R1 (0 Ω). Free it by removing R1 if ever needed |
| GPIO34 | Battery-voltage divider (200 k / 100 k) through R28 (0 Ω) |
| GPIO12, GPIO15 | Strapping pins (MTDI, MTDO); external levels at boot change boot behaviour |
| GPIO0, GPIO2, GPIO5 | Strapping pins, and GPIO0 is on the auto-download circuit |
| TXD0 / RXD0 | Console UART to the CH343P USB-serial chip; keep free for logs and flashing |
| SD0–SD3, CMD, CLK | Module flash |

Input-only GPIOs 34–39 have no internal pull resistors. That's fine here because every board is always powered together.

Assumed, not verified: GPIO16 and GPIO17 are free because the N4 variant has no PSRAM. Check against the module datasheet before building.

## Input board pins (Waveshare RP2350-USB-C, identical on both)

From Waveshare's schematic `RP2350-USB-C.pdf` (github.com/waveshareteam/RP2350-USB-C). The 18-pin header exposes GPIO0–10, GPIO26–29, 3V3, GND and VSYS.

| Signal | GPIO | Direction | Notes |
|---|---|---|---|
| BCLK in | 26 | In | From ESP32 GPIO25 via 33 Ω |
| LRCK in | 27 | In | From ESP32 GPIO33 via 33 Ω |
| DOUT | 28 | Out | To the ESP32 data-in pin (35 for board 1, 26 for board 2) |
| DIN (chain input) | 29 | In | For future expansion (another input board or an ADC). Tie to GND until used |
| UART TX | 4 | Out | UART1 TX → the ESP32 UART RX |
| UART RX | 5 | In | UART1 RX ← the ESP32 UART TX |
| Debug serial TX (PIO) | 3 | Out | Optional, to a USB-serial adapter |
| VBUS sense (optional) | any spare (0, 1, 2, 6–10) | In | From the board's `VSYS` pin via a 10k/20k divider. `VSYS` is raw VBUS here, so no solder jumper is needed. Probably unnecessary |

Not on the header, so no conflict: GPIO12/13 (second USB-C port, PIO-USB), GPIO16 (RGB LED).

**Erratum RP2350-E9** (input-mode pull-down latching / leakage) does not apply to any pin above: all are driven, and none relies on an internal pull-down. Confirm during bring-up.

## Power

**The RP2350-USB-C has no VBUS diode.** Its USB-C VBUS connects straight to the `VSYS` net and the `VSYS` header pin (verified from the schematic). Both of its USB-C ports share that net. So each input board needs **its own external Schottky** before the shared rail, or the two hosts' 5 V rails would be tied together.

```
Host 1 ─USB-C─▶ board 1 VSYS ──▶|── ┐
                                    ├── shared rail ──▶ ESP32 VSYS pin (J3-19)
Host 2 ─USB-C─▶ board 2 VSYS ──▶|── ┘
                (D1, D2: your Schottkys, cathode to the rail)
```

| From | To |
|---|---|
| Input board 1 `VSYS` | D1 anode |
| Input board 2 `VSYS` | D2 anode |
| D1 + D2 cathodes | Shared rail → ESP32 `VSYS` (J3-19), 22 µF + 0.1 µF near the ESP32 |
| All GND | All GND |

- **Diode orientation matters:** the banded end (cathode) goes to the rail. Check with a multimeter's diode range before powering anything.
- Each input board's own 3.3 V regulator (RT9013) is fed from its USB VBUS *before* the diode, so it keeps full headroom.
- The rail is about 4.25–5.2 V, typically ~4.65 V (estimate; review-notes #18): VBUS minus cable drop minus one Schottky drop. Measure it on the built box.
- **The ESP32 board's own USB-C is protected:** its VBUS reaches VSYS through D3 (MBR230, onboard). Plugging a laptop into it for flashing does not back-feed the rail past the input boards' diodes, and the rail does not appear on its USB-C. **You can flash the ESP32 with the box powered.**
- The ESP32 board's MP1605 converter accepts 2.3–5.5 V in (schematic note), covering the whole rail range with ~0.3 V to spare at the top.
- The ESP32 board's ETA6098 charger sits on the same VSYS net. With no battery fitted it should stay idle (estimate ~85%; its absolute-maximum ratings are unverified). Never fit a battery to its GH1.25 connector.
- **The second USB-C port on each input board is live on `VSYS`.** Anything plugged into it lands on that board's VBUS, on the host side of the diode. Leave both inner ports unused and unreachable inside the case.

## Parts at the split point (perfboard)

- **2 × Schottky diode** (e.g. 1N5817, SS14, or any low-Vf part rated ≥ 1 A): one per input board, `VSYS` → rail.
- **4 × 33 Ω:** BCLK → board 1, BCLK → board 2, LRCK → board 1, LRCK → board 2. Place them at the ESP32 end.
- The loop-back wires (GPIO25 → 36, GPIO33 → 39) connect before the resistors, right at the ESP32 board.
- Keep I2S runs under ~10 cm.
