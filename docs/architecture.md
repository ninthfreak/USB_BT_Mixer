# System architecture

How the box works end to end. This is the single reference for firmware work. Decisions behind it are in `docs/decisions.md`; pins are in `hardware/wiring.md`.

**Status:** agreed design (2026-09-28). Nothing is built or tested yet.

```
                ┌──────────────── QT Py RP2040 (×2, identical) ───────────────┐
 Host ──USB──▶  │ sound card (UAC2) ──▶ audio buffer ──▶ PIO I2S out ─────────┼──DOUT──▶ ┐
                │                                         ▲ clocked by ESP32   │         │
                │ config page (USB network, HTTP) ◀─▶ relay ◀─▶ UART ────────┼──TX/RX─▶ │
                └──────────────────────────────────────────────────────────────┘         │
                                                      BCLK/LRCK ◀──────────────────────┤
                                                                                        ▼
                ┌──────────────────────────── ESP32 Feather V2 ────────────────────────────┐
                │ I2S0 / I2S1 in ──▶ per-input gain ──▶ sum ──▶ limiter ──▶ SBC ──▶ Bluetooth│
                │ UART1 / UART2 ◀─▶ command handler ◀─▶ settings (saved in flash)           │
                │ generates BCLK/LRCK (the only audio clock)                                 │
                └────────────────────────────────────────────────────────────────────────────┘
```

## 1. Roles

| Board | Job | Holds state? |
|---|---|---|
| **QT Py RP2040** (×2, one firmware image) | USB sound card for its host; sends that audio to the ESP32 over I2S, following the ESP32's clock; serves the configuration page over a USB network link; relays commands and replies between page and ESP32 | **No.** Stateless relay and web server. |
| **ESP32 Feather V2** | The only audio clock; receives both inputs; per-input gain, mix, limiter; Bluetooth A2DP source (SBC); pairing and reconnection; command handler | **Yes: the single source of truth** for all settings and pairings, saved in flash |

## 2. Audio path

1. **Host → QT Py:** USB audio (UAC2, asynchronous with a feedback endpoint), **44.1 kHz** stereo (pending owner OK; ESP-IDF's A2DP source is 44.1 kHz only, review-notes #16). The audio arrives in 1 ms packets.
2. **QT Py buffer:** a TinyUSB FIFO held at about half full, roughly 2 ms (verified: TinyUSB `AUDIO_FEEDBACK_METHOD_FIFO_COUNT`).
3. **QT Py → ESP32:** a PIO program shifts samples out on DOUT **on the ESP32's BCLK/LRCK edges**. The QT Py never generates audio timing.
4. **ESP32 input:** I2S0 (master) receives QT Py 1; I2S1 (slave, on looped-back clocks) receives QT Py 2. Both boards follow the same LRCK edges, so their samples arrive aligned.
5. **ESP32 processing:** host volume × box trim per input → sum in 32-bit → limiter → SBC encoder → Bluetooth.

**Clock synchronisation (no resampling anywhere):**

- The ESP32's clock drains each QT Py's FIFO at the ESP32's rate.
- TinyUSB's feedback endpoint reports the FIFO level to the host, which then adjusts its sending rate. Each host ends up locked to the ESP32's clock.
- The Bluetooth stack runs on the same ESP32 crystal.

**No host connected:** the QT Py is still clocked and sends zeros. That input simply contributes silence.

**Latency owned by the box:** QT Py FIFO ~2 ms + the ESP32's I2S DMA buffers (keep them small; to be measured) + SBC framing. The Bluetooth link and the headphones' buffer add the rest.

## 3. Control path

**Transport to the host: USB network adapter + a web page served by the box.**

- Each QT Py adds a USB network interface (CDC-NCM; CDC-ECM as fallback) beside its sound card, running lwIP with DHCP, DNS and an HTTP/WebSocket server. This is based on TinyUSB's `net_lwip_webserver` example.
- The host gets an address from the box. The box hands out **no default gateway**, so the host's internet traffic doesn't route through it.
- You open the page by address or name. Addresses differ per board, e.g. `192.168.7.1` for input 1 and `192.168.8.1` for input 2, plus a DNS name.
- The page is stored in the QT Py's flash and ships with the firmware, so page and firmware versions always match.
- Any browser works, Safari included. No internet, no other server, no permission prompts.

**Flow of one change:**

1. The page sends a command over the WebSocket, e.g. `set gain input=2 db=-6`.
2. The QT Py wraps it in a UART message and sends it to the ESP32.
3. The ESP32 validates and applies it, saves it if it's persistent, then **sends the new state out on both UARTs**.
4. Each QT Py forwards the state to any page it has open. Two pages (one per host) stay in sync.

**Events the QT Py sends unprompted:**

| Event | Purpose |
|---|---|
| Host volume / mute changed (the sound card's volume control) | The ESP32 applies it, so **all gain lives in one place** |
| Host mounted / unmounted / suspended | Status display; silence handling |
| FIFO underrun / overrun counts | Diagnostics |

**UART link (per QT Py):**

- About 1 Mbaud, 8N1.
- Framed messages: start byte, length, type, sequence number, payload, CRC.
- Commands that change state get an acknowledgement; the sender retries on timeout.
- QT Py pins: TX GP20, RX GP5 (RP2040 UART1). ESP32: UART1 (GPIO8/7) for QT Py 1, UART2 (GPIO32/14) for QT Py 2.

**Commands the ESP32 should support** (first pass, not final):

| Area | Commands |
|---|---|
| Mix | Per-input trim, per-input mute, master level, limiter on/off/threshold, ducking (optional) |
| Bluetooth | Scan, list results, connect, disconnect, forget, list paired devices, status (connected device, codec settings) |
| System | Get full state, firmware versions (ESP32 and both QT Pys), protocol version, reboot, reboot a QT Py into its bootloader |

## 4. Firmware updates

| Board | Method |
|---|---|
| QT Py | The page (or `picotool`) sends "reboot to bootloader". The QT Py then appears as a USB drive; copy the new firmware file (UF2) onto it. |
| ESP32 | Its own USB-C (CP2102N, auto-reset) by opening the case; OTA over Wi-Fi possible later |

## 5. Risks, highest first

| Risk | Difficulty | Mitigation |
|---|---|---|
| QT Py PIO I2S slave timing | 5/10 | Logic analyzer; test with one board first |
| ESP32 I2S1 following I2S0's looped-back clocks | 5/10 | Test early, before the Bluetooth work |
| Sound card + network adapter as one USB device, across macOS, Linux and Android | 5/10 | Test on each host type early. Fallback: USB MIDI or USB serial for control; the UART protocol is unchanged. |
| RP2040 RAM/CPU for USB audio + lwIP + web server together | 4/10 | Measure; keep the page small and serve it from flash |
| ESP32-A2DP volume handling | Low: supported (verified) | Use `A2DPNoVolumeControl` to avoid applying volume twice; handle passthrough VOL keys (review-notes #16) |

## 6. Suggested bring-up order

Each step is testable on its own:

1. ESP32 as I2S master → one QT Py sending a test tone → the ESP32 logs samples (proves the I2S slave path).
2. Add the second QT Py on I2S1 (proves the dual-input clocking).
3. ESP32 mix → Bluetooth A2DP to headphones with the test tones.
4. QT Py USB sound card → real host audio into the chain (proves feedback / clock lock).
5. UART protocol with a minimal command (e.g. set trim) sent from a serial terminal.
6. USB network + web page on the QT Py.
7. Shared power, hot-plug, enclosure.
