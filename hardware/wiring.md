# Wiring: ESP32 hub design

2× Adafruit QT Py RP2040 (USB audio inputs) → Adafruit ESP32 Feather V2 (clock master, mixer, Bluetooth A2DP source).

Replaces the earlier RP2040-chain pin map and `docs/HANDOFF.md` §4. Decision: `docs/decisions.md` (2026-09-28).

**Status:** proposed, not yet built. The pin numbers come from the boards' schematics, checked; whether the I2S and UART setup works is untested.

```
                     BCLK, LRCK (ESP32 is clock master)
            ┌───────────────────────┬──────────────────────┐
            │                       │                      │
 Host 1 ─USB─▶ QT Py 1 ──DOUT──▶ ESP32 I2S0 (RX, master)    │
               UART ◀──────────▶ ESP32 UART1               │
                                                           │
 Host 2 ─USB─▶ QT Py 2 ──DOUT──▶ ESP32 I2S1 (RX, slave) ◀──┘ (BCLK/LRCK looped back)
               UART ◀──────────▶ ESP32 UART2

 ESP32: mix + gain + limiter → Bluetooth A2DP (SBC) → headphones
```

## Why the ESP32 uses two I2S peripherals

- The original ESP32 has **two I2S peripherals, each with one data input** in standard mode (TDM support on the original ESP32 is unlikely, ~75% confident).
- **I2S0** runs as **master**: it generates BCLK/LRCK and receives QT Py 1.
- **I2S1** runs as **slave** on the same clocks and receives QT Py 2.
- BCLK and LRCK are **wired back into two input-only pins** for I2S1. Routing them internally is probably possible too (~70% confident), but a physical loop-back wire removes that uncertainty for the cost of two otherwise-idle pins.

## ESP32 Feather V2 pins

From Adafruit's schematic, `Adafruit ESP32 Feather V2.sch`.

| Signal | Feather label | ESP32 GPIO | Direction | Notes |
|---|---|---|---|---|
| BCLK out (I2S0 master) | IO27 | 27 | Out | Through 33 Ω to each QT Py |
| LRCK out (I2S0 master) | IO33 | 33 | Out | Through 33 Ω to each QT Py |
| BCLK loop-back in (I2S1 slave) | A4 | 36 | In (input-only pin) | Short wire from GPIO27 on the Feather itself |
| LRCK loop-back in (I2S1 slave) | A3 | 39 | In (input-only pin) | Short wire from GPIO33 |
| Data in from QT Py 1 (I2S0) | A2 | 34 | In (input-only pin) | |
| Data in from QT Py 2 (I2S1) | I37 | 37 | In (input-only pin) | |
| UART1 TX → QT Py 1 RX | TX | 8 | Out | |
| UART1 RX ← QT Py 1 TX | RX | 7 | In | |
| UART2 TX → QT Py 2 RX | IO32 | 32 | Out | |
| UART2 RX ← QT Py 2 TX | IO14 | 14 | In | |
| Power in | BAT | — | — | From the shared rail, **no diode** (review-notes #14). Never attach a LiPo. |
| Ground | GND | — | — | |

**Pins deliberately avoided:**

- **GPIO12 and GPIO15** are strapping pins; external levels at boot can change boot behaviour.
- **GPIO13** drives the on-board LED.
- **SDA/SCL (GPIO22/20)** are left free for I2C.
- The console UART (UART0) goes to the CP2102N USB-serial chip and stays free for logs and flashing.

Input-only GPIOs 34–39 have no internal pull resistors. That's fine here because every board is always powered together.

## QT Py RP2040 pins (identical on both boards)

| Signal | GPIO (label) | Direction | Notes |
|---|---|---|---|
| BCLK in | 26 (A3) | In | From ESP32 GPIO27 via 33 Ω |
| LRCK in | 27 (A2) | In | From ESP32 GPIO33 via 33 Ω |
| DOUT | 28 (A1) | Out | To the ESP32 data-in pin (34 for board 1, 37 for board 2) |
| DIN (chain input) | 29 (A0) | In | For future expansion (another RP2040 or an ADC). Tie to GND until used. |
| UART TX | 20 (TX) | Out | To the ESP32 UART RX |
| UART RX | 5 (RX) | In | From the ESP32 UART TX |
| Debug serial TX (PIO) | 3 (MOSI) | Out | Optional, to a USB-serial adapter |
| VBUS sense (optional) | 24 (SDA) | In | From the VBUS side of JP2 via a 10k/20k divider; probably unnecessary |

## Power

| From | To |
|---|---|
| QT Py 1 `5V` pin | QT Py 2 `5V` pin, Feather `BAT` pin, 22 µF + 0.1 µF near the Feather |
| All GND | All GND |

- Each QT Py's `5V` pin sits behind its own onboard Schottky (verified), so the two hosts never connect to each other.
- The rail is ~4.6–4.8 V (estimate).
- **Don't bridge JP2** on either QT Py.

## Parts at the split point (perfboard)

- **4 × 33 Ω:** BCLK → QT Py 1, BCLK → QT Py 2, LRCK → QT Py 1, LRCK → QT Py 2. Place them at the ESP32 end.
- The loop-back wires (GPIO27 → 36, GPIO33 → 39) connect before the resistors, right at the Feather.
- Keep I2S runs under ~10 cm.
