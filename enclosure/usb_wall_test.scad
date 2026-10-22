// Two-port USB-C wall + cradle test coupon for the Waveshare RP2350-USB-C.
//
// Purpose: check port alignment, cable seating, side-by-side cable crowding,
// and that plug forces go into the enclosure instead of the board's solder
// joints — before designing the full box.
//
// Layout decision (docs/decisions.md): both input ports side by side on one
// face. This coupon prints BOTH, because two plug overmolds fouling each other
// is the main risk of that layout and a one-port coupon cannot show it.
//
// Parts:
//   coupon() — base, wall with two USB-C openings, two board cradles. ONE PART.
//
// Retention: two nubs rise from the cradle floor into the board's edge
// notches. They take plug-in and pull-out force in the plane of the PCB, and
// side-to-side. No loose clips.
//
// Assembly, per board: drop it STRAIGHT DOWN into the cradle so the notches
// land over the nubs. Nothing slides, and nothing needs to thread into the
// wall: the EXPOSED port's shell is flush with the board edge (measured on the
// real board), so the port opening stays a closed hole in a solid wall.
// If a future board has a proud outer shell, that opening has to be slotted
// open to the top again — see commit a5fbb47.
//
// Nothing holds the board DOWN. That is deliberate: the lid does it in the
// full box, and leaving it off here keeps the coupon to one printed part and
// lets you lift a board straight out to inspect the notch fit.
//
// NOT tested by this coupon: blocking the inner USB-C port. That port is live
// on the board's 5V net (hardware/wiring.md), so the full box must make it
// unreachable. The coupon leaves it open so the fit can be inspected.
//
// Coordinates (board A frame):
//   X = across the boards, board A occupies 0..17.50
//   Y = along the boards, 0 = inner (back) edge, 33.00 = outer (port) edge
//   Z = 0 at the board's bottom face
//
// Values marked MEASURE are not in Waveshare's drawing. Check them with
// calipers on a real board and edit before printing the final enclosure.

include <boards.scad>

/* [Coupon-only] */
wall_top  = pcb_t + usb_h + 5;   // wall height above board bottom
wall_pad  = 7;                   // wall overhang past the outer cradle walls

/* [Assembly] */
install_margin = 0.4;   // extra room to lower the board past the shell overhang
back_clear     = 2.0;   // material behind the board, to carry the cradle rails

// Derived ------------------------------------------------------------------
pitch   = board_w + 2 * fit + side_t + pitch_extra;  // board A left edge -> board B left edge
usb_cx_a = usb_cx;
usb_cx_b = pitch + usb_cx;

z_base_top = -under_clear;
z_base_bot = -under_clear - base_t;
y_wall_in  = board_l;
y_wall_out = board_l + wall_t;
y_back     = -back_clear;
usb_zc     = pcb_t + usb_h / 2;

// Notch extents in board-local Y (0 = inner edge, board_l = port edge)
ny1 = board_l - notch_d;
ny0 = ny1 - notch_len;

// Outer extents of the whole coupon
x_lo = -fit - side_t;
x_hi = pitch + board_w + fit + side_t;
wall_x0 = x_lo - wall_pad;
wall_x1 = x_hi + wall_pad;

// Coupon-specific accessors. Board numbers come from boards.scad, which the
// checks include directly, so only coupon geometry needs exporting here.
function p_pitch()  = pitch;
function p_nub()    = [notch_c, nub_h];
function p_pocket() = [om_w, om_h, mouth_recess, wall_t];

module wall() {
    difference() {
        translate([wall_x0, y_wall_in, z_base_bot])
            cube([wall_x1 - wall_x0, wall_t, wall_top - z_base_bot]);
        for (cx = [usb_cx_a, usb_cx_b]) {
            // shell opening, through
            translate([cx, y_wall_in - eps, usb_zc])
                rrect(usb_w + 2 * hole_c, usb_h + 2 * hole_c,
                      (usb_h + 2 * hole_c) / 2, wall_t + 2 * eps);
            // overmold pocket; floor sits mouth_recess in front of the receptacle mouth
            pocket_d = y_wall_out - (y_wall_in + usb_over_out + mouth_recess);
            if (pocket_d > 0)
                translate([cx, y_wall_out - pocket_d, usb_zc])
                    rrect(om_w, om_h, om_r, pocket_d + eps);
        }
    }
}

// One board's cradle. x0 = that board's left edge.
module cradle(x0) {
    x_in_l  = x0 - fit;
    x_in_r  = x0 + board_w + fit;
    union() {
        // side rails, flush with board top so the castellated pads stay reachable
        for (xs = [x_in_l - side_t, x_in_r])
            translate([xs, y_back, z_base_top - eps])
                cube([side_t, y_wall_in - y_back + eps, pcb_t - z_base_top + eps]);
        // ledges under the long edges
        for (xs = [x_in_l, x0 + board_w - ledge_w])
            translate([xs, 0, z_base_top - eps])
                cube([ledge_w + fit, board_l, -z_base_top + eps]);
        // retention nubs, rising from the base into the board's edge notches.
        // These are the only thing holding the board fore-and-aft.
        for (nx = [x0 + notch_c, x0 + board_w - notch_dep + notch_c])
            translate([nx, ny0 + notch_c, z_base_top - eps])
                cube([notch_dep - 2 * notch_c, notch_len - 2 * notch_c,
                      nub_h - z_base_top + eps]);
    }
}

module base_plate() {
    translate([min(x_lo, wall_x0), y_back, z_base_bot])
        cube([max(x_hi, wall_x1) - min(x_lo, wall_x0),
              y_wall_in - y_back + eps, base_t]);
}

module coupon() {
    union() {
        base_plate();
        wall();
        cradle(0);
        cradle(pitch);
    }
}

// Ghost boards and shells, preview only (F5)
module board_ghost(x0) {
    %color("SteelBlue", 0.5) rp_outline(x0, pcb_t);
    // outer shell (into the wall) and the unused inner shell
    %color("Silver", 0.6) rp_shell(x0, "out");
    %color("Silver", 0.6) rp_shell(x0, "in");
}

/* [Output] */
part = "preview"; // [preview, coupon]

if (part == "coupon") {
    translate([0, 0, -z_base_bot]) coupon();       // base on the bed
} else {
    coupon();
    board_ghost(0);
    board_ghost(pitch);
}
