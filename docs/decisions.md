# Decision log

Decisions made by the owner. Newest first. Reasoning and alternatives live in the linked docs.

| Date | Decision | Why | Details |
|---|---|---|---|
| 2026-09-28 | **The ESP32 does the mixing and is the audio clock master.** Both RP2040s become identical I2S slaves (receive the ESP32's clocks, send their USB audio). | Every adjustable mix setting then lives on the chip that receives the management commands. | `hardware/wiring.md`. Two direct inputs (the ESP32's two I2S peripherals); more inputs chain into an RP2040's DIN. |
| 2026-09-28 | **No buttons on the case.** Bluetooth pairing (scan, connect, forget) is done only through the USB control channel from any connected device's browser. | The owner always has some device with a browser to plug in. A firmware bug in the control path is fixed by reflashing (RP2040s over USB; ESP32 via its internal USB-C or later OTA). | Conditions: the controlling device must plug into one of the box's USB-C ports (until/unless Wi-Fi control is added), and its browser must support the chosen channel (USB MIDI: Chrome, Edge, Firefox; WebUSB: Chrome, Edge). |
| 2026-09-28 | **Box is managed through a USB control channel** on the RP2040 input boards, relayed to the ESP32 over UART. No custom native app; a web page. | Driver-free, works from any connected host, doesn't use the Bluetooth radio. | Channel not yet chosen. Recommendation: USB MIDI + Web MIDI page. Wi-Fi web page on the ESP32 remains a possible later addition (station mode is rated stable alongside Classic Bluetooth by Espressif). |
| 2026-09-28 | **Bluetooth output: original ESP32** (candidate board: Adafruit ESP32 Feather V2) running an A2DP source, instead of the TSA5001. | Owner prefers it for the learning value and the control it gives (pairing, headphone volume, status, codec parameters). | SBC only. The owner accepts the added firmware work (pairing, reconnection, AVRCP volume). The TSA5001 stays as a fallback. See `viability-review.md` §3b. |
| 2026-09-24 | **Inputs: 2× RP2040.** XMOS and analog-mix alternatives rejected. | XMOS is too expensive; an analog mix adds a digital→analog→digital conversion. | `viability-review.md` §3a |
| 2026-09-24 | **Board: Adafruit QT Py RP2040** | Onboard VBUS diode and CC resistors (verified from schematic); small; USB-C at the board edge. | `hardware/board-comparison.md` |
| 2026-09-24 | **USB-C ports exposed directly through the enclosure wall.** No extension cables. | Fewer connectors; extensions only make things worse. | `enclosure/` |

## Open questions that follow from these decisions

| Question | Options | Notes |
|---|---|---|
| ~~Where does mixing happen?~~ | Resolved: ESP32 hub | See the 2026-09-28 entry |
| Which USB control channel? | USB MIDI (recommended), WebUSB, HID, USB serial | See the chat analysis; USB MIDI covers the most hosts. |
| ~~Feather V2 power path~~ | Resolved: rail → `BAT` pin, no diode | review-notes #14 (schematic-verified) |
| ESP32-A2DP library features | AVRCP absolute volume, reconnect to last device | Believed supported (~60–80%); not verified |
