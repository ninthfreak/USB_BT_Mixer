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
// land over the nubs. Nothing slides. For that to work the port opening is
// slotted open to the top of the wall, so the USB-C shell drops in from above;
// in the full box the lid caps that slot.
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

/* [Board — Waveshare RP2350-USB-C] */
board_w = 17.50;   // Waveshare dimensioned drawing
board_l = 33.00;   // Waveshare dimensioned drawing
board_r = 2.00;    // corner radius, drawing (cradle is square; this is reference)
pcb_t   = 1.60;    // MEASURE: PCB thickness (assumed 1.6)

/* [USB-C receptacles — one at each end, centred] */
usb_w    = 8.90;   // shell width: board_w - 2*4.30, from the drawing
usb_h    = 3.26;   // MEASURE: shell height (typical top-mount value)
usb_over = 1.03;   // MEASURE: shell overhang past the board edge (QT Py value)
usb_cx   = board_w / 2;   // centred, from the drawing

/* [Retention notches — port end only] */
// Two rectangular cutouts, one in each long edge, near the exposed port end.
// Waveshare does NOT dimension them; these come from measuring their drawing
// pixel by pixel, so treat them as +/- 0.15 mm and MEASURE on a real board.
// The inner end has no notches: what looks like notches there is the row of
// castellated pads (about 0.5 mm deep).
notch_d   = 3.45;  // MEASURE: notch's near edge, from the port edge
notch_len = 2.00;  // MEASURE: length along the board
notch_dep = 1.50;  // MEASURE: depth into each long edge
notch_c   = 0.15;  // nub clearance per face
nub_h     = pcb_t; // nub top, flush with the board's top face

/* [Side-by-side spacing] */
// Port centre spacing = board_w + 2*fit + side_t + pitch_extra.
// With pitch_extra = 3.0 that is about 22.9 mm, which clears two overmolds up
// to ~22 mm wide. Lower it to shrink the box; raise it if your fattest cables
// collide. This is the number the coupon exists to test.
pitch_extra = 3.0;

/* [Fit — tune with this print] */
fit       = 0.20;  // board-to-pocket clearance per side
hole_c    = 0.25;  // shell-to-opening clearance per side

/* [Wall] */
wall_t    = 2.4;
wall_top  = pcb_t + usb_h + 5;   // wall height above board bottom
wall_pad  = 7;                   // wall overhang past the outer cradle walls

/* [Cable overmold pockets, outer face] */
om_w = 13.0;       // pocket width  (fits most USB-C overmolds)
om_h = 7.2;        // pocket height
om_r = 1.5;        // pocket corner radius
mouth_recess = 0;  // pocket floor distance in front of receptacle mouth

/* [Cradle] */
under_clear = 1.5; // MEASURE: gap under board for underside parts
base_t      = 2.0;
side_t      = 2.0;
ledge_w     = 1.0; // support ledges under the long edges

/* [Assembly] */
install_margin = 0.4;   // extra room to lower the board past the shell overhang
back_clear     = 2.0;   // material behind the board, to carry the cradle rails

/* [Hidden] */
$fn = 48;
eps = 0.01;

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

// Accessors so tests/fit_checks.scad never duplicates these numbers.
// OpenSCAD's `use <>` imports functions and modules, but not variables.
function p_pitch()  = pitch;
function p_board()  = [board_w, board_l, pcb_t];
function p_usb()    = [usb_w, usb_h, usb_over, usb_cx];
function p_margin() = install_margin;
function p_notch()  = [notch_d, notch_len, notch_dep];
function p_nub()    = [notch_c, nub_h];

// The board outline, notches included. Shared by the preview and the checks.
module board_outline(x0, h) {
    difference() {
        translate([x0, 0, 0]) cube([board_w, board_l, h]);
        translate([x0 - eps, ny0, -eps])
            cube([notch_dep + eps, notch_len, h + 2 * eps]);
        translate([x0 + board_w - notch_dep, ny0, -eps])
            cube([notch_dep + eps, notch_len, h + 2 * eps]);
    }
}

module rrect(w, h, r, d) {
    // rounded rectangle in XZ, centred, extruded along +Y by d
    // hull of corner circles: stays valid when r = h/2 (stadium shape),
    // where offset() of a zero-height square would produce nothing
    rr = min(r, w / 2, h / 2);
    rotate([-90, 0, 0])
        linear_extrude(d)
            hull()
                for (sx = [-1, 1], sz = [-1, 1])
                    translate([sx * (w / 2 - rr), sz * (h / 2 - rr)]) circle(rr);
}

module wall() {
    difference() {
        translate([wall_x0, y_wall_in, z_base_bot])
            cube([wall_x1 - wall_x0, wall_t, wall_top - z_base_bot]);
        for (cx = [usb_cx_a, usb_cx_b]) {
            // shell opening, through
            translate([cx, y_wall_in - eps, usb_zc])
                rrect(usb_w + 2 * hole_c, usb_h + 2 * hole_c,
                      (usb_h + 2 * hole_c) / 2, wall_t + 2 * eps);
            // drop slot: open from the opening up to the wall top, so the
            // shell can come straight down into it. The lid caps this.
            translate([cx - (usb_w + 2 * hole_c) / 2, y_wall_in - eps, usb_zc])
                cube([usb_w + 2 * hole_c, wall_t + 2 * eps, wall_top - usb_zc + eps]);
            // overmold pocket; floor sits mouth_recess in front of the receptacle mouth
            pocket_d = y_wall_out - (y_wall_in + usb_over + mouth_recess);
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
    %color("SteelBlue", 0.5) board_outline(x0, pcb_t);
    // outer shell (into the wall) and the unused inner shell
    %color("Silver", 0.6)
        translate([x0 + usb_cx, board_l + usb_over - 7.35, usb_zc])
            rrect(usb_w, usb_h, usb_h / 2, 7.35);
    %color("Silver", 0.6)
        translate([x0 + usb_cx, -usb_over, usb_zc])
            rrect(usb_w, usb_h, usb_h / 2, 7.35);
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
