// Interference checks for usb_wall_test.scad. Run via tests/check_fit.sh.
// Board/shell numbers must match usb_wall_test.scad.
use <../usb_wall_test.scad>
which = 0;
pcb_t = 1.6; usb_w = 8.94; usb_h = 3.26; usb_over = 1.03; usb_cx = 8.89;
bw = 17.78; bl = 20.70;
module board_solid() { cube([bw, bl, pcb_t]); }
module shell_solid() { translate([usb_cx, bl + usb_over - 7.35, pcb_t + usb_h / 2]) rrect(usb_w, usb_h, usb_h / 2, 7.35); }
module stemma()      { translate([4.0, 0.30, pcb_t]) cube([6.1, 4.25, 2.5]); }  // from .brd
module board_install() { translate([0, -1.5, 0]) { board_solid(); shell_solid(); } }
// guards: must be non-empty
if (which == 10) shell_solid();
if (which == 11) coupon();
if (which == 12) key();
// collisions: must be empty (or zero-volume contact)
if (which == 1) intersection() { coupon(); board_solid(); }
if (which == 2) intersection() { coupon(); shell_solid(); }
if (which == 3) intersection() { coupon(); key(); }
if (which == 4) intersection() { key(); board_solid(); }
if (which == 5) intersection() { key(); stemma(); }
if (which == 6) intersection() { coupon(); board_install(); }
