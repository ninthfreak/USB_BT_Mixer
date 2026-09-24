# Viability review

Written 2026-09-24, revised the same day. This judges the **outcome**, not the handoff's design.

## Scope (set by owner)

| | Target |
|---|---|
| **Inputs** | Any USB-C host that plays audio to a class-compliant USB audio device (UAC). No specific host is targeted. |
| **Output** | Any Bluetooth audio sink. No specific headphones are targeted. |
| **Power** | USB power from whichever input cables are connected. |
| **Use** | Game audio mixed with background music or video. No calls. The eyes stay on the game, so video lip sync is a minor concern. **Game-audio latency is the priority.** |

**Evidence labels:**

- **Verified:** checked against source code or a schematic.
- **Sourced:** from manufacturer or third-party text.
- **Estimate:** my judgment.

---

## 1. Verdict

| Question | Answer | Confidence |
|---|---|---|
| Can the outcome be built? | **Yes.** | ~85% that at least one path below works |
| Is the input side (2× QT Py RP2040, shared I2S clock) sound? | Yes | ~70% |
| What limits latency? | Mostly the Bluetooth transport and codec that the box and the sink can agree on, plus the sink's own buffer. **The box's microcontroller path is ~2–3 ms.** | See section 2 |

---

## 2. Where latency comes from

End-to-end path:

**host audio stack → USB (UAC2) → box → Bluetooth transmitter → radio link → sink decoder and buffer**

| Stage | Delay | Can the box change it? | Evidence |
|---|---|---|---|
| Host audio stack and USB buffering | Unknown; varies by host OS | No | — |
| TinyUSB FIFO in each board | ~2 ms average (held at half full) | Already near minimal | Verified: TinyUSB source comment |
| I2S hop, board B → board A | 1 frame ≈ 21 µs | No need | Calculated |
| Transmitter: input buffer, encoder, link settings | Depends on the transmitter | **Yes, by choosing the output stage** | — |
| Codec / transport negotiated with the sink | Largest single variable | **Partly.** The box can only offer codecs; the sink must support the same one. | — |
| Sink's own jitter buffer | Often the largest part | **No.** It's set by the sink's firmware. | Estimate |

**Consequences:**

- **The box's firmware and processors aren't a latency lever.** The only lever the box controls is the **output stage**: which transports and codecs it offers, and whether it prefers the lowest-latency one.
- **Ceiling:** a sink that supports only SBC over A2DP sets its own latency. No transmitter design fixes that.
- **Lip sync:** hosts won't shift video to compensate, because they see a USB sound card, not Bluetooth. Minor for this use case.

### 2a. Low-latency Bluetooth options a transmitter can offer

| Transport / codec | Sinks that support it | Latency notes | Evidence |
|---|---|---|---|
| A2DP SBC | All A2DP sinks (mandatory) | The baseline. The sink buffer dominates. | Sourced (A2DP spec: SBC is mandatory) |
| A2DP AAC | Many | Often no better than SBC, possibly worse | Estimate, medium confidence |
| A2DP aptX Low Latency | A smaller, older set of sinks | Designed for low latency | Sourced (Qualcomm marketing); no measurement |
| A2DP aptX Adaptive (low-latency mode) | Snapdragon Sound sinks | Creative claims ~50 ms for its BT-W5 dongle in this mode | Sourced (Creative) |
| LE Audio LC3 | Newer BT 5.2+ sinks | Designed for lower latency. Interoperability between vendors is still immature. | Sourced (Nordic docs, forum reports) |

**Best generic strategy:** offer as many of these as possible, and prefer the lowest-latency one each sink supports, with SBC as the fallback.

---

## 3. Architecture options

### 3a. Input stage: two USB device ports

| Option | Difficulty | Confidence | Notes |
|---|---|---|---|
| **2× RP2040 (QT Py), shared I2S clock** | 5–6/10 | ~70% | One board generates the only audio clock, so no sample-rate conversion is needed. The riskiest code is the second board's PIO I2S slave. |
| One chip with two USB device controllers | 7–8/10 | ~40% | **TinyUSB's device stack supports one port only** (verified: a single global `_usbd_rhport` in `usbd.c`). |
| RP2040 native USB + PIO-USB as the second device | 8/10 | ~25% | PIO-USB device mode is experimental; isochronous support is unknown. |

| **2× hardware USB-audio bridge chips (e.g., TI PCM2706: UAC1, I2S out), analog mix** | 3/10 | ~70% | **No firmware.** Each chip locks its sample clock to its own host, so the two outputs are in **different clock domains**. Mixing them in analog (each chip's DAC → resistor mix) sidesteps that. Output then needs an analog-input transmitter, or an ADC → I2S → TSA5001. Adds an analog stage, so hum/noise can enter from the hosts' tied grounds and USB power. UAC1 works on more hosts than UAC2. |
| 2× hardware bridge chips, digital mix | 6/10 | ~50% | Same clock-domain split, so it needs hardware ASRC chips plus a mixer MCU. More parts than the RP2040 route for no gain. |
| 2× XMOS (XU316) running XMOS's reference USB-audio firmware; one acts as I2S slave, the other uses the firmware's built-in mixer | 6–7/10 | ~45% | Mature, widely deployed USB-audio firmware. Heavy toolchain. **Power draw is likely much higher than RP2040** (estimate, unverified), which risks the one-host-powers-everything budget. |
| One STM32 with two USB device controllers (OTG_FS + OTG_HS in FS mode), ST's USB device library | 7/10 | ~45% | One chip, one clock domain, easy mixing. TinyUSB can't do two device ports (verified); ST's library can run two device instances, but I believe ST ships only a UAC1 class with no feedback (estimate), so UAC2 async would have to be written. Few boards expose both ports. |

**Recommendation:** 2× QT Py (chosen). The firmware-free analog route is the credible alternative: it trades the firmware risk (PIO I2S slave, feedback loop) for analog noise risk and fewer output-stage options.

### 3b. Output stage (the latency lever)

| Option | What it offers | Difficulty | Confidence | Main risks |
|---|---|---|---|---|
| **A. TinySine TSA5001** (I2S in) | SBC, AAC, aptX, aptX HD, **aptX LL**. That list is the vendor's, relayed through the handoff; I haven't checked it myself. | 4/10 | ~60% | The codec is picked automatically with unknown priority; it might pick aptX HD over LL. Closed firmware. Minimum voltage and I2S format unknown. 48 kHz only (sourced). |
| **B. USB Bluetooth transmitter dongle** with aptX Adaptive low-latency mode (e.g., Creative BT-W5), fed by a **third RP2040 acting as USB audio host** | SBC, AAC, aptX Adaptive with a user-selectable low-latency priority (sourced, Creative). LE Audio support: not verified. | 7/10 | ~40% | **TinyUSB has a USB audio host driver** (verified) that supports playback and explicit feedback, and its example lists RP2040 as a build target (verified). I haven't verified that it runs reliably on RP2040. **Clock-domain problem:** if the dongle paces its own rate, board A's I2S clock must be trimmed to follow it, using board C's buffer level as a software PLL. That's extra work. |
| **C. LE Audio source**: nRF5340 running Nordic's unicast client app, I2S in | LE Audio LC3 only | 8/10 | ~30% | Only LE Audio sinks. Interop reports are mixed: works with Sony Inzone Buds; no audio with WF-1000XM6 or EarFun Air Pro 4. Adding a Classic transmitter as fallback raises this to 9/10. |
| **D. ESP32 + ESP32-A2DP** | SBC only, open and tunable | 6/10 | ~60% | Doesn't raise the ceiling. Only useful if buffer tuning helps, which is unmeasured. |
| **E. I2S DAC → analog Bluetooth transmitter** | Whatever that transmitter offers | 3/10 | ~75% | An extra digital→analog→digital conversion. Mostly a fallback for reliability, not latency. |

**Recommendation (not a decision):**

1. **Build with option A first.** It's cheap and already offers aptX LL. On the first test with a sink that supports several codecs, find out which codec the TSA5001 actually picks.
2. **If lower latency is needed on more sinks, option B is the next step.** aptX Adaptive's low-latency mode is the most widely deployed low-latency Classic option I can source. It costs a third board and the clock-trim work.
3. **Option C only if LE Audio sinks become the priority.** It has the highest potential and the highest interop risk.

The board A I2S output stays the same for A, C, D and E. Option B adds board C, which receives board A's I2S.

### 3c. Paths that don't build this box

| Option | Difficulty | Confidence | Meets outcome? |
|---|---|---|---|
| 2 USB-C DAC dongles → resistor mix → Bluetooth transmitter | 2/10 | ~80% | Partly. The transmitter needs its own power. Ground-loop hum risk. |
| Stream one host's audio to the other over a network; that host pairs to the sink directly | 1–2/10 | Depends on host | Partly. Needs software on both hosts. |

---

## 4. Risk list for the recommended path (ranked)

| # | Risk | Impact | How to retire it |
|---|---|---|---|
| 1 | Bluetooth latency too high for gaming with a given sink | Depends on the sink; see section 2 ceiling | Measure the built box (handoff milestone 7 method). Direct pairing to a host is only a rough proxy. |
| 2 | TSA5001: voltage, I2S format, codec priority | Output-stage swap | One QT Py sending a test tone → TSA5001, before any USB work |
| 3 | PIO I2S slave on board B | Mixing | Logic analyzer; existing community code |
| 4 | USB feedback (clock matching) misbehaves on a host | Clicks or dropouts | Buffer-level logging over UART (development only) |
| 5 | USB-C wall mount stresses the solder joints | Board failure over time | Print the wall and cradle first |

---

## 5. Recommended order (risk first)

1. **Output stage, one board.** A QT Py as I2S master sends a generated sine wave → TSA5001 → a sink. No USB yet. Record the voltage, the I2S format, and the codec picked for each sink you try.
2. **USB input, one board.** The QT Py enumerates as a UAC2 speaker and plays through the TSA5001.
3. **Second board.** PIO I2S slave, mixing on board A.
4. **Shared power and hot-plug.**
5. **Latency measurement** per sink and codec.
6. **Enclosure.** Wall-and-cradle test print first; this can run in parallel from step 1.
7. **Only if needed:** output-stage upgrade (3b, option B or C).

---

## Sources

- TinyUSB source (cloned 2026-09-24): https://github.com/hathach/tinyusb (`src/class/audio/audio_host.*`, `examples/host/audio_host`)
- TSA5001 48 kHz-only note: https://github.com/pschatzmann/arduino-audio-tools/discussions/1433
- TSA5001 product page: https://www.tinysineaudio.com/products/tsa5001-bluetooth-5-3-audio-transmitter-board-i2s-digital-input
- Creative BT-W5 (aptX Adaptive low-latency mode, ~50 ms claim): https://us.creative.com/p/accessories/creative-bt-w5
- nRF5340 Audio unicast client (I2S/USB input): https://nrfconnectdocs.nordicsemi.com/ncs/2.6.1/nrf/applications/nrf5340_audio/unicast_client/README.html
- LE Audio interop reports: https://devzone.nordicsemi.com/f/nordic-q-a/124106/nrf5340-nora-b126-as-hci-controller-for-le-audio-on-raspberry-pi-cm4-pairs-ok-no-audio-with-sony-wf-1000xm6 and https://github.com/zephyrproject-rtos/zephyr/discussions/96481
- TI PCM2706 (UAC1, I2S mode via FSEL): https://www.ti.com/product/PCM2706
- Board schematics: see `hardware/board-comparison.md`
