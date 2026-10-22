// Interference checks for usb_wall_test.scad. Run via tests/check_fit.sh.
// Board numbers come from the model itself through p_*() accessors, so there
// is nothing to keep in sync by hand.
use <../usb_wall_test.scad>
which = 0;

pitch = p_pitch();
bw = p_board()[0]; bl = p_board()[1]; pcb_t = p_board()[2];
usb_w = p_usb()[0]; usb_h = p_usb()[1]; usb_over = p_usb()[2]; usb_cx = p_usb()[3];
notch_d = p_notch()[0]; notch_len = p_notch()[1]; notch_dep = p_notch()[2];
notch_c = p_nub()[0]; nub_h = p_nub()[1];
usb_zc = pcb_t + usb_h / 2;
SWEEP = 25;   // how far up the board is lifted for the straight-down drop test

// the real outline, notches included — shared with the model
module board_solid(x0)  { board_outline(x0, pcb_t); }
module shell_out(x0)    { translate([x0 + usb_cx, bl + usb_over - 7.35, usb_zc])
                              rrect(usb_w, usb_h, usb_h / 2, 7.35); }
module shell_in(x0)     { translate([x0 + usb_cx, -usb_over, usb_zc])
                              rrect(usb_w, usb_h, usb_h / 2, 7.35); }
module assembly(x0)     { board_solid(x0); shell_out(x0); shell_in(x0); }

// The volume swept by the board as it is lowered straight down into place.
// The shells are convex, so hull(shape, shape raised) is exactly their sweep.
// If this is clear of the coupon, the board drops in without sliding.
module drop_sweep(x0) {
    board_outline(x0, pcb_t + SWEEP);
    hull() { shell_out(x0); translate([0, 0, SWEEP]) shell_out(x0); }
    hull() { shell_in(x0);  translate([0, 0, SWEEP]) shell_in(x0); }
}

// one notch's volume, to prove a nub actually reaches into it
module notch_vol(x0)    { translate([x0, bl - notch_d - notch_len, 0])
                              cube([notch_dep, notch_len, pcb_t]); }
// Thin probe midway between the two cable pockets, at pocket height AND in the
// pocket's Y band: a probe spanning the whole wall survives on solid material
// behind the pockets and passes for the wrong reason.
module wall_web_probe() {
    translate([usb_cx + pitch / 2 - 0.25, bl + usb_over + 0.2, usb_zc - 0.25])
        cube([0.5, 0.5, 0.5]);
}

// guards: must be NON-empty, else a check below passes for the wrong reason
if (which == 10) shell_out(0);
if (which == 11) coupon();
if (which == 13) shell_in(0);
if (which == 14) intersection() { coupon(); wall_web_probe(); }
if (which == 17) intersection() { coupon(); notch_vol(0); }       // nub reaches into the notch
if (which == 18) difference() { cube([bw, bl, pcb_t]); board_solid(0); }  // notches exist
if (which == 19) intersection() { coupon(); notch_vol(pitch); }   // board B's nub too

// collisions: must be empty (or zero-volume contact)
if (which == 1) intersection() { coupon(); board_solid(0); }
if (which == 2) intersection() { coupon(); shell_out(0); }
if (which == 7) intersection() { coupon(); board_solid(pitch); }
if (which == 8) intersection() { coupon(); shell_out(pitch); }
if (which == 15) intersection() { coupon(); shell_in(0); }
if (which == 24) intersection() { coupon(); drop_sweep(0); }      // drops straight in
if (which == 25) intersection() { coupon(); drop_sweep(pitch); }
