# Viability review

Written 2026-09-24. This judges the **outcome**, not the handoff's design.

**Outcome:** two computers or phones plug into one small box over USB-C. Each sees a normal USB sound card. The box mixes both and sends the mix to Bluetooth headphones. The box runs on USB power from whichever cables are plugged in.

**Evidence labels:**

- **Verified:** checked against source code or a schematic.
- **Sourced:** from third-party text.
- **Estimate:** my judgment.

---

## 1. Verdict

| Question | Answer | Confidence |
|---|---|---|
| Can the outcome be built? | **Yes.** No part of it needs anything exotic. | ~85% that at least one path below works |
| Is the current plan (2× QT Py + TSA5001) sound? | Mostly. The main risk is the TSA5001, not the firmware. | ~60–65% as specced |
| Is there an outcome-level risk no design can fix? | **Yes: Bluetooth latency with no video sync correction.** See section 2. | ~90% it behaves as described |

---

## 2. Two limits that apply to every design

### 2a. Latency, and why video will look out of sync

- Standard Bluetooth headphone audio (A2DP) adds about **150–250 ms** with your headphones (estimate). No processor, board, or firmware choice changes that much.
- **The part that matters more:** when headphones pair directly with a computer or phone, the OS *knows* about the Bluetooth delay and shifts video to match.
- **Through this box, the computer only sees a USB sound card** with a few ms of delay. It won't compensate.
  - **Effect:** in video, speech lags lips by ~150–250 ms. That's clearly noticeable; people tend to notice lag past ~100 ms.
  - **Confidence:** ~90% that this is how it behaves.
- **Mitigations:**
  - **Per-app audio delay:** VLC and mpv can shift the video to match. Browsers, Zoom, and most phone apps can't.
  - **Latency value in the USB descriptor:** the USB audio standard has a field for this, and TinyUSB exposes it. Whether macOS, Windows, iOS, or Android use it to shift video is unknown to me. I'd guess ~20–30% that at least one does.
- **Only matters if you watch video or do calls through the box.** For music or games-without-lipsync, it's just delay.
- **Owner's use case (2026-09-24):** gaming + music, or gaming + video playing in the background. Never calls. Eyes stay on the game, so **video lip sync is a minor issue**.
  - The latency that matters is **game audio**. Games never compensate for Bluetooth delay, whether the headphones are paired directly or go through the box.
  - **The box's own microcontroller path adds ~2–3 ms:** the TinyUSB FIFO at half-fill averages ~2 ms (verified: TinyUSB source comment), and each I2S hop is 1 frame, ≈21 µs (calculated).
  - **Everything else differs from direct pairing in an unknown direction:**
    - host USB-audio buffering replaces the host's own Bluetooth-stack buffering
    - the TSA5001's input buffering, codec choice, encoder, and link settings replace the host's
    - These parts dominate, and they can't be estimated precisely without measuring. An earlier "~5–15 ms" figure here had no basis and has been removed.
  - So lowering Bluetooth latency (codec control, Nothing Low Lag, maybe LE Audio later) is the thing worth optimizing.

### 2b. Headphone codecs make the TSA5001's aptX support irrelevant

- The TSA5001's headline features are aptX, aptX Low Latency, and aptX HD.
- **None of your three headphones support aptX:**
  - Shokz OpenMove: SBC only
  - Nothing Ear (open): SBC and AAC
  - Sony WF-1000XM5: SBC, AAC, LDAC, and LC3 (LE Audio)
- So any Bluetooth transmitter that does good SBC and AAC gives the same result. That opens up the output-stage options in section 3.

### 2c. Other outcome-level facts

- **Headphone "multipoint" doesn't mix.** It connects to two sources but plays only one at a time. That's why this box needs to exist (sourced; common knowledge).
- **Phones as hosts:** iOS and Android both support class-compliant USB audio. Phone-supplied power (~100 mA+) should cover the box, though it's near the edge on some phones (estimate).

### 2d. Hosts (owner, 2026-09-24): MacBook + a handheld running Android or Linux

No phones, no Windows, no consoles.

| Host | UAC2 async support | Notes | Confidence |
|---|---|---|---|
| MacBook | Yes, class-compliant | Needs the Feature Unit (volume/mute), or the slider greys out (review-notes #9). | ~90% |
| Linux handheld | Yes (`snd-usb-audio`) | The best-trodden path. PipeWire/Pulse volume works either way. | ~90% |
| Android handheld | Yes on modern Android (8+) | Android routes all audio to a USB audio device automatically. Vendor kernels occasionally ship quirks. | ~80% |

- **Windows drops out of the test plan.** The feedback-format quirk (review-notes #10) no longer matters.
- **Console UAC1 support isn't needed.**
- **Handheld battery:** when the handheld is the only host, it powers the whole box (~70–120 mA estimate). That's a small drain.

---

## 3. Architecture options for the outcome

### 3a. Input stage: two USB device ports

Each computer needs its own USB *device* controller, and nearly every microcontroller has only one.

| Option | Difficulty | Confidence | Notes |
|---|---|---|---|
| **2× RP2040 (QT Py), shared I2S clock** | 5–6/10 | ~70% | The current plan. Its best idea is that one board generates the only audio clock, so no sample-rate conversion is needed. The riskiest code is the second board's PIO I2S slave. |
| One chip with two USB controllers (STM32 with 2 OTG ports) | 7–8/10 | ~40% | **TinyUSB's device stack supports one port only** (verified: a single global `_usbd_rhport` in `usbd.c`). You'd need a different USB stack or heavy changes. |
| RP2040 native USB + PIO-USB as the second device | 8/10 | ~25% | PIO-USB device mode is experimental, and I don't know that it supports isochronous (audio) transfers. |

**Recommendation:** keep 2× QT Py.

### 3b. Output stage: I2S → Bluetooth

| Option | Difficulty | Confidence | Pros | Cons |
|---|---|---|---|---|
| **TinySine TSA5001** (current) | 4/10 | ~60% | Small. Handles Bluetooth by itself. AAC capable. | Single small vendor, closed firmware. 48 kHz only (sourced). **Minimum supply voltage, I2S format, and codec choice all unknown.** Its aptX advantage doesn't apply (2b). |
| **PCM5102A DAC → off-the-shelf analog Bluetooth transmitter**, both inside the box | 3/10 | ~75% | Mature consumer parts. Lots of transmitter choices. Easy to swap. | One digital→analog→digital hop (audibly fine at this level). Transmitters with batteries may pull charging current at plug-in. Choose one powered by 5 V without a battery. Must fit the enclosure. |
| **ESP32 (original) + ESP32-A2DP library** | 6/10 | ~60% | Open firmware, tunable. | SBC only. Some headphones have pairing quirks with it (sourced, anecdotal). More code to own. |

**Recommendation:** buy the TSA5001 *and* a PCM5102A board. Both are cheap. Try the TSA5001 first; the DAC + transmitter route is the lower-risk fallback. Both use the same I2S output from board A, so the rest of the design doesn't change.

### 3c. Paths that don't build this box

Listed because you asked about the outcome, not the design.

| Option | Difficulty | Confidence | Meets outcome? |
|---|---|---|---|
| Off-the-shelf chain: 2 USB-C DAC dongles → resistor mix → battery Bluetooth transmitter | 2/10 | ~80% | Partly. The transmitter needs its own battery or power. Risk of ground-loop hum between the two computers. Not a single tidy box. |
| Software: stream computer B's audio over the network to computer A (e.g., SonoBus); A pairs to the headphones directly | 1–2/10 | ~80% on computers, low on phones | Partly. No hardware, and **A keeps OS video sync** (2a). B adds ~20–50 ms network delay. Needs software on both. Phones are limited. |
| Commercial dual-USB mixer (e.g., RØDECaster models with two USB-C audio ports) + Bluetooth transmitter on the headphone out | 1/10 | ~60% that a model fits | Partly. Expensive, needs wall power, and big. I'm ~80% sure of the dual-USB feature and haven't checked it here. |

---

## 4. Risk list for the recommended path (ranked)

| # | Risk | Impact if it goes wrong | How to retire it | Cost of test |
|---|---|---|---|---|
| 1 | Game-audio latency (2a) too high to enjoy (video sync is minor for this use case) | The whole project, any design | Rough check by direct pairing (section 5); real number only by measuring the built box | Free |
| 2 | TSA5001 doesn't work on the ~4.7 V rail, has an odd I2S format, or picks a bad codec | Output stage swap | Bring it up with **one** QT Py sending a test tone, before any USB work | Parts on hand |
| 3 | PIO I2S slave on board B | Mixing | Logic analyzer; there's existing community code | Time |
| 4 | USB feedback (clock matching) misbehaves on one OS | Clicks or dropouts on that OS | Buffer-level logging (section 5) | Time |
| 5 | USB-C wall mount stresses the QT Py's solder joints | Board failure over time | Print the wall and cradle first | One print |

---

## 5. Recommended order (risk first)

This replaces the handoff's milestone order.

1. **Rough latency check (no build, no purchase).** Pair the headphones directly to the handheld and play a game.
   - **What this tells you:** whether Bluetooth game-audio delay of roughly this size is tolerable for you. If you already game this way, the check is done.
   - **What it does not tell you:** the box's actual latency. The box uses a different signal path (USB audio → two RP2040s → I2S → TSA5001) and a different Bluetooth chip, firmware, and possibly codec. Its latency could be higher or lower. Only a measurement at the end (handoff milestone 7 method) gives the real number.
   - **Rejected alternative:** a USB-C DAC dongle + off-the-shelf transmitter. That's also only a proxy (no mixing path, different Bluetooth chip), so it adds cost without adding accuracy for this question.
2. **Output stage, one board.** A QT Py as I2S master playing a generated sine wave → TSA5001 → headphones. No USB yet. Settles the voltage, format, and codec questions.
3. **USB input, one board.** The QT Py enumerates as a UAC2 speaker and plays through the TSA5001.
   - Buffer-level logging over UART is how you confirm feedback works. It's optional, development-only (see chat).
4. **Second board.** PIO I2S slave, mixing on board A.
5. **Shared power and hot-plug.**
6. **Enclosure.** Wall-and-cradle test print first; this can run in parallel from step 2 onward.

---

## Sources

- TinyUSB source (cloned 2026-09-24): https://github.com/hathach/tinyusb
- TSA5001 48 kHz-only note: https://github.com/pschatzmann/arduino-audio-tools/discussions/1433
- TSA5001 product page: https://www.tinysineaudio.com/products/tsa5001-bluetooth-5-3-audio-transmitter-board-i2s-digital-input
- Board schematics: see `hardware/board-comparison.md`
