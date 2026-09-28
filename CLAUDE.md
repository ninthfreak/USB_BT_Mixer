# USB_BT_Mixer

Two USB-C inputs (each one a UAC2 sound card) → mixed → one Bluetooth audio output.

**Read `docs/architecture.md` first** (current design), then `docs/decisions.md`. `docs/HANDOFF.md` is the original design record; much of it is superseded.
`docs/review-notes.md` lists corrections and risks found after the handoff. Where the two disagree, the review notes win.
`docs/decisions.md` records the owner's decisions and overrides both.

## Working preferences

- The owner assesses risk and tradeoffs. Give accurate, honest feasibility reads, including for hard or dead-end paths.
- Rate difficulty (x/10) and confidence (%) explicitly. Recommendations are recommendations, not decisions. Mark verified vs. assumed.
- Readability: short paragraphs, headings, tables, small verifiable steps (owner has ADHD and is dyslexic).
- Red/green color blind: never use red vs. green alone to carry meaning (UI, plots, LEDs, analyzer annotations). Use shape, text, position, or blue/orange.
- Enclosure is printed on an Elegoo Centauri Carbon. No carbon-fiber-filled filament near the antenna (it attenuates 2.4 GHz).

## Repo layout

| Folder | Contents |
|---|---|
| `docs/` | Handoff, review notes, test logs |
| `hardware/` | BOM (`BOM.csv`), wiring, power notes |
| `enclosure/` | Enclosure design sources and exported STLs |
| `firmware/` | RP2040: Pico SDK + TinyUSB, one image for both boards (USB audio in → I2S slave out, UART control relay). ESP32: ESP-IDF (I2S clock master ×2 inputs, mixer, A2DP source, control). |
