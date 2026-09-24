# Project Handoff: 2-Input USB-C → Bluetooth Audio Mixer

This file summarizes a planning conversation, so work can continue in Claude Code.
Tip: drop it into the repo root. Rename it to `CLAUDE.md` if you want Claude Code to load it automatically.

---

## 1. Working preferences (please follow)

- **Owner assesses risk and tradeoffs.** Give accurate information and honest feasibility reads, including for hard or dead-end paths. Don't steer toward easier alternatives or soften difficulty.
- **Rate difficulty (x/10) and confidence (%) explicitly.** State recommendations as recommendations, never as decisions. Keep uncertainty visible, and mark what's verified vs. assumed.
- **Readability:** the owner has ADHD and is dyslexic. Use short paragraphs, clear headings, tables, and small verifiable steps.
- **Red/green color blind:** never use red vs. green alone to convey meaning. That applies to UI, plots, logic-analyzer annotations, and LED status schemes; use shape, text, position, or blue/orange instead.
- **Fabrication:** the enclosure will be 3D printed (Elegoo Centauri Carbon). Avoid carbon-fiber-filled filament near the antenna, because it attenuates 2.4 GHz.

---

## 2. Goal

A small box with **two USB-C inputs** and **one Bluetooth audio output**:

- Each USB-C port connects to a computer, or a phone that supports USB audio. That device sees the box as a normal USB sound card (UAC2, class compliant, no drivers).
- The box **mixes both inputs** and streams the mix to Bluetooth headphones.
- The box is **powered by whichever USB-C cable(s) are connected**.

No commercial single-box product doing this was found, so it's a custom build.

### How we got here (rejected or deferred options)

| Option | Status | Why |
|---|---|---|
| Multiple Bluetooth *inputs* mixed on a Pi Zero 2 W / Linux (PipeWire) | Dropped | The requirements changed. The radio needs multiple roles at once (scatternet), which is flaky; latency is two Bluetooth hops. |
| Raspberry Pi (any model) as the dual USB device | Rejected | Every Pi has at most one USB device-capable port. |
| Off-the-shelf chain: 2 USB-C DAC dongles → resistor mix → commercial BT transmitter | Viable but not chosen | Difficulty 2/10, ~85% confidence. Risk of ground-loop hum. The owner wants a custom single box. |
| 2× RP2040 + ESP32 (A2DP source, SBC only) | **Fallback** | ESP32 = original ESP32 only (WROOM-32 / PICO-MINI-02); S2/S3/C-series lack Classic BT. |
| STM32 with two USB device controllers | Deferred | Elegant clocking, but dual-port UAC2 under TinyUSB is little-tested. |
| nRF5340 LE Audio (LC3) output stage | Future experiment | Only relevant for LE Audio headphones such as the Sony XM5. Difficulty 8–9/10, ~30% confidence (interoperability risk). |
| **2× Pico + TinySine TSA5001 (I2S → Bluetooth)** | **Current plan** | See below. |

---

## 3. Current architecture

```
Computer A ──USB-C──► Pico A (UAC2 device + I2S MASTER + mixer + limiter) ──I2S──► TSA5001 ──BT──► headphones
                         ▲
                         │ I2S data (clocked by Pico A)
Computer B ──USB-C──► Pico B (UAC2 device + I2S SLAVE)
```

- **Pico A generates the only audio clock** (bit clock and word select) at **48 kHz**. It drives Pico B and the TSA5001.
- **Pico B** receives the clock and sends its audio to Pico A. Its "upstream" data input is tied to GND (the start of the chain).
- **Pico A** computes `out = limiter(own_sample + picoB_sample)` and sends the result to the TSA5001.
- **Both computers sync to Pico A's clock** through UAC2 asynchronous feedback (see 5.1). The result is no sample-rate conversion and no drift handling in the Picos.
- **The TSA5001** (Qualcomm-based) is an I2S slave. It picks the Bluetooth codec automatically and handles its own Bluetooth timing.
- **Design for swappability:** keep a firmware setting for the I2S role, so the output stage can be swapped for an ESP32 or nRF5340 without rewiring upstream.

### Chain design notes
- Carry **32-bit I2S slots** between the Picos (16-bit USB samples sign-extended), so sums never clip mid-chain.
- Only the **last stage (Pico A)** scales and limits down to the TSA5001's output format.
- One firmware image with a config flag: `ROLE_MASTER_LAST` (Pico A) or `ROLE_SLAVE` (Pico B). This scales to more inputs by chaining more slave Picos.

---

## 4. Hardware

### Bill of materials

| Part | Qty | Notes | Approx. cost |
|---|---|---|---|
| Raspberry Pi **Pico or Pico 2 (NOT the W versions)** | 2 | On W boards, USB power sense isn't on GPIO24 (it goes through the wireless chip). | ~$4–5 each |
| TinySine **TSA5001**, BT 5.3 I2S transmitter | 1 (buy 2) | I2S slave, 48 kHz, 16/24/32-bit, aptX / aptX LL / aptX HD / SBC / AAC, A2DP only. $14.95 from tinysineaudio.com. The sibling TSA5002 is the same on paper but out of stock. | $14.95 |
| 2.4 GHz antenna, U.FL (IPEX / MHF1) | 1 | Flat adhesive to start; U.FL-to-SMA bulkhead if you see dropouts. **Confirm the connector type** from the board. | ~$3–8 |
| Panel-mount USB-C (female) → micro-USB (male) extension, **data-capable** | 2 | The Picos are micro-USB. | ~$3–6 each |
| Momentary normally-open pushbutton (panel-mount, 6–12 mm) | 1 | The TSA5001's pairing control is a **header**, not a button. Hold 3 s = search; 5 s = clear pairing. Consider recessing it. | ~$1–3 |
| Capacitor, 22–47 µF, ≥10 V | 1 | Across the rail near the TSA5001. Stay ≤ ~47 µF because of USB's limit on capacitance at plug-in. | <$1 |
| 33 Ω resistors | 4 | In series on the bit clock and word select lines leaving Pico A (to Pico B and to the TSA5001). | <$1 |
| 26–28 AWG hookup wire, M2 screws/standoffs | — | | ~$8 |
| 3D-printed enclosure | 1 | Access to the pairing switch, a window or light pipe for the TSA5001 LED, antenna at the edge facing the user. | — |

**Tools:** soldering iron, multimeter, micro-USB data cable, **a cheap 8-channel 24 MHz logic analyzer with PulseView (close to essential)**.
**Optional:** a PCM5102A I2S DAC board, to *hear* Pico A's I2S output before the TSA5001 arrives or to rule out Bluetooth problems.

Estimated total: ~$40–55 plus shipping.

### Power design (confidence ~85%)
- Each Pico has an onboard Schottky diode from **VBUS to VSYS**. **Tie Pico A VSYS to Pico B VSYS.** The two diodes then combine both USB supplies, and the computers are never connected to each other.
- **NEVER connect the two VBUS pins together.**
- The TSA5001 power input goes to the shared VSYS rail. The rail is **~4.6–4.8 V**, not 5 V. **Open question:** does the TSA5001 run reliably at that voltage? About 75% likely. Test it, or ask TinySine for the minimum input voltage.
- Both Picos are always powered together. That prevents an unpowered RP2040 from being powered through its I/O pins by Pico A's clock signals.
- Each Pico reads **its own** VBUS on **GPIO24** (USB side, before the diode) to know whether its computer is connected.
- Budget: Picos ~20–30 mA each, TSA5001 ~30–60 mA while streaming (estimate; the listed "6 mA" is surely idle). Total ~70–120 mA. Declare ~200 mA `bMaxPower` in **both** Picos' descriptors.
- Connecting the two computers' grounds through the box is acceptable because the audio path is all digital.

### Wiring

Pin numbers are **suggestions**; adjust for PIO pin-group constraints.

| Signal | From | To | Suggested GPIO |
|---|---|---|---|
| Bit clock (BCLK), 3.072 MHz | Pico A (via 33 Ω) | Pico B, and the TSA5001 via its own 33 Ω | A: GP10 → B: GP10 |
| Word select (LRCK), 48 kHz | Pico A (via 33 Ω) | Pico B, and the TSA5001 via its own 33 Ω | A: GP11 → B: GP11 |
| Data | Pico B DOUT | Pico A DIN | B: GP12 → A: GP13 |
| Data | Pico A DOUT | TSA5001 SD | A: GP12 |
| Chain start | Pico B DIN | GND | B: GP13 |
| Rail | Pico A VSYS | Pico B VSYS, TSA5001 +, capacitor | — |
| Ground | all | all | — |
| Pairing | pushbutton | across the TSA5001 pairing header | — |

The TSA5001 I2S header has SD, LRCK, BCLK, MCLK (unused), and GND. Keep the I2S wires under ~10 cm.

Optional: let Pico A trigger pairing through an NPN transistor or N-MOSFET across the pairing header. Only drive the header directly from a GPIO if you've measured it at ≤3.3 V.

---

## 5. Firmware (Pico SDK + TinyUSB, C)

### 5.1 USB side (both Picos)
- TinyUSB **UAC2 speaker**: 48 kHz, 16-bit, stereo, **asynchronous mode with a feedback endpoint**.
- **Base the feedback on how full the audio buffer is.** Each Pico's buffer drains at Pico A's I2S clock rate, not the Pico's own USB timing. TinyUSB has a feedback method based on buffer count and a `uac2_speaker_fb` example. **Verify the current API names; they've changed across versions.**
- Give each Pico distinct USB product strings and serial numbers (e.g., "BT Mixer Input A" / "BT Mixer Input B").
- Volume: likely omit the volume control from the descriptor, so the OS applies software volume and each computer's slider sets its level in the mix. Medium confidence; verify on macOS and Windows.
- Test on macOS/Linux first. Windows' built-in UAC2 driver (Win10 1703+) is stricter about descriptors and the feedback format.

### 5.2 I2S (PIO)
- Standard I2S (Philips) framing, 2 × 32-bit slots per frame, BCLK = 64 × 48 kHz = 3.072 MHz.
- **Pico A:** PIO I2S **master** transmitter (to the TSA5001) plus a receiver for Pico B's data, using its own clock. This is the well-trodden case.
- **Pico B:** PIO I2S **slave** that follows the external BCLK/LRCK: transmit, plus receive upstream data for chain scalability. **This is the riskiest custom code.** Expect ~20–30 PIO instructions and time with a logic analyzer.
- **Clock accuracy:** choose a system clock that divides evenly into the I2S clock. For example, 153.6 MHz (12 MHz × 128 → VCO 1536 MHz, divided by 5 and 2) = 50 × 3.072 MHz. That avoids fractional-divider jitter. USB keeps its separate 48 MHz PLL.
- **Open question:** the exact I2S format the TSA5001 expects (Philips vs. left-justified, slot width, bit alignment). Confirm with the logic analyzer and trial.

### 5.3 Per-sample logic
- `sum = upstream_in (int32) + own_usb_sample (sign-extended to 32-bit)`
- Slave role: send `sum` downstream in a 32-bit slot.
- Master/last role: apply a soft limiter, then output 16- or 24-bit (left-aligned in a 32-bit slot, per the TSA5001's format).
- USB buffer empty → contribute zeros. No computer connected (GPIO24 low) → contribute zeros but **still pass upstream audio through**.

---

## 6. Build milestones (each works on its own before the next)

| # | Step | Difficulty |
|---|---|---|
| 1 | Pico A enumerates as a UAC2 speaker on Mac/PC; log the buffer fill level over serial. | 3/10 |
| 2 | Pico A as I2S master → PCM5102A DAC (optional): hear the audio, confirm the buffer level stays steady (feedback working). | 4/10 |
| 3 | Power the TSA5001 from the VSYS rail (check the voltage first); feed it Pico A's I2S; pair headphones; confirm the format and streaming. | 4/10 |
| 4 | Pico B slave transmit, verified on the logic analyzer; mix at Pico A. **Riskiest step.** | 6/10 |
| 5 | Shared power: hot-plug each cable while audio plays, and check the silence behavior. | 3/10 |
| 6 | Enclosure, antenna, pairing switch, panel USB-C jacks. | — |
| 7 | Latency measurement for each headphone model (method below). | 2/10 |

**Overall: difficulty ~5/10, confidence ~65–70%.**

**Latency measurement:** play a sharp click from the computer through the box. Record with a phone microphone near the earbud, with a wired speaker on the computer playing the same click. The gap between the two clicks is the added latency.

---

## 7. Headphones and latency

The TSA5001 picks the codec automatically. Qualcomm transmitters usually choose the "best" codec both ends support, which likely means **AAC where available. AAC usually has *more* latency than SBC** (medium confidence). The codec can't be forced or tuned (closed firmware).

| Headphones | Codecs | Notes | Expected total latency |
|---|---|---|---|
| Shokz OpenMove | SBC only | No known low-latency mode. | ~150–250 ms |
| Nothing Ear (open) | SBC, AAC | **Low Lag Mode** (Nothing X app, claimed <120 ms with a phone). Other Nothing/CMF models reportedly **reset it on reconnect**; ~40–50% it persists. Workaround: keep the phone connected via multipoint and toggle it per session. The box can't send the command (closed TSA5001 firmware). | ~110–170 ms with Low Lag, ~150–250 ms without (low-to-medium confidence) |
| Sony WF-1000XM5 | SBC, AAC, LDAC, LC3 (LE Audio) | Sony's "Low latency" mode *is* LE Audio. The TSA5001 is A2DP only, so no benefit; AAC via the TSA5001. LE Audio would need a future nRF5340 stage. | ~150–250+ ms |

Latency sources: USB ~5–10 ms, Pico buffers ~2–5 ms, the remainder is the Bluetooth link and the headphones' buffer (the dominant, uncontrollable part). A faster processor would **not** help meaningfully; only codec and buffering choices matter.

---

## 8. Open questions and risks

| Item | Status | Confidence |
|---|---|---|
| Pico B's PIO I2S slave program | Custom code; the main risk | — |
| TSA5001 works at ~4.6–4.8 V | Test, or ask TinySine | ~75% |
| TSA5001's I2S format / slot width | Confirm by trial | — |
| TSA5001 antenna connector = U.FL | Check the board | High, not verified |
| TSA5001 LED on a header? | Check on arrival | Unknown |
| TinyUSB feedback API names and behavior | Verify against the current release | Medium-high |
| Windows UAC2 feedback quirks | Test | Medium |
| TSA5001 codec choice (AAC vs. SBC) and latency | Measure | Medium |
| Nothing Low Lag persistence with the box | Test at milestone 3 | ~40–50% |

## 9. Fallback: ESP32 output stage
If the TSA5001 disappoints, use an **original ESP32** (e.g., Adafruit ESP32 Feather V2 / ESP32-PICO-MINI-02, or DevKitC with WROOM-32E) running Phil Schatzmann's **ESP32-A2DP** `BluetoothA2DPSource` (SBC only).

- Either the ESP32 becomes the I2S master (the original plan: I2S0 master receive using the audio PLL, a ring buffer, and a slip handler), or it runs as a slave to Pico A.
- Power it from the rail through a low-dropout 3.3 V regulator (e.g., AP2112K) into its 3V3 pin.
- Upside: sender queue tuning is possible, and the Nothing Low Lag command could in theory be sent over RFCOMM (reverse-engineered protocol, ~40% confidence, GPL-3.0 reference project `nothingx-pc`).
