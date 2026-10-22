// Shared board dimensions and helpers for the USB_BT_Mixer enclosure.
//
// Every file that needs a board number includes THIS file. Nothing else
// redefines one. Duplicated dimensions have twice caused a check to pass for
// the wrong reason in this project, so there is exactly one copy.
//
// Values marked MEASURE are still guesses. Check them with calipers and edit
// here; every model and every test picks the change up.

/* [Hidden] */
$fn = 48;
eps = 0.01;

// ── Waveshare RP2350-USB-C (×2, the USB audio inputs) ────────────────────
// Source: Waveshare's dimensioned drawing (github.com/waveshareteam/RP2350-USB-C).
board_w = 17.50;   // drawing
board_l = 33.00;   // drawing
board_r = 2.00;    // corner radius, drawing
pcb_t   = 1.60;    // MEASURE: PCB thickness

// USB-C receptacles, one at EACH end, both centred across the board.
usb_w    = 8.90;   // shell width: board_w - 2*4.30, from the drawing
usb_h    = 3.26;   // MEASURE: shell height
usb_cx   = board_w / 2;
// The two connectors differ on the real board (owner, boards in hand):
usb_over_out = 0.00;   // MEASURED: the EXPOSED port is flush with the board edge
usb_over_in  = 1.00;   // MEASURE: the inner programming port IS proud
usb_depth    = 7.35;   // how far a receptacle reaches back along the board

// Retention notches: two cutouts in the long edges, PORT END ONLY.
// Waveshare does not dimension these; measured off their drawing pixel by
// pixel, so ±0.15 mm. Probably depanelling tabs, so edges may be rough.
// The inner end has no notches — what looks like them is the castellated
// pad row, about 0.5 mm deep.
notch_d   = 3.45;  // MEASURE: notch's near edge, from the port edge
notch_len = 2.00;  // MEASURE: length along the board
notch_dep = 1.50;  // MEASURE: depth into each long edge

// Castellated pads run from 2.88 mm to 23.20 mm from the INNER edge
// (9 per side, 2.54 pitch, first centre at 2.88). That leaves the port-end
// 9.8 mm and the inner-end 2.88 mm of each long edge pad-free — which is
// where anything may press on the board without crushing a soldered wire.
pad_first  = 2.88;
pad_pitch  = 2.54;
pad_count  = 9;
pad_last   = pad_first + (pad_count - 1) * pad_pitch;   // 23.20
pad_inset  = 1.13;  // pad centre, in from the long edge (drawing)

// ── Waveshare ESP32-DEV-KIT-WROOM-32E-N4 (the mixer / Bluetooth source) ──
// Source: Waveshare's dimensioned drawing.
esp_w  = 53.80;    // long dimension: USB-C at one end, PCB antenna at the other
esp_d  = 27.94;    // short dimension
esp_t  = 1.60;     // MEASURE: PCB thickness
// Four mounting holes, 50.04 × 25.40 mm centres. That puts each centre
// (53.80-50.04)/2 = 1.88 mm from the short edges and (27.94-25.40)/2 = 1.27 mm
// from the long edges — which identifies the drawing's unlabelled 1.27.
esp_hole_dx  = 50.04;
esp_hole_dy  = 25.40;
esp_hole_dia = 2.60;   // MEASURE: not dimensioned by Waveshare. 2.6 assumes M2.5
esp_top_h    = 5.00;   // MEASURE: tallest part above the PCB (likely the BAT JST)
esp_bot_h    = 0.50;   // MEASURE: anything on the underside
esp_usb_w    = 8.95;   // drawing

// ── Enclosure fit (shared by the coupon and the box) ─────────────────────
fit         = 0.20;  // RP board to cradle clearance, per side
hole_c      = 0.25;  // USB shell to wall-opening clearance, per side
notch_c     = 0.15;  // nub clearance inside the notch, per face
nub_h       = pcb_t; // nub top, flush with the board's top face
under_clear = 1.5;   // MEASURE: gap under an RP board for underside parts
side_t      = 2.0;   // cradle side rail thickness
ledge_w     = 1.0;   // support ledge under each long edge
base_t      = 2.0;   // floor thickness
wall_t      = 2.4;   // outer wall thickness
// Port centre spacing = board_w + 2*fit + side_t + pitch_extra. At 3.0 that is
// about 22.9 mm, clearing two cable overmolds up to ~22 mm wide.
pitch_extra = 3.0;
// Cable overmold pocket in the outer face of the port wall.
om_w = 13.0;
om_h = 7.2;
om_r = 1.5;
// Wall left in front of the receptacle mouth: the dial between a tidy
// shell-shaped opening and full plug insertion. A plug stops this far short.
mouth_recess = 1.00;

// ── Helpers ──────────────────────────────────────────────────────────────

// Rounded rectangle in XZ, centred, extruded along +Y by d.
// Built from a hull of corner circles: stays valid when r = h/2 (a stadium),
// where offset() of a zero-height square would produce nothing.
module rrect(w, h, r, d) {
    rr = min(r, w / 2, h / 2);
    rotate([-90, 0, 0])
        linear_extrude(d)
            hull()
                for (sx = [-1, 1], sz = [-1, 1])
                    translate([sx * (w / 2 - rr), sz * (h / 2 - rr)]) circle(rr);
}

// An RP2350 board's outline, notches included, extruded h tall from z=0.
// x0 = its left edge; y = 0 at the INNER edge, board_l at the port edge.
module rp_outline(x0, h) {
    ny1 = board_l - notch_d;
    ny0 = ny1 - notch_len;
    difference() {
        translate([x0, 0, 0]) cube([board_w, board_l, h]);
        translate([x0 - eps, ny0, -eps])
            cube([notch_dep + eps, notch_len, h + 2 * eps]);
        translate([x0 + board_w - notch_dep, ny0, -eps])
            cube([notch_dep + eps, notch_len, h + 2 * eps]);
    }
}

// One RP2350 receptacle shell. end = "out" (port, flush) or "in" (proud).
module rp_shell(x0, end) {
    over = (end == "out") ? usb_over_out : usb_over_in;
    y    = (end == "out") ? board_l + over - usb_depth : -over;
    translate([x0 + usb_cx, y, pcb_t + usb_h / 2])
        rrect(usb_w, usb_h, usb_h / 2, usb_depth);
}
