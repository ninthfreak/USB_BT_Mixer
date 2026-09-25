# USB-C RP2040 board comparison (power path)

Checked 2026-09-24.

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
| **Adafruit QT Py RP2040** | **Yes:** VBUS → D1 (NSR0320) → `+5V` pin | **Yes** (R12, R13) | JP2 solder-jumper pad (VBUS side) | Schematic |
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
- **The rail is about 4.6–4.8 V**, which is VBUS minus one Schottky drop. The TSA5001 voltage question from the handoff still stands.
- **Each host sees both boards' 10 µF input caps plus the added capacitor.** That's about 20 µF + 22 µF, over the USB 10 µF plug-in limit. Low practical risk (see review-notes #3).
- **VBUS sensing may not be needed.** With the cable unplugged, the board sees no USB frames, and TinyUSB reports "suspended".
  - Firmware can treat "not mounted or suspended" as "contribute zeros". That's the same behavior the handoff wanted from GPIO24.
  - Confidence ~75%. Sensing is still cheap to add from the solder-jumper pad: a 10k/20k divider to a GPIO.

## Recommendation (not a decision)

**QT Py RP2040.** It's small (PCB outline 20.7 × 17.8 mm from the board file; the USB-C shell may overhang), has edge USB-C, and has all three power features confirmed from the schematic. It exposes about 11 GPIOs; this project needs about 6.

**KB2040 or Pro Micro RP2040** if you want more pins or bigger solder pads. The Pro Micro's PPTC fuse is a nice extra. Their longer 33 × 18 mm Pro Micro footprint makes wall-mounting slightly easier.

## Sources

- Adafruit QT Py RP2040 design files: https://github.com/adafruit/Adafruit-QT-Py-RP2040-PCB
- Adafruit KB2040 design files: https://github.com/adafruit/Adafruit-KB2040-PCB
- Adafruit Feather RP2040 design files: https://github.com/adafruit/Adafruit-Feather-RP2040-PCB
- SparkFun Pro Micro RP2040 design files: https://github.com/sparkfun/SparkFun_Pro_Micro-RP2040
- SB Components Micro RP2040 schematic: https://github.com/sbcshop/Micro_RP2040
- Waveshare RP2040-Zero wiki: https://www.waveshare.com/wiki/RP2040-Zero
- Seeed XIAO RP2040 wiki: https://wiki.seeedstudio.com/XIAO-RP2040/
