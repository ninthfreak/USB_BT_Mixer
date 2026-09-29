# USB_BT_Mixer

A small box with two USB-C inputs and one Bluetooth audio output. Any USB-C host that supports USB audio sees each input as a normal USB sound card. The box mixes both inputs and streams the mix to any Bluetooth audio sink.

- **Architecture (start here): [`docs/architecture.md`](docs/architecture.md)**
- Decision log: [`docs/decisions.md`](docs/decisions.md)
- Design record: [`docs/HANDOFF.md`](docs/HANDOFF.md)
- Corrections since the handoff: [`docs/review-notes.md`](docs/review-notes.md)
- Design envelope (limits and extension points): [`docs/design-envelope.md`](docs/design-envelope.md)
- Viability review: [`docs/viability-review.md`](docs/viability-review.md)
- Parts list: [`hardware/BOM.csv`](hardware/BOM.csv)

Status: planning. Inputs: Waveshare RP2350-USB-C ×2, USB-C exposed directly through the enclosure (each needs an external Schottky to the shared rail). Bluetooth output: original ESP32 on a Waveshare ESP32-DEV-KIT-WROOM-32E-N4, powered from the rail via its `VSYS` pin. The ESP32 mixes and owns the audio clock. Configured from any browser via a page the box serves over USB; no case buttons. See [`docs/decisions.md`](docs/decisions.md). Firmware not started; the enclosure test coupon needs re-measuring for the new input board.
