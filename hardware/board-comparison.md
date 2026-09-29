# USB-C RP2040 / RP2350 board comparison (power path)

Checked 2026-09-24; RP2350-USB-C added 2026-09-29.

> **Outcome:** the owner chose the **Waveshare RP2350-USB-C** on 2026-09-29, accepting that it needs an external Schottky per board. See `docs/decisions.md` and review-notes #20. The QT Py analysis below is kept because it still documents what the power path has to achieve.

**What this project needs from a board:**

1. A diode between USB VBUS and a header pin, so both boards can share one rail without connecting the two computers' 5V.
2. 5.1 kΩ CC resistors, so C-to-C cables supply power.
3. A reachable VBUS point, for "is a computer connected" sensing (optional, see below).
4. USB-C at the board edge, so the port can come straight through the enclosure wall.

**How each row was checked:**

- **Schematic:** read from the manufacturer's published schematic file (Eagle `.sch`, cloned from GitHub). The netlist shows the connections directly.
- **Text:** manufacturer text seen through search results. The schematic couldn't be fetched from this environment.
- **Unverified:** no source reached.

## Summary

| Board | VBUS → header diode | CC 5.1k | VBUS tap for sensing | Evidence |
|---|---|---|---|---|
| **Waveshare RP2350-USB-C** (chosen) | **No.** Both USB-C ports' VBUS go straight to the `VSYS` net and the `VSYS` header pin. No diode anywhere on the board. **Needs an external Schottky per board.** | **Yes** (R5/R6 on port 1, R10/R13 on port 2) | `VSYS` header pin (it is VBUS) | Schematic (github.com/waveshareteam/RP2350-USB-C) |
| **Adafruit QT Py RP2040** (superseded) | **Yes:** VBUS → D1 (NSR0320) → `+5V` pin | **Yes** (R12, R13) | JP2 solder-jumper pad (VBUS side) | Schematic |
| **Adafruit KB2040** | **Yes:** VBUS → fuse → D1 (NSR0320) → `RAW` pin | **Yes** (R1, R2) | SJ1 solder-jumper pad | Schematic |
| **SparkFun Pro Micro RP2040** | **Yes:** VBUS → PPTC fuse → D2 Schottky (280 mV) → `RAW` pin | **Yes** (R1, R3) | JP14 "USB solder pads" | Schematic |
| Adafruit Feather RP2040 | Yes, VBUS → MBR540 → VHI. But VHI isn't on a header; only the `USB` pin (raw VBUS) and `BAT` are. | Yes | `USB` pin | Schematic |
| SB Components Micro RP2040 | **No:** USB VBUS goes straight to the `5V` net and header pin | **No:** CC1/CC2 are unconnected in the schematic, so C-to-C cables won't supply power | `5V` header pin (it is VBUS) | Schematic (PDF from github.com/sbcshop/Micro_RP2040, v1.0, 2023-04-28) |
| Waveshare RP2040-Zero | **No.** The 5V pin *is* VBUS. | Unverified | 5V pin | Text |
| Seeed XIAO RP2040 | Unverified. Seeed advises adding your own diode when powering through the 5V pin, which suggests no onboard diode on that path. | Unverified | Unverified | Text (indirect) |
| Pimoroni Tiny 2040 | Unverified | Unverified | Unverified | None |

Solder jumpers JP2 (QT Py) and SJ1 (KB2040) join two *different* nets in the schematic, so they're open by default. That leaves the diode in circuit. Confidence ~90%.

## Consequences for this design

- On the QT Py, KB2040, and Pro Micro RP2040, the handoff's original power idea works as intended. **Tie the two boards' `+5V` / `RAW` pins together.** The onboard diodes combine both USB supplies and the computers never connect to each other.
- **The rail is about 4.25–5.2 V, typically ~4.65 V (estimate; review-notes #18)**: the host's VBUS minus cable drop minus one Schottky drop. Measure it on the built box. The TSA5001 voltage question from the handoff still stands.
- **Each host sees both boards' 10 µF input caps plus the added capacitor.** That's about 20 µF + 22 µF, over the USB 10 µF plug-in limit. Low practical risk (see review-notes #3).
- **VBUS sensing may not be needed.** With the cable unplugged, the board sees no USB frames, and TinyUSB reports "suspended".
  - Firmware can treat "not mounted or suspended" as "contribute zeros". That's the same behavior the handoff wanted from GPIO24.
  - Confidence ~75%. Sensing is still cheap to add from the solder-jumper pad: a 10k/20k divider to a GPIO.

## Recommendation (not a decision), as written 2026-09-24

**QT Py RP2040.** It's small (PCB outline 20.7 × 17.8 mm from the board file; the USB-C shell may overhang), has edge USB-C, and has all three power features confirmed from the schematic. It exposes about 11 GPIOs; this project needs about 6.

## What changed on 2026-09-29

The owner chose the **Waveshare RP2350-USB-C** instead, for its RAM. The comparison above ranks boards by power path alone, which is only one axis.

| | QT Py RP2040 | RP2350-USB-C |
|---|---|---|
| RAM | 264 KB | **520 KB** |
| Flash | 8 MB | 2 MB (W25Q16) |
| PIO blocks | 2 | 3 |
| Size | 20.7 × 17.8 mm | 33.0 × 17.5 mm (sourced, not measured) |
| USB-C ports | 1, at the edge | 2, one at each end. The inner one is unused and stays inside the case |
| Exposed GPIOs | ~11 | 15 (GPIO0–10, 26–29) |
| VBUS diode | Onboard | **External, owner-fitted** |

The deciding factor was RAM: fitting USB audio, lwIP and the web server on one chip is the highest firmware risk in `docs/architecture.md`, and doubling RAM attacks it directly. A missing diode is a part the owner already has; RAM is not.

**KB2040 or Pro Micro RP2040** if you want more pins or bigger solder pads. The Pro Micro's PPTC fuse is a nice extra. Their longer 33 × 18 mm Pro Micro footprint makes wall-mounting slightly easier.

## Sources

- Adafruit QT Py RP2040 design files: https://github.com/adafruit/Adafruit-QT-Py-RP2040-PCB
- Adafruit KB2040 design files: https://github.com/adafruit/Adafruit-KB2040-PCB
- Adafruit Feather RP2040 design files: https://github.com/adafruit/Adafruit-Feather-RP2040-PCB
- SparkFun Pro Micro RP2040 design files: https://github.com/sparkfun/SparkFun_Pro_Micro-RP2040
- SB Components Micro RP2040 schematic: https://github.com/sbcshop/Micro_RP2040
- Waveshare RP2040-Zero wiki: https://www.waveshare.com/wiki/RP2040-Zero
- Seeed XIAO RP2040 wiki: https://wiki.seeedstudio.com/XIAO-RP2040/
