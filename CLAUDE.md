# USB_BT_Mixer

Two USB-C inputs (each one a UAC2 sound card) → mixed → one Bluetooth audio output.

**Read `docs/HANDOFF.md` first.** It is the full design record: architecture, BOM, wiring, firmware plan, milestones, open questions.
`docs/review-notes.md` lists corrections and risks found after the handoff. Where the two disagree, the review notes win.

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
| `firmware/` | Pico SDK + TinyUSB firmware (one image, `ROLE_MASTER_LAST` / `ROLE_SLAVE`) |
