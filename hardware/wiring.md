# Wiring: Adafruit QT Py RP2040 ×2 + TSA5001

This replaces the wiring table in `docs/HANDOFF.md` section 4. The handoff's GP10–GP13 aren't brought out on the QT Py.

## QT Py GPIOs on the headers

Verified from Adafruit's schematic (`Adafruit QT Py RP2040.sch`):

| Label | GPIO | | Label | GPIO |
|---|---|---|---|---|
| A0 | 29 | | SDA | 24 |
| A1 | 28 | | SCL | 25 |
| A2 | 27 | | TX | 20 |
| A3 | 26 | | RX | 5 |
| MOSI | 3 | | SCK | 6 |
| MISO | 4 | | STEMMA QT connector | 22, 23 |

Not on headers: GP11 (NeoPixel power), GP12 (NeoPixel data), GP21 (BOOT button).
Crystal: 12 MHz (verified), so the clock math in review-notes #2 holds.

## Proposed pin map (same on both boards)

BCLK and LRCK must be **consecutive GPIOs** (BCLK = base, LRCK = base + 1) for the usual PIO side-set I2S master.

| Signal | GPIO (label) | Board A (master, last) | Board B (slave) |
|---|---|---|---|
| BCLK 3.072 MHz | 26 (A3) | Output, via 33 Ω to B and via 33 Ω to TSA5001 | Input |
| LRCK 48 kHz | 27 (A2) | Output, via 33 Ω to B and via 33 Ω to TSA5001 | Input |
| DOUT | 28 (A1) | → TSA5001 SD | → Board A GP29 |
| DIN | 29 (A0) | ← Board B GP28 | Tied to GND (chain start) |
| Debug UART TX | 20 (TX) | → USB-serial adapter RX | → USB-serial adapter RX |
| VBUS sense (optional) | 24 (SDA) | From the VBUS side of solder jumper JP2 via a 10k/20k divider | Same |
| Pairing trigger (optional) | 3 (MOSI) | → NPN/N-MOSFET across the TSA5001 pairing header | Unused |

## Power

| From | To |
|---|---|
| Board A `5V` pin | Board B `5V` pin, TSA5001 +, 22 µF cap |
| All GND | All GND |

- Each board's `5V` pin sits **after** its onboard NSR0320 Schottky (verified), so tying them together is safe.
- **Don't** bridge solder jumper JP2 on either board. That would bypass the diode.
- The rail is about 4.6–4.8 V. The TSA5001 minimum input voltage is still unverified.

Status: proposed, not yet built. Pin choice confidence ~85%. The main risk is a PIO constraint I haven't hit yet, and it's easy to change.
