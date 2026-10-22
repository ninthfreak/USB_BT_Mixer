// Interference checks for box.scad. Run via tests/check_box.sh.
// Board numbers come from boards.scad; box geometry from box.scad's modules.
include <../boards.scad>
use <../box.scad>
which = 0;
SWEEP = 25;

// Mirror of box.scad's derived layout. Kept to the few values the checks need.
pitch  = board_w + 2 * fit + side_t + pitch_extra;
esp_w_ = esp_w; esp_d_ = esp_d;

// Rebuild the same placement box.scad uses.
rp_x_lo = -fit - side_t;
rp_x_hi = pitch + board_w + fit + side_t;
rp_cx   = (rp_x_lo + rp_x_hi) / 2;
side_clear = 3.0; service_gap = 6.0; back_gap = 8.0;
esp_standoff = 3.0; head_clear = 1.2;
esp_x0 = rp_cx - esp_w / 2;
esp_y1 = -service_gap;
esp_y0 = esp_y1 - esp_d;
z_floor = -under_clear;

module rp_board(x0)   { rp_outline(x0, pcb_t); }
module rp_assembly(x0){ rp_board(x0); rp_shell(x0, "out"); rp_shell(x0, "in"); }

// Volume the board sweeps while being lowered straight down.
module drop_sweep(x0) {
    rp_outline(x0, pcb_t + SWEEP);
    hull() { rp_shell(x0, "out"); translate([0,0,SWEEP]) rp_shell(x0, "out"); }
    hull() { rp_shell(x0, "in");  translate([0,0,SWEEP]) rp_shell(x0, "in"); }
}

// ESP32: its PCB, and the envelope of everything standing on it.
module esp_pcb()   { translate([esp_x0, esp_y0, z_floor + esp_standoff])
                         cube([esp_w, esp_d, esp_t]); }
module esp_parts() { translate([esp_x0, esp_y0, z_floor + esp_standoff + esp_t])
                         cube([esp_w, esp_d, esp_top_h]); }

// Where castellated pads — and therefore soldered wires — live on a board.
// A pad centre sits pad_first..pad_last from the inner edge; pads are about
// 1.6 mm long, so the occupied band starts 0.8 mm before the first centre.
// Nothing on the lid may touch this.
module pad_zone(x0) {
    for (xs = [x0, x0 + board_w - 2.0])
        translate([xs, pad_first - 0.8, pcb_t])
            cube([2.0, (pad_last + 0.8) - (pad_first - 0.8), 3.0]);
}

// guards: must be NON-EMPTY
if (which == 1)  base();
if (which == 2)  lid();
// a nub must actually occupy each notch, not just the ledges under the board
module notch_vol(x0, side) {
    xs = (side == 0) ? x0 : x0 + board_w - notch_dep;
    translate([xs, board_l - notch_d - notch_len, 0])
        cube([notch_dep, notch_len, pcb_t]);
}
if (which == 3)  intersection() { base(); notch_vol(0, 0); }
if (which == 8)  intersection() { base(); notch_vol(0, 1); }
if (which == 9)  intersection() { base(); notch_vol(pitch, 0); }
// a slab sitting on board A's top face: the press posts must reach it
if (which == 4)  intersection() { lid(); translate([0, 0, pcb_t])
                     cube([board_w, board_l, 0.2]); }
if (which == 7)  intersection() { lid(); translate([pitch, 0, pcb_t])
                     cube([board_w, board_l, 0.2]); }
if (which == 5)  esp_parts();
if (which == 6)  pad_zone(0);

// collisions: must be EMPTY or zero-volume contact
if (which == 10) intersection() { base(); rp_board(0); }
if (which == 11) intersection() { base(); rp_board(pitch); }
if (which == 12) intersection() { base(); rp_shell(0, "out"); }
if (which == 13) intersection() { base(); rp_shell(0, "in"); }
if (which == 14) intersection() { base(); rp_shell(pitch, "out"); }
if (which == 15) intersection() { base(); esp_pcb(); }
if (which == 16) intersection() { base(); esp_parts(); }
if (which == 17) intersection() { base(); drop_sweep(0); }
if (which == 18) intersection() { base(); drop_sweep(pitch); }
if (which == 19) intersection() { lid(); rp_board(0); }
if (which == 20) intersection() { lid(); rp_board(pitch); }
if (which == 21) intersection() { lid(); rp_shell(0, "out"); }
if (which == 22) intersection() { lid(); rp_shell(0, "in"); }
if (which == 23) intersection() { lid(); rp_shell(pitch, "out"); }
if (which == 24) intersection() { lid(); rp_shell(pitch, "in"); }
if (which == 25) intersection() { lid(); esp_parts(); }
if (which == 26) intersection() { lid(); base(); }
if (which == 27) intersection() { lid(); pad_zone(0); }
if (which == 28) intersection() { lid(); pad_zone(pitch); }
