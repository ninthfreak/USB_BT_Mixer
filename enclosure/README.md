# Enclosure

## Status

| Part | State |
|---|---|
| Two-port USB-C wall + cradle **test coupon** (`usb_wall_test.scad`) | One printed part. Models and checks pass. **Dimensions still carry guesses** — see "Measure these". |
| Full enclosure | Not started. Waits on the coupon results. |

**Layout decision:** both input ports side by side on one face; the ESP32's own USB-C stays inside (`docs/decisions.md`).

## Board dimensions in hand

| Board | Size | Source |
|---|---|---|
| Waveshare RP2350-USB-C (×2) | 33.00 × 17.50 mm, R2.00 corners. USB-C 8.90 mm wide, centred, **at both ends**. **Two retention notches** in the long edges at the port end: 1.50 deep × 2.00 long, 3.45 from the port edge | Size and corners: drawing (verified). Notches: measured off the drawing, ±0.15 mm — Waveshare does not dimension them |
| Waveshare ESP32-DEV-KIT-WROOM-32E-N4 | 53.80 × 27.94 mm. Four mounting holes at 50.04 × 25.40 mm centres. 19-pin headers, 2.54 mm pitch, 45.72 mm span, rows 24.94 mm apart. USB-C 8.95 mm wide on one short edge; **PCB antenna at the opposite end** | Waveshare dimensioned drawing (verified) |

Rough full-box estimate: the ESP32 sets the width, so about **62 × 72 × 20 mm** outside, boards flat, input ports on one short face. An estimate, not a model.

**Antenna rule:** the ESP32's antenna end must point at a wall with no wiring, no diodes and no USB cables crowding it, and no carbon-fibre-filled filament anywhere near.

## Test coupon

![Coupon with both boards dropped in](img/preview_iso.png)

The wall is solid, the boards drop straight down onto the nubs, and their flush outer shells sit against the wall's inner face.

**What it's for:** a small print (about 59 × 37 × 13 mm) to check the port design before the full box.

- Do the USB-C shells line up with the wall openings?
- Do real cables seat fully?
- **Do two cable overmolds fit side by side?** The main risk of the chosen layout, and the reason the coupon prints both ports.
- **Do the nubs hold the boards against plug-in and pull-out force?**

### Retention: nubs in the floor

Two nubs rise from the cradle floor into the board's edge notches, flush with the board's top face.

![Nub in the notch](img/preview_nub.png)

| Force | Taken by |
|---|---|
| Pull-out (cable yanked outward) | Nub faces against the notch walls, in the plane of the PCB |
| Push-in (plugging in) | Nub faces against the other notch walls |
| Side to side | Nub sides in the notches, plus the cradle rails |
| Up and down | **Nothing on the coupon.** The lid does it in the full box |

This replaces two earlier attempts, both now deleted: a drop-in clip at the inner end (commit `755abec`), and a "staple" of pegs dropped into the notches from above (commit `730c92e`). Both are recoverable from git if needed.

### The wall stays a solid piece

Fixed nubs mean the board must come **straight down** — it cannot slide forward, because the notch would have to travel over the nub through solid PCB.

That would normally force the port opening to be slotted open at the top so a protruding shell could drop in. It doesn't here: **on the real board the exposed port's shell is flush with the board edge** (owner, boards in hand). Only the inner programming port is proud. A flush shell never has to thread into the wall, so the opening stays a closed, shell-shaped hole in a solid wall, and the board still drops straight down.

The two overhangs are now separate parameters, `usb_over_out` (0.00, measured) and `usb_over_in` (1.00, still to measure). The drop test encodes the dependency: set `usb_over_out` back to a proud value and it fails, because the closed wall would then block the board.

### How deep the plug can go

With a flush receptacle, the wall sits in front of the connector mouth, so a plug stops that far short of bottoming out. `mouth_recess` is the dial:

| `mouth_recess` | Result |
|---|---|
| 1.00 (current) | 1 mm of wall in front, shell-shaped opening — **the same geometry as the coupon already printed** |
| smaller | Plug seats deeper, less wall left around the opening |
| 0 | Pocket goes clean through: full insertion, but the opening becomes overmold-sized rather than shell-shaped |

**Open question:** did a cable fully click home on the coupon you printed? That print had the same 1 mm of wall in front. If yes, leave `mouth_recess` alone. If a cable felt short or loose, drop it to 0.6 and reprint just the wall end.

## Measure these

The boards are in hand, so these can stop being guesses. Each is a parameter at the top of `usb_wall_test.scad`.

| Parameter | Current value | What to measure |
|---|---|---|
| `pcb_t` | 1.60 mm (assumed) | Board thickness, away from any parts |
| `usb_h` | 3.26 mm (typical top-mount shell) | USB-C shell height, board top to shell top |
| `usb_over_out` | **0.00 mm (measured: flush)** | Done |
| `usb_over_in` | 1.00 mm (assumed) | How far the inner programming port's shell overhangs |
| `under_clear` | 1.5 mm (assumed) | Tallest part on the board's underside, if any |
| `notch_dep` | 1.50 mm (pixel-measured) | Notch depth into the long edge |
| `notch_len` | 2.00 mm (pixel-measured) | Notch length along the board |
| `notch_d` | 3.45 mm (pixel-measured) | Notch's near edge, from the port edge |

The notch numbers matter most now that they carry all the load, and they are the least trustworthy: Waveshare does not dimension them, and they are probably depanelling tabs, so the edges may be rough.

After editing:

1. Run `tests/check_fit.sh`. Every line should say `ok`, `clear` or `contact only`, exit code 0.
2. Re-export:

   ```
   openscad -o stl/usb_wall_test_coupon.stl -D 'part="coupon"' usb_wall_test.scad
   ```

   The checks read board numbers from the model through `p_*()` accessors, so there is nothing to keep in sync by hand.

## Printing

| Setting | Suggestion |
|---|---|
| File | `stl/usb_wall_test_coupon.stl` — one part, nothing loose |
| Orientation | As exported, sitting on its base |
| Supports | None. The port openings are short bridges, about 9 mm |
| Material | PLA or PETG for the test. **Not** carbon-fibre-filled (that rule matters most near the antenna in the final box) |
| Layer height | 0.12–0.16 mm. The nubs are 1.2 × 1.7 mm in plan, so fine layers matter more than before |
| Walls | 3 or more perimeters |

## Test steps

1. Drop a board straight down into a cradle so the notches land over the nubs. It should not need sliding or forcing.
2. Repeat for the second board.
3. Plug in several different cables, including your thickest-housing one. For each:
   - Does it click fully in?
   - Does the board move fore and aft, or do the nubs hold it?
   - Does the plug housing hit the wall before the plug is fully in?
4. **Plug both ports at once with your two fattest cables.** Do the housings foul each other?
5. Wiggle a plugged-in cable up, down and sideways. Watch whether the board flexes or lifts.
6. Yank a cable out fast. Do the nubs hold, or do they shear?
7. Hold the board down with a finger while plugging, to simulate the lid. Does that change anything?

## Tuning parameters

| Symptom | Change |
|---|---|
| Nubs won't enter the notches, or the board rattles fore and aft | `notch_c` (default 0.15 per face), then the notch dimensions from your calipers |
| A nub shears off | Raise `notch_c` (a tight nub takes a side load it shouldn't), or thicken the board under it by lowering `under_clear` |
| Two cables foul each other at the wall | `pitch_extra` (default 3.0). Raising it widens the box |
| Board too tight or loose across the cradle | `fit` (default 0.20 per side) |
| Shell binds in the opening, or the gap looks sloppy | `hole_c` (default 0.25 per side) |
| Plug housing hits the wall before the plug is fully in | Raise `om_w` / `om_h` (13.0 × 7.2) |
| Plug does not click fully home | Lower `mouth_recess` (1.00 now; 0 removes all wall in front) |

## Files

| File | Contents |
|---|---|
| `usb_wall_test.scad` | Parametric model. Set `part` to `preview` or `coupon`. |
| `stl/` | Exported print file |
| `tests/check_fit.sh` | Collision checks, including a straight-down drop test. Needs `openscad` and Python `trimesh`. |
| `img/` | Preview renders |

### A note on the guards

`check_fit.sh` runs *guards* before the collision checks. A guard asserts that a
test solid is non-empty. Without them an empty solid makes every collision check
pass for the wrong reason — which has happened twice in this project, once from
a modelling bug and once from a probe that was too big.

The drop test is the one that earns its keep now: it sweeps the board and both
USB shells upward and checks nothing is in the way, which is what proves the
board can be lowered in without sliding. Breaks confirmed to fail the suite:

| Break | Catches |
|---|---|
| Make `usb_over_out` proud again (closed wall blocks the drop) | `check 24`, `check 25` |
| Set `notch_c` negative (nub too big) | `check 1`, `check 7`, `check 24`, `check 25` |
| Set `notch_dep` to 0 (notches gone) | `guard 17`, `guard 19` |
| Widen `om_w` past the port pitch | `guard 14` |

The wall-web probe has now been wrong three times — too big, then spanning the
whole wall, then left behind when the pocket moved. It derives its position
from `p_pocket()` rather than hand-computed numbers, which is why the last move
did not silently break it.
