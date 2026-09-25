# Design envelope

The design's limits and extension points in one place. Written 2026-09-25.

**Baseline design:** 2× QT Py RP2040 (board A is the clock master and mixer, board B follows A's clock) → I2S → TSA5001 → Bluetooth. System clock 76.8 MHz, one audio clock domain at 48 kHz.

**Evidence labels:** *verified* = checked against source, schematic or datasheet; *sourced* = third-party text; *estimate* = my judgment.

---

## 1. Hard limits of the baseline

| Limit | Value | Set by | Evidence |
|---|---|---|---|
| Sample rate | **48 kHz only** | TSA5001 | Sourced |
| USB speed | Full speed (12 Mbit/s) | RP2040 | Verified |
| USB audio bandwidth per input | Stereo 48 kHz at 16 or 24 bits fits easily (≤ 288 bytes per 1 ms frame; full-speed allows up to 1023) | USB 2.0 full-speed isochronous transfers | Calculated |
| Hosts that play 44.1 kHz | The host OS converts the rate itself; the box only offers 48 kHz | Host OS | Estimate: macOS, Linux and Android do this automatically |
| Bluetooth output | **One A2DP link, SBC/AAC/aptX family**, no LE Audio or broadcast (Auracast) | TSA5001 | Sourced (vendor list, not verified) |
| Bluetooth sinks at once | Presumably 1 | TSA5001 | Estimate |
| Latency, box's own path | ~2–3 ms | TinyUSB FIFO (~2 ms) + I2S hops (≈21 µs each) | Verified / calculated |
| Latency, end to end | Dominated by the Bluetooth link and the sink's buffer; unknown until measured | Sink + transmitter | — |
| Supply rail | ~4.6–4.8 V (USB power minus one Schottky diode) | Board power paths | Verified topology, estimated voltage |
| Power available | Whatever one host's port supplies, since one host may power everything | USB spec: 500 mA for USB 2.0, 900 mA for USB 3.x, 1.5–3 A for USB-C current modes | Sourced (USB spec) |
| Audio back to hosts (microphone) | None | A2DP carries audio one way only; no capture stream is defined | Verified (design) |
| Controls | Each host's own volume slider only | Design | — |

---

## 2. The rule behind most boundaries: one clock domain

Everything mixed digitally must run on **board A's clock**.

| Source type | Fits? | Why |
|---|---|---|
| USB input through another RP2040 | **Yes** | The host follows A's clock through USB feedback. |
| ADC (analog input) | **Yes** | The ADC follows A's clocks. It needs a master clock, which requires the 61.44 MHz clock change. |
| Anything with **its own clock**: S/PDIF/optical input, a Bluetooth *receiver*, network audio, a second I2S master | **No, not without an ASRC** | Two independent clocks drift apart, so one stream has to be resampled (asynchronous sample-rate conversion). That means a hardware ASRC chip or software resampling; difficulty 6–7/10. |

---

## 3. Extension points

| Extension | What it takes | Clock change? | Difficulty | Confidence | Main risk |
|---|---|---|---|---|---|
| **More USB inputs** | Another RP2040 per input, chained before board B. Each adds 1 frame (≈21 µs). | No | 3/10 per board | ~80% | Board A's clock line fans out further; power budget |
| **Analog line input** | 3.5 mm jack → PCM1808 ADC (following A's clocks) → board B's chain input; 12.288 MHz master clock from board A; fix sample scaling; gain in firmware | **Yes: 76.8 → 61.44 MHz** | ~4/10 | ~70% | Ground-loop hum; ADC input range on a ~4.7 V supply (unverified) |
| **Analog line output** | PCM5102A DAC wired in parallel with the TSA5001; 3.5 mm jack | No | ~2/10 | ~85% | Hum into mains-powered gear; wired output is ~150–250 ms ahead of Bluetooth |
| Headphone output | Analog line output + headphone amplifier | No | ~3/10 | ~80% | Same as above |
| Different Bluetooth output stage | Anything that accepts board A's I2S: ESP32 (SBC only), TS3086-based module (if the firmware suits), nRF5340 (LE Audio) | No | 4–8/10 | 30–60% | Firmware and interop; see `viability-review.md` §3b |
| USB Bluetooth dongle (aptX Adaptive) | Third RP2040 as USB audio **host**; board A's clock trimmed to follow the dongle | No, but A's clock becomes adjustable | 7/10 | ~40% | RP2040 host playback unproven; clock-following loop |
| Physical volume knob | Potentiometer → a spare analog pin, or a digital encoder | No | 2/10 | ~85% | **Pin conflict:** A0–A3 (the analog pins) are used for I2S in the current pin map |
| Status LED | Onboard NeoPixel, **not** red/green-coded | No | 1/10 | ~95% | — |

---

## 4. Not reachable without a redesign

| Goal | Why not |
|---|---|
| Sample rates other than 48 kHz end to end | TSA5001 is 48 kHz only |
| Latency below what the sink's buffer allows | The sink's firmware sets it; only a lower-latency codec or transport negotiated with that sink helps |
| Microphone / calls through the headphones | A2DP carries audio one way only |
| Several Bluetooth sinks at once | Not with the TSA5001 |
| Mixing unsynchronised digital sources | Needs an ASRC (§2) |
| Running with no host connected | No battery; the box gets its power from the hosts |

---

## 5. Resource budget, board A (current pin map)

| Resource | Used | Free | Notes |
|---|---|---|---|
| Header GPIOs (11, plus 2 on the STEMMA QT connector) | BCLK, LRCK, DOUT, DIN, UART TX | ~6–8 | GP24/25 are the clock-output-capable pins needed for an ADC master clock |
| PIO state machines (8) | ~2–3 (I2S out, I2S in) | ~5 | A separate DAC data line would use one more |
| CPU | TinyUSB + mixing + limiter | Large margin (estimate) | ~1,600 cycles per 48 kHz frame at 76.8 MHz, ~1,280 at 61.44 MHz |
