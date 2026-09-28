# Decision log

Decisions made by the owner. Newest first. Reasoning and alternatives live in the linked docs.

| Date | Decision | Why | Details |
|---|---|---|---|
| 2026-09-28 | **Control channel: USB network adapter + web page served by the QT Py itself** (CDC-NCM/ECM, lwIP, HTTP/WebSocket). Commands relay to the ESP32 over UART; the ESP32 holds all state. | Fully self-contained: no internet, no other server, any browser (Safari included), no permission prompts. Hosting the page elsewhere was rejected as not simple. | `docs/architecture.md` §3. Fallback if the sound card + network device misbehaves on a host: USB MIDI or USB serial, with the same UART protocol. |
| 2026-09-28 | **The ESP32 does the mixing and is the audio clock master.** Both RP2040s become identical I2S slaves (receive the ESP32's clocks, send their USB audio). | Every adjustable mix setting then lives on the chip that receives the management commands. | `hardware/wiring.md`. Two direct inputs (the ESP32's two I2S peripherals); more inputs chain into an RP2040's DIN. |
| 2026-09-28 | **No buttons on the case.** Bluetooth pairing (scan, connect, forget) is done only through the USB control channel from any connected device's browser. | The owner always has some device with a browser to plug in. A firmware bug in the control path is fixed by reflashing (RP2040s over USB; ESP32 via its internal USB-C or later OTA). | Condition: the controlling device must plug into one of the box's USB-C ports (until/unless Wi-Fi control is added). With the self-served page, any browser works (see the control-channel entry). |
| 2026-09-28 | **Box is managed through a USB control channel** on the RP2040 input boards, relayed to the ESP32 over UART. No custom native app; a web page. | Driver-free, works from any connected host, doesn't use the Bluetooth radio. | Channel chosen: see the control-channel entry above. Wi-Fi web page on the ESP32 remains a possible later addition (station mode is rated stable alongside Classic Bluetooth by Espressif). |
| 2026-09-28 | **Bluetooth output: original ESP32** (candidate board: Adafruit ESP32 Feather V2) running an A2DP source, instead of the TSA5001. | Owner prefers it for the learning value and the control it gives (pairing, headphone volume, status, codec parameters). | SBC only. The owner accepts the added firmware work (pairing, reconnection, AVRCP volume). The TSA5001 stays as a fallback. See `viability-review.md` §3b. |
| 2026-09-24 | **Inputs: 2× RP2040.** XMOS and analog-mix alternatives rejected. | XMOS is too expensive; an analog mix adds a digital→analog→digital conversion. | `viability-review.md` §3a |
| 2026-09-24 | **Board: Adafruit QT Py RP2040** | Onboard VBUS diode and CC resistors (verified from schematic); small; USB-C at the board edge. | `hardware/board-comparison.md` |
| 2026-09-24 | **USB-C ports exposed directly through the enclosure wall.** No extension cables. | Fewer connectors; extensions only make things worse. | `enclosure/` |

## Open questions that follow from these decisions

| Question | Options | Notes |
|---|---|---|
| ~~Where does mixing happen?~~ | Resolved: ESP32 hub | See the 2026-09-28 entry |
| ~~Which USB control channel?~~ | Resolved: USB network + self-served page | See the control-channel entry |
| ~~Feather V2 power path~~ | Resolved: rail → `BAT` pin, no diode | review-notes #14 (schematic-verified) |
| Feather charger chip (U3) | A: remove U3 (recommended); B: diode; C: 3.3 V into `3V`; D: leave | Adafruit warns against non-battery sources on `BAT` because they destroy the charger. review-notes #17, #19. **Owner to decide.** |
| ~~ESP32-A2DP library features~~ | Resolved: reconnect yes; volume yes with `A2DPNoVolumeControl` + passthrough handler | review-notes #16 (verified from source) |
| ~~Sample rate~~ | Not a choice: **44.1 kHz end to end is a constraint** | Stock ESP-IDF's A2DP source offers 44.1 kHz only (verified), and the design has one clock and no resampling. review-notes #16 |
