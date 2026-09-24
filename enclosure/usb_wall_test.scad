// USB-C wall + cradle test coupon for one Adafruit QT Py RP2040.
//
// Purpose: check port alignment, cable seating, and that plug forces go into
// the enclosure instead of the board's solder joints — before designing the
// full box.
//
// Parts:
//   coupon() — base, wall with USB-C opening, cradle for the board
//   key()    — drop-in clip behind the board: takes push-in force and holds
//              the back of the board down
//
// Assembly: lower the board into the cradle about 1.5 mm back from the wall,
// slide it forward so the USB-C shell enters the opening, then drop key()
// into the slots behind it.
//
// Coordinates (board frame, from Adafruit's Eagle .brd):
//   X = across the board, 0..17.78
//   Y = along the board, 0 = back edge, 20.70 = USB edge
//   Z = 0 at the board's bottom face
//
// Values marked MEASURE are not in the board file. Check them with calipers
// and edit before printing the final enclosure.

/* [Board — Adafruit QT Py RP2040] */
board_w = 17.78;   // from .brd outline
board_l = 20.70;   // from .brd outline
pcb_t   = 1.60;    // MEASURE: PCB thickness (assumed 1.6)

/* [USB-C receptacle] */
usb_w    = 8.94;   // shell width, from footprint outline
usb_h    = 3.26;   // MEASURE: shell height (typical top-mount value)
usb_over = 1.03;   // shell overhang past board edge, from footprint + placement
usb_cx   = 8.89;   // shell centre X, from placement

/* [Fit — tune with this print] */
fit       = 0.20;  // board-to-pocket clearance per side
hole_c    = 0.25;  // shell-to-opening clearance per side
key_fit   = 0.15;  // key blade play in its slot

/* [Wall] */
wall_t    = 2.4;
wall_w    = 32;
wall_top  = pcb_t + usb_h + 5;   // wall height above board bottom

/* [Cable overmold pocket, outer face] */
om_w = 13.0;       // pocket width  (fits most USB-C overmolds)
om_h = 7.2;        // pocket height
om_r = 1.5;        // pocket corner radius
mouth_recess = 0;  // pocket floor distance in front of receptacle mouth

/* [Cradle] */
under_clear = 1.5; // gap under board; tallest underside part ~1.1 (SOD-323)
base_t      = 2.0;
side_t      = 2.0;
ledge_w     = 1.0; // support ledges under the long edges (clear of underside parts)

/* [Key (back retainer)] */
install_margin = 0.4;                // extra room to lower the board past the shell overhang
key_t   = usb_over + install_margin; // slot width in Y
back_t  = 2.0;                       // material behind the slot
lip_t   = 1.2;                       // lip thickness over the board top
lip_len = 1.2;                       // lip reach over the board
grip_h  = 3.0;                       // key sticks up this far above the posts
// Lip only at the back corners: STEMMA QT connector spans X 4.0–10.1,
// reset button X 10.4–14.6 (from .brd).
lip_spans = [[0, 3.4], [15.0, board_w]];

/* [Hidden] */
$fn = 48;
eps = 0.01;

z_base_top = -under_clear;
z_base_bot = -under_clear - base_t;
x_in_l  = -fit;
x_in_r  = board_w + fit;
x_out_l = x_in_l - side_t;
x_out_r = x_in_r + side_t;
y_wall_in  = board_l;
y_wall_out = board_l + wall_t;
y_back     = -(key_t + back_t);
z_post_top = pcb_t + lip_t + 1.0;
usb_zc     = pcb_t + usb_h / 2;

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
        translate([usb_cx - wall_w / 2, y_wall_in, z_base_bot])
            cube([wall_w, wall_t, wall_top - z_base_bot]);
        // shell opening, through
        translate([usb_cx, y_wall_in - eps, usb_zc])
            rrect(usb_w + 2 * hole_c, usb_h + 2 * hole_c, (usb_h + 2 * hole_c) / 2, wall_t + 2 * eps);
        // overmold pocket; floor sits mouth_recess in front of the receptacle mouth
        pocket_d = y_wall_out - (y_wall_in + usb_over + mouth_recess);
        if (pocket_d > 0)
            translate([usb_cx, y_wall_out - pocket_d, usb_zc])
                rrect(om_w, om_h, om_r, pocket_d + eps);
    }
}

module cradle() {
    difference() {
        union() {
            // base plate
            translate([min(x_out_l, usb_cx - wall_w / 2), y_back, z_base_bot])
                cube([max(x_out_r, usb_cx + wall_w / 2) - min(x_out_l, usb_cx - wall_w / 2),
                      y_wall_in - y_back + eps, base_t]);
            // side walls, flush with board top so castellated pads stay reachable
            for (x0 = [x_out_l, x_in_r])
                translate([x0, y_back, z_base_top - eps])
                    cube([side_t, y_wall_in - y_back + eps, pcb_t - z_base_top + eps]);
            // ledges under the long edges
            for (x0 = [x_in_l, board_w - ledge_w])
                translate([x0, 0, z_base_top - eps])
                    cube([ledge_w + fit, board_l, -z_base_top + eps]);
            // taller back posts that hold the key
            for (x0 = [x_out_l, x_in_r])
                translate([x0, y_back, z_base_top - eps])
                    cube([side_t, back_t + key_t, z_post_top - z_base_top + eps]);
        }
        // key slots through the back posts
        for (x0 = [x_out_l, x_in_r])
            translate([x0 - eps, -key_t, z_base_top])
                cube([side_t + 2 * eps, key_t, z_post_top - z_base_top + 1]);
    }
}

module coupon() {
    union() { wall(); cradle(); }
}

module key() {
    blade = key_t - key_fit;
    len   = (x_out_r - x_out_l) - 0.4;
    x0    = x_out_l + 0.2;
    union() {
        // blade: fills the gap behind the board edge, ends ride in the post slots
        translate([x0, -key_t + key_fit / 2, z_base_top + 0.2])
            cube([len, blade, z_post_top + grip_h - z_base_top - 0.2]);
        // corner lips over the board top
        for (s = lip_spans)
            translate([s[0], -key_t + key_fit / 2, pcb_t + 0.1])
                cube([s[1] - s[0], blade + lip_len, lip_t]);
    }
}

// Ghost board and shell, preview only (F5)
module board_ghost() {
    %color("SteelBlue", 0.5) cube([board_w, board_l, pcb_t]);
    %color("Silver", 0.6)
        translate([usb_cx, board_l + usb_over - 7.35, usb_zc])
            rrect(usb_w, usb_h, usb_h / 2, 7.35);
}

/* [Output] */
part = "preview"; // [preview, coupon, key]

if (part == "coupon") {
    // base on the bed
    translate([0, 0, -z_base_bot]) coupon();
} else if (part == "key") {
    // print lying on its back face, lips pointing up
    rotate([90, 0, 0]) translate([0, key_t - key_fit / 2, 0]) key();
} else {
    coupon();
    color("DarkOrange") key();
    board_ghost();
}
