// Interference checks for usb_wall_test.scad. Run via tests/check_fit.sh.
// Board numbers come from the model itself through p_*() accessors, so there
// is nothing to keep in sync by hand.
use <../usb_wall_test.scad>
which = 0;

pitch = p_pitch();
bw = p_board()[0]; bl = p_board()[1]; pcb_t = p_board()[2];
usb_w = p_usb()[0]; usb_h = p_usb()[1]; usb_over = p_usb()[2]; usb_cx = p_usb()[3];
install_y = -1.5;   // documented assembly offset: lower the board this far back

notch_d = p_notch()[0]; notch_len = p_notch()[1]; notch_dep = p_notch()[2];
py0 = p_peg_z()[0]; py1 = p_peg_z()[1];
// the real outline, notches included — shared with the model
module board_solid(x0)  { board_outline(x0, pcb_t); }
// the volume of one notch, to prove the peg actually reaches into it
module notch_vol(x0)    { translate([x0, bl - notch_d - notch_len, 0])
                              cube([notch_dep, notch_len, pcb_t]); }
// outer shell: protrudes past the port edge, into the wall opening
module shell_out(x0)    { translate([x0 + usb_cx, bl + usb_over - 7.35, pcb_t + usb_h / 2])
                              rrect(usb_w, usb_h, usb_h / 2, 7.35); }
// inner shell: protrudes past the back edge, through the key's window
module shell_in(x0)     { translate([x0 + usb_cx, -usb_over, pcb_t + usb_h / 2])
                              rrect(usb_w, usb_h, usb_h / 2, 7.35); }
module assembly(x0)     { board_solid(x0); shell_out(x0); shell_in(x0); }
module at_install(x0)   { translate([0, install_y, 0]) assembly(x0); }
// Thin probe at the midpoint between the two overmold pockets, AT POCKET HEIGHT.
// It must stay inside the pocket's Z band, or wall material above the pockets
// keeps the guard non-empty and it passes for the wrong reason.
usb_zc = pcb_t + usb_h / 2;
// It must also sit in the pocket's Y band: the pocket only occupies the outer
// part of the wall, so a probe spanning the full thickness survives on the
// solid inner part and passes for the wrong reason.
module wall_web_probe() {
    translate([usb_cx + pitch / 2 - 0.25, bl + usb_over + 0.2, usb_zc - 0.25])
        cube([0.5, 0.5, 0.5]);
}

// guards: must be NON-empty, else a check below passes for the wrong reason
if (which == 10) shell_out(0);
if (which == 11) coupon();
if (which == 13) shell_in(0);
if (which == 14) intersection() { coupon(); wall_web_probe(); }   // wall between pockets exists
if (which == 16) staple(0);
if (which == 17) intersection() { staple(0); notch_vol(0); }      // peg reaches into the notch
if (which == 18) difference() { translate([0,0,0]) cube([bw, bl, pcb_t]); board_solid(0); }  // notches exist

// collisions: must be empty (or zero-volume contact)
if (which == 1) intersection() { coupon(); board_solid(0); }
if (which == 2) intersection() { coupon(); shell_out(0); }
if (which == 6) intersection() { coupon(); at_install(0); }
if (which == 7) intersection() { coupon(); board_solid(pitch); }
if (which == 8) intersection() { coupon(); shell_out(pitch); }
if (which == 15) intersection() { coupon(); shell_in(0); }
if (which == 20) intersection() { staple(0); board_solid(0); }
if (which == 21) intersection() { staple(0); shell_out(0); }
if (which == 23) intersection() { staple(0); assembly(pitch); }
