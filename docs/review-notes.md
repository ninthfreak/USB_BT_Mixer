# Review notes on the handoff

Checked 2026-09-24. These are corrections and added risks. The items are *not* yet verified on hardware.

## 1. Board choice: the handoff says Pico, the plan was a USB-C RP2040 board

- The handoff specifies a micro-USB Raspberry Pi Pico plus panel extensions. The real plan was a **USB-C RP2040 board** (Waveshare, Adafruit, or Seeed), with its **port exposed directly through the enclosure wall**. No extension cables.
- Anything in the handoff that depends on the Pico board is suspect:
  - **Power sharing:** the Pico has an onboard VBUS → VSYS Schottky. Other boards may tie their 5V pin straight to VBUS. If so, tying the two boards' 5V pins together **connects both computers' 5V rails**. Each board then needs its own external Schottky.
  - **VBUS sense:** GPIO24 is Pico-only. Plan on a resistor divider from each board's VBUS (before any diode) to a spare GPIO.
  - **CC resistors (5.1 kΩ Rd):** needed for C-to-C cables to supply power. Most USB-C boards have them. Verify per board.
- Enclosure impact: the board's USB-C receptacle takes the plug forces directly. The enclosure must back the board so that plugging and unplugging don't load the solder joints.

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

## 6. RP2040-Zero power path (board under consideration)

- **Source-verified:** on the RP2040-Zero, the **5V pin is wired straight to USB VBUS**, with no diode. The board has no power-path circuitry, only the ME6211 3.3 V LDO. (Waveshare wiki text, seen through search results. The schematic PDF couldn't be fetched from this environment.)
- **Consequence:** the handoff's "tie the two VSYS pins together" becomes "tie two computers' VBUS together". **Don't do it.**
- **Consequence 2:** Board A is the only clock source and the only output. If only Board B's cable is plugged in, Board A must still get power, so a shared rail is required.
- Candidate fixes are in the chat log and not yet chosen. Test to run: power one Zero's 3V3 pin from a bench supply with USB unplugged, and measure the 5V pin. That shows whether the ME6211 back-feeds VBUS.
- **CC resistors:** not verified. Test with a C-to-C cable into a laptop.

## 7. Board comparison

See `hardware/board-comparison.md`. The QT Py RP2040, KB2040, and Pro Micro RP2040 all have an onboard VBUS diode and CC resistors (confirmed from schematics). The shared-rail power design works on them as originally intended.

## 8. Board chosen: Adafruit QT Py RP2040

Sections 4–6 above that assume a Pico or Pico 2 are superseded:

- GPIO24 VBUS sense → optional divider from JP2, or firmware-only detection (see `hardware/board-comparison.md`).
- Erratum E9 (#5) → moot. The QT Py is RP2040, not RP2350.
- Wiring → `hardware/wiring.md`.

## 9. Volume control: omitting it likely breaks macOS

- The handoff says to leave the volume control out of the USB descriptor and let the OS apply software volume.
- **Windows** does that. **macOS generally doesn't.** It greys out the volume slider for devices that expose no volume control (the same as with HDMI). Confidence ~85%.
- **Recommendation:** keep the Feature Unit (volume + mute), as TinyUSB's `uac2_speaker_fb` example already does, and apply the gain per board in firmware. Each computer's slider then still sets its level in the mix.
- Difficulty 2/10.

## 10. TinyUSB feedback: verified against current source

Checked against the TinyUSB master branch cloned 2026-09-24:

- The `uac2_speaker_fb` example exists.
- The buffer-fill method is `AUDIO_FEEDBACK_METHOD_FIFO_COUNT`, set in `tud_audio_feedback_params_cb()`. It holds the FIFO at half full and adds about 2 ms of delay. The header comment says it's tested on Windows, Linux, and macOS.
- **The Windows feedback-format worry is mostly handled.** For UAC2, TinyUSB sends 16.16 feedback in 4 bytes, which is the format Windows requires.
- Keep "test on Windows" as a milestone, but it's lower risk than the handoff implied.

## 11. Debug output: use the UART, not USB serial

- The handoff's milestone 1 logs over "serial". On the QT Py, the only USB port is the audio port.
- **Recommendation:** log on UART TX (GP20) to a 3.3 V USB-serial adapter. That keeps the audio USB descriptor simple.
- USB CDC plus audio (composite) also works, but it adds another thing to debug on Windows.

## 12. Smaller gaps

| Item | Note | Risk |
|---|---|---|
| Firmware updates with the box closed | The BOOT button is inside the box. Add a TinyUSB reset interface so `picotool reboot -u` (or a 1200-baud touch) enters the bootloader. Consider a pinhole over the button as a backup. | Low |
| NeoPixel | Drive GP11 low to keep it off (a few mA and stray light), or use it as a status LED, **not** red/green-coded. | Low |
| USB suspend current | If one host sleeps while the other plays, the diode-OR can still draw ~100 mA from the sleeping host. That's technically over the 2.5 mA suspend limit. Hosts rarely enforce it. | Low |
| Ground tie | The box joins both computers' grounds. The box's audio is digital so it's fine here, but either computer's *own* analog outputs could pick up hum. | Low |
| Per-stage delay | Each slave stage adds 1 frame (≈21 µs). Negligible. | None |
| PCM5102A test board | Many modules need SCK tied to GND (a solder jumper) to run without MCLK. Check before milestone 2. | Low |
