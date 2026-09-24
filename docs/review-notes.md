# Review notes on the handoff

Checked 2026-09-24. These are corrections and added risks. The items are *not* yet verified on hardware.

## 1. USB-C panel extensions may not get power from USB-C hosts (important)

- **Problem:** a USB-C host (a laptop's C port, a phone) only turns on VBUS when it sees a **5.1 kΩ pull-down (Rd) on CC**. Many cheap "USB-C female → micro-USB male" panel extensions don't have it.
- **Symptom:** it works with a USB-A → C cable, but a C-to-C cable gives no power and no enumeration.
- **Fix options:**
  - Buy extensions that state "5.1k resistor" / "works with C-to-C", then test with a C-to-C cable when they arrive.
  - Or use a USB-C breakout board with Rd on CC1 and CC2, wired to the Pico's USB test pads (TP2/TP3 = D−/D+) or a cut micro-USB cable.
- **Confidence the problem is real:** ~90%. Whether a given listing has Rd: unknown until tested.

## 2. System clock: 153.6 MHz is an overclock

| Clock | × BCLK | RP2040 (Pico) rating 133 MHz | RP2350 (Pico 2) rating 150 MHz |
|---|---|---|---|
| 76.8 MHz | 25 | In spec | In spec |
| 153.6 MHz | 50 | Over spec (SDK 2.1.1+ treats up to 200 MHz as supported, ~85% sure of that) | ~2% over spec |

- **Recommendation:** start at **76.8 MHz** (VCO 768 MHz, /5 /2). It divides evenly, and it's in spec on both chips.
- A slave PIO still gets ~12 cycles per BCLK half-period, which is enough to follow edges.
- Move to 153.6 MHz only if CPU time runs short.
- Note: jitter here doesn't affect sound quality (the TSA5001 re-encodes digitally). The integer divider mostly helps cleaner analyzer captures.
- Confidence: ~80% that 76.8 MHz leaves enough CPU for TinyUSB plus mixing. The load is light (48k stereo frames/s).

Full list of integer options from the 12 MHz crystal (≤ 210 MHz): 30.72, 46.08, 61.44, 76.8, 153.6 MHz.

## 3. Rail capacitance vs. the USB spec

- USB 2.0 caps plug-in capacitance at **10 µF** unless you limit inrush current. The handoff says ≤ 47 µF.
- Each host sees all the VSYS capacitance through its diode: Pico A's + Pico B's onboard caps + the added capacitor.
- **Practical risk: low.** Most hosts tolerate it. At worst you'd see a brief brown-out or a port-overcurrent message on plug-in.
- **Recommendation:** start at 22 µF. Go up only if the TSA5001 drops out under load.

## 4. Firmware: only connect USB when VBUS is present

- Pico B gets power from Pico A's side even when its own cable is unplugged.
- Firmware should call `tud_connect()` only while GPIO24 reads high, and `tud_disconnect()` when it goes low. Otherwise it drives the D+ pull-up into a dead cable.
- Low risk either way, but it's cleaner.

## 5. Pico 2 (RP2350) erratum E9

- On RP2350 A2 silicon, an input pin with the **internal pull-down** enabled can latch at ~2 V.
- It doesn't affect pins driven by Pico A or tied hard to GND.
- If you use Pico 2 boards, **disable internal pull-downs** on the I2S input pins.
- Confidence: ~85% that it's harmless in this design with pulls off.
