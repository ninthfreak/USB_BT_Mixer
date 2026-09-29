# Decision log

Decisions made by the owner. Newest first. Reasoning and alternatives live in the linked docs.

| Date | Decision | Why | Details |
|---|---|---|---|
| 2026-09-29 | **Input boards: 2× Waveshare RP2350-USB-C**, each with an owner-supplied Schottky from its `VSYS` pin to the shared rail. Replaces the Adafruit QT Py RP2040. | 520 KB RAM vs 264 KB, which directly attacks the highest firmware risk (USB audio + lwIP + web server on one chip). The missing VBUS diode is no obstacle: the owner has diodes and is comfortable fitting them. | `hardware/wiring.md`, review-notes #20. Costs: 2 MB flash instead of 8 MB; a second USB-C port faces into the case (accepted, left unused); enclosure needs re-measuring. |
| 2026-09-29 | **ESP32 board: Waveshare ESP32-DEV-KIT-WROOM-32E-N4**, powered from the rail into its `VSYS` pin. Replaces the Adafruit ESP32 Feather V2. | The Feather has no supported way to take a non-battery supply: Adafruit warns that external supplies on `BAT` destroy the LiPoly charger (#19). This board's `VSYS` is a proper system-power input, its converter accepts 2.3–5.5 V, and onboard D3 protects its USB-C so the ESP32 can be flashed with the box powered. | `hardware/wiring.md`, review-notes #20. Same ESP32 chip, so A2DP/SBC and the 44.1 kHz constraint are unchanged. Pin map redone around GPIO27 (RGB LED) and GPIO34 (battery ADC). |
| 2026-09-28 | **Control channel: USB network adapter + web page served by the QT Py itself** (CDC-NCM/ECM, lwIP, HTTP/WebSocket). Commands relay to the ESP32 over UART; the ESP32 holds all state. | Fully self-contained: no internet, no other server, any browser (Safari included), no permission prompts. Hosting the page elsewhere was rejected as not simple. | `docs/architecture.md` §3. Fallback if the sound card + network device misbehaves on a host: USB MIDI or USB serial, with the same UART protocol. |
| 2026-09-28 | **The ESP32 does the mixing and is the audio clock master.** Both RP2040s become identical I2S slaves (receive the ESP32's clocks, send their USB audio). | Every adjustable mix setting then lives on the chip that receives the management commands. | `hardware/wiring.md`. Two direct inputs (the ESP32's two I2S peripherals); more inputs chain into an RP2040's DIN. |
| 2026-09-28 | **No buttons on the case.** Bluetooth pairing (scan, connect, forget) is done only through the USB control channel from any connected device's browser. | The owner always has some device with a browser to plug in. A firmware bug in the control path is fixed by reflashing (RP2040s over USB; ESP32 via its internal USB-C or later OTA). | Condition: the controlling device must plug into one of the box's USB-C ports (until/unless Wi-Fi control is added). With the self-served page, any browser works (see the control-channel entry). |
| 2026-09-28 | **Box is managed through a USB control channel** on the RP2040 input boards, relayed to the ESP32 over UART. No custom native app; a web page. | Driver-free, works from any connected host, doesn't use the Bluetooth radio. | Channel chosen: see the control-channel entry above. Wi-Fi web page on the ESP32 remains a possible later addition (station mode is rated stable alongside Classic Bluetooth by Espressif). |
| 2026-09-28 | **Bluetooth output: original ESP32** (candidate board: Adafruit ESP32 Feather V2) running an A2DP source, instead of the TSA5001. | Owner prefers it for the learning value and the control it gives (pairing, headphone volume, status, codec parameters). | SBC only. The owner accepts the added firmware work (pairing, reconnection, AVRCP volume). The TSA5001 stays as a fallback. See `viability-review.md` §3b. |
| 2026-09-24 | **Inputs: 2× RP2040.** XMOS and analog-mix alternatives rejected. | XMOS is too expensive; an analog mix adds a digital→analog→digital conversion. | `viability-review.md` §3a |
| ~~2026-09-24~~ | ~~**Board: Adafruit QT Py RP2040**~~ | Superseded 2026-09-29 by the RP2350-USB-C (see the top entry). | `hardware/board-comparison.md` |
| 2026-09-24 | **USB-C ports exposed directly through the enclosure wall.** No extension cables. | Fewer connectors; extensions only make things worse. | `enclosure/` |

## Open questions that follow from these decisions

| Question | Options | Notes |
|---|---|---|
| ~~Where does mixing happen?~~ | Resolved: ESP32 hub | See the 2026-09-28 entry |
| ~~Which USB control channel?~~ | Resolved: USB network + self-served page | See the control-channel entry |
| ~~Feather V2 power path~~ | Moot: the Feather is no longer the board | Superseded 2026-09-29. The analysis stays in review-notes #14, #17, #19 |
| ~~Feather charger chip (U3)~~ | Moot: board changed rather than modified | The owner chose a board designed for rail power instead of any of options A–D |
| ~~ESP32-A2DP library features~~ | Resolved: reconnect yes; volume yes with `A2DPNoVolumeControl` + passthrough handler | review-notes #16 (verified from source) |
| ~~Sample rate~~ | Not a choice: **44.1 kHz end to end is a constraint** | Stock ESP-IDF's A2DP source offers 44.1 kHz only (verified), and the design has one clock and no resampling. review-notes #16 |
