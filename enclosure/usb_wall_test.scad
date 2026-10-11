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
//   coupon() — base, wall with two USB-C openings, two board cradles
//   key()    — drop-in clip behind one board: takes push-in force on the PCB
//              corners and holds the back of the board down. Print two.
//              It has a window for the board's INNER USB-C connector.
//
// Assembly, per board: lower it into the cradle about 1.5 mm back from the
// wall, slide it forward so the outer USB-C shell enters the opening, then
// drop a key() into the slots behind it.
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

/* [Side-by-side spacing] */
// Port centre spacing = board_w + 2*fit + side_t + pitch_extra.
// With pitch_extra = 3.0 that is about 22.9 mm, which clears two overmolds up
// to ~22 mm wide. Lower it to shrink the box; raise it if your fattest cables
// collide. This is the number the coupon exists to test.
pitch_extra = 3.0;

/* [Fit — tune with this print] */
fit       = 0.20;  // board-to-pocket clearance per side
hole_c    = 0.25;  // shell-to-opening clearance per side
key_fit   = 0.15;  // key blade play in its slot
win_c     = 0.50;  // key window clearance around the inner shell, per side

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

/* [Key (back retainer)] */
install_margin = 0.4;                // extra room to lower the board past the shell overhang
key_t   = usb_over + install_margin; // slot width in Y
back_t  = 2.0;                       // post material behind the slot
lip_t   = 1.2;                       // lip thickness over the board top
lip_len = 1.2;                       // lip reach over the board
grip_h  = 3.0;                       // key sticks up this far above the posts
rib_t   = 2.5;                       // key thickness in Y above the board: stiffens the thin blade

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
y_back     = -(key_t + back_t);
usb_zc     = pcb_t + usb_h / 2;
z_shell_top = pcb_t + usb_h;          // top of the inner USB-C shell
z_rib0      = z_shell_top + win_c;    // stiffening rib starts clear above it
z_rib1      = z_rib0 + grip_h;
z_post_top  = z_rib0;                 // posts guide the key up to the rib

// Inner-shell window in the key, in board-local X
win_x0 = usb_cx - usb_w / 2 - win_c;
win_x1 = usb_cx + usb_w / 2 + win_c;
// The key bears on the PCB back edge outside that window
bear_spans = [[0, win_x0], [win_x1, board_w]];

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
    difference() {
        union() {
            // side rails, flush with board top so the castellated pads stay reachable
            for (xs = [x_in_l - side_t, x_in_r])
                translate([xs, y_back, z_base_top - eps])
                    cube([side_t, y_wall_in - y_back + eps, pcb_t - z_base_top + eps]);
            // ledges under the long edges
            for (xs = [x_in_l, x0 + board_w - ledge_w])
                translate([xs, 0, z_base_top - eps])
                    cube([ledge_w + fit, board_l, -z_base_top + eps]);
            // taller back posts that hold the key
            for (xs = [x_in_l - side_t, x_in_r])
                translate([xs, y_back, z_base_top - eps])
                    cube([side_t, back_t + key_t, z_post_top - z_base_top + eps]);
        }
        // key slots through the back posts
        for (xs = [x_in_l - side_t, x_in_r])
            translate([xs - eps, -key_t, z_base_top])
                cube([side_t + 2 * eps, key_t, z_post_top - z_base_top + 1]);
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

// One key. x0 = that board's left edge. Print two.
//
// Cross-section, looking along X at the board centre:
//
//   z_rib1  ┌────────┐            rib: full length, thick in Y, grips here
//           │  rib   │
//   z_rib0  └────────┘            starts clear above the inner shell
//              ( )                inner USB-C shell passes through, open
//   pcb_t   ┌──┐                  lips (only outside the shell span)
//           │bl│                  lower blade: bears on the WHOLE PCB back edge
//   base    └──┘
//
// Everything between pcb_t and z_rib0 exists only outside the shell span and
// at the two ends that ride in the post slots.
module key(x0) {
    x_in_l = x0 - fit;
    x_in_r = x0 + board_w + fit;
    blade  = key_t - key_fit;
    len    = (x_in_r + side_t) - (x_in_l - side_t) - 0.4;
    xk     = x_in_l - side_t + 0.2;
    y0     = -key_t + key_fit / 2;
    union() {
        // lower blade: full length, up to the board top. Takes push-in force
        // across the whole PCB back edge, including under the connector.
        translate([xk, y0, z_base_top + 0.2])
            cube([len, blade, pcb_t - (z_base_top + 0.2)]);
        // end blocks: ride in the post slots, full height
        for (xs = [xk, x_in_r + 0.0])
            translate([xs, y0, pcb_t])
                cube([side_t - 0.2, blade, z_rib1 - pcb_t]);
        // stiffening rib: full length, clear above the inner shell
        translate([xk, y0 - (rib_t - blade), z_rib0])
            cube([len, rib_t, z_rib1 - z_rib0]);
        // lips over the board top, only outside the shell span
        for (s = bear_spans)
            translate([x0 + s[0], y0, pcb_t + 0.1])
                cube([s[1] - s[0], blade + lip_len, lip_t]);
    }
}

// Ghost boards and shells, preview only (F5)
module board_ghost(x0) {
    %color("SteelBlue", 0.5) translate([x0, 0, 0]) cube([board_w, board_l, pcb_t]);
    // outer shell (into the wall) and inner shell (through the key window)
    %color("Silver", 0.6)
        translate([x0 + usb_cx, board_l + usb_over - 7.35, usb_zc])
            rrect(usb_w, usb_h, usb_h / 2, 7.35);
    %color("Silver", 0.6)
        translate([x0 + usb_cx, -usb_over, usb_zc])
            rrect(usb_w, usb_h, usb_h / 2, 7.35);
}

/* [Output] */
part = "preview"; // [preview, coupon, key]

if (part == "coupon") {
    translate([0, 0, -z_base_bot]) coupon();       // base on the bed
} else if (part == "key") {
    rotate([90, 0, 0]) translate([-x_lo, key_t - key_fit / 2, 0]) key(0);
} else {
    coupon();
    color("DarkOrange") { key(0); key(pitch); }
    board_ghost(0);
    board_ghost(pitch);
}
