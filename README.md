# USB_BT_Mixer

A small box with two USB-C inputs and one Bluetooth audio output. Any USB-C host that supports USB audio sees each input as a normal USB sound card. The box mixes both inputs and streams the mix to any Bluetooth audio sink.

- Design record: [`docs/HANDOFF.md`](docs/HANDOFF.md)
- Corrections since the handoff: [`docs/review-notes.md`](docs/review-notes.md)
- Viability review: [`docs/viability-review.md`](docs/viability-review.md)
- Parts list: [`hardware/BOM.csv`](hardware/BOM.csv)

Status: planning. Board: Adafruit QT Py RP2040 ×2, USB-C exposed directly through the enclosure. Wiring: `hardware/wiring.md`. Firmware and enclosure not started.
