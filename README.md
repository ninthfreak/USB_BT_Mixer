# USB_BT_Mixer

A small box with two USB-C inputs and one Bluetooth audio output. Any USB-C host that supports USB audio sees each input as a normal USB sound card. The box mixes both inputs and streams the mix to any Bluetooth audio sink.

- **Architecture (start here): [`docs/architecture.md`](docs/architecture.md)**
- Decision log: [`docs/decisions.md`](docs/decisions.md)
- Design record: [`docs/HANDOFF.md`](docs/HANDOFF.md)
- Corrections since the handoff: [`docs/review-notes.md`](docs/review-notes.md)
- Design envelope (limits and extension points): [`docs/design-envelope.md`](docs/design-envelope.md)
- Viability review: [`docs/viability-review.md`](docs/viability-review.md)
- Parts list: [`hardware/BOM.csv`](hardware/BOM.csv)
- **Latest review (2026-11-16): [`docs/project-review-2026-11.md`](docs/project-review-2026-11.md)**

**Status (2026-11-16): designed, nothing built.**

| Part | State |
|---|---|
| Hardware | Two Waveshare RP2350-USB-C input boards and a Waveshare ESP32-DEV-KIT-WROOM-32E-N4 solder flat onto a carrier PCB ([`hardware/carrier/`](hardware/carrier/)). Routed and DRC clean; **not ordered**. Print [`carrier-fit-check.pdf`](hardware/carrier/carrier-fit-check.pdf) and lay the real boards on it first |
| Firmware | Not started. Design: [`docs/architecture.md`](docs/architecture.md) |
| Enclosure | The modelled box is for the earlier hand-wired build and is out of date. The carrier needs a new one |

Each input board's native USB port faces its host through the enclosure wall and reaches the shared rail through its own Schottky. The ESP32 mixes, owns the audio clock and is the Bluetooth A2DP source. Configured from any browser via a page the box serves over USB; no case buttons. See [`docs/decisions.md`](docs/decisions.md).
