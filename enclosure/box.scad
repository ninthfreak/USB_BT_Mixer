// Full enclosure for USB_BT_Mixer: base + lid.
//
// Layout (decision 2026-10-22, docs/decisions.md):
//   - Two RP2350-USB-C input boards sit flat in cradles at the FRONT, ports
//     side by side through the port wall. Retained by nubs in their edge
//     notches; the lid presses them down.
//   - The ESP32 dev kit sits flat on the BASE behind them, screwed down
//     through its own four mounting holes. Not on the lid.
//   - Lid held by four M3 self-tapping screws into printed bosses.
//
// Antenna: the ESP32's PCB antenna is at the end opposite its USB-C, so it
// ends up at one BACK corner, over empty space. Keep the wiring loom on the
// USB-C side of the ESP32, and print in anything but carbon-fibre-filled
// filament (CLAUDE.md).
//
// Coordinates (same frame as usb_wall_test.scad, extended backwards):
//   X = left to right across the box
//   Y = 0 at an RP board's INNER edge; +Y toward the port wall (the front),
//       -Y toward the back, where the ESP32 lives
//   Z = 0 at an RP board's bottom face
//
// Values marked MEASURE live in boards.scad. Edit them there, not here.

include <boards.scad>

/* [Box] */
side_clear   = 3.0;    // gap from the widest board to the interior wall
service_gap  = 6.0;    // RP inner edges to the ESP32's front edge: wiring space
back_gap     = 8.0;    // ESP32 back edge to the interior back wall
lid_t        = 2.4;
head_clear   = 1.2;    // gap above the tallest component
esp_standoff = 3.0;    // ESP32 PCB underside above the interior floor

/* [Screws — M3 self-tapping into printed bosses] */
m3_pilot   = 2.50;     // self-tapping pilot; M3 cuts its own thread
m3_boss_od = 5.50;
m3_clear   = 3.30;     // lid through-hole
m3_cbore_d = 6.20;     // head counterbore in the lid
m3_cbore_h = 2.20;

/* [ESP32 hold-down screws] */
esp_pilot   = 2.10;    // M2.5 self-tapping
esp_boss_od = 5.00;

/* [Lid alignment lip] */
lip_h = 1.5;
lip_w = 1.2;
lip_c = 0.25;

/* [Lid press pads — where it may touch an RP board] */
// Castellated pads run 2.88..23.20 mm from the inner edge, so the pad-free
// zones are the inner 2.88 mm and the port-end 9.8 mm. These footprints stay
// inside those, clear of both USB-C shells and of the retention notches.
press_x   = [[0.8, 3.8], [board_w - 3.8, board_w - 0.8]];
press_in  = [0.4, 1.8];                    // near the inner edge
press_out = [board_l - 3.1, board_l - 0.6];// near the port edge, ahead of the notches

// ── Derived ──────────────────────────────────────────────────────────────
pitch    = board_w + 2 * fit + side_t + pitch_extra;
usb_cx_a = usb_cx;
usb_cx_b = pitch + usb_cx;

rp_x_lo = -fit - side_t;                 // outer face of board A's left rail
rp_x_hi = pitch + board_w + fit + side_t;
rp_cx   = (rp_x_lo + rp_x_hi) / 2;

esp_x0 = rp_cx - esp_w / 2;              // ESP32 centred on the same axis
esp_x1 = esp_x0 + esp_w;
esp_y1 = -service_gap;                   // ESP32 front edge
esp_y0 = esp_y1 - esp_d;                 // ESP32 back edge
esp_cx = rp_cx;
esp_cy = (esp_y0 + esp_y1) / 2;

in_x0 = min(rp_x_lo, esp_x0) - side_clear;   // interior extents
in_x1 = max(rp_x_hi, esp_x1) + side_clear;
in_y0 = esp_y0 - back_gap;
in_y1 = board_l;                             // port wall inner face

z_floor = -under_clear;                      // interior floor
z_bot   = z_floor - base_t;
// Interior ceiling: clear the tallest thing inside.
esp_top   = z_floor + esp_standoff + esp_t + esp_top_h;
rp_top    = pcb_t + usb_h;
z_ceil    = max(esp_top, rp_top) + head_clear;
z_lid_top = z_ceil + lid_t;

// M3 boss centres: two in the front side channels, two behind the ESP32.
m3_inset = m3_boss_od / 2 + 0.6;
m3_pos = [
    [in_x0 + m3_inset, in_y1 - m3_inset],
    [in_x1 - m3_inset, in_y1 - m3_inset],
    [in_x0 + m3_inset, in_y0 + m3_inset],
    [in_x1 - m3_inset, in_y0 + m3_inset],
];
// ESP32 mounting hole centres
esp_pos = [ for (sx = [-1, 1], sy = [-1, 1])
            [esp_cx + sx * esp_hole_dx / 2, esp_cy + sy * esp_hole_dy / 2] ];

// ── Base ─────────────────────────────────────────────────────────────────

module floor_plate() {
    translate([in_x0 - wall_t, in_y0 - wall_t, z_bot])
        cube([(in_x1 - in_x0) + 2 * wall_t, (in_y1 - in_y0) + 2 * wall_t, base_t]);
}

module outer_walls() {
    difference() {
        translate([in_x0 - wall_t, in_y0 - wall_t, z_bot])
            cube([(in_x1 - in_x0) + 2 * wall_t, (in_y1 - in_y0) + 2 * wall_t,
                  z_ceil - z_bot]);
        translate([in_x0, in_y0, z_floor])
            cube([in_x1 - in_x0, in_y1 - in_y0, z_ceil - z_floor + eps]);
    }
}

// Port openings in the front wall: shell-shaped hole plus a pocket for the
// cable overmold. Same geometry as the validated test coupon.
module port_cutouts() {
    for (cx = [usb_cx_a, usb_cx_b]) {
        translate([cx, in_y1 - eps, pcb_t + usb_h / 2])
            rrect(usb_w + 2 * hole_c, usb_h + 2 * hole_c,
                  (usb_h + 2 * hole_c) / 2, wall_t + 2 * eps);
        pocket_d = (in_y1 + wall_t) - (in_y1 + usb_over_out + mouth_recess);
        if (pocket_d > 0)
            translate([cx, in_y1 + wall_t - pocket_d, pcb_t + usb_h / 2])
                rrect(om_w, om_h, om_r, pocket_d + eps);
    }
}

// One RP board's cradle: side rails, edge ledges, and the two retention nubs.
module cradle(x0) {
    x_in_l = x0 - fit;
    x_in_r = x0 + board_w + fit;
    ny1 = board_l - notch_d;
    ny0 = ny1 - notch_len;
    union() {
        for (xs = [x_in_l - side_t, x_in_r])
            translate([xs, -service_gap, z_floor - eps])
                cube([side_t, in_y1 + service_gap + eps, pcb_t - z_floor + eps]);
        for (xs = [x_in_l, x0 + board_w - ledge_w])
            translate([xs, 0, z_floor - eps])
                cube([ledge_w + fit, board_l, -z_floor + eps]);
        for (nx = [x0 + notch_c, x0 + board_w - notch_dep + notch_c])
            translate([nx, ny0 + notch_c, z_floor - eps])
                cube([notch_dep - 2 * notch_c, notch_len - 2 * notch_c,
                      nub_h - z_floor + eps]);
    }
}

module esp_standoffs() {
    for (p = esp_pos) difference() {
        translate([p[0], p[1], z_floor - eps])
            cylinder(d = esp_boss_od, h = esp_standoff + eps);
        translate([p[0], p[1], z_floor - eps])
            cylinder(d = esp_pilot, h = esp_standoff + 2 * eps);
    }
}

module m3_bosses() {
    for (p = m3_pos) difference() {
        translate([p[0], p[1], z_floor - eps])
            cylinder(d = m3_boss_od, h = z_ceil - z_floor + eps);
        translate([p[0], p[1], z_floor - eps])
            cylinder(d = m3_pilot, h = z_ceil - z_floor + 2 * eps);
    }
}

module base() {
    difference() {
        union() {
            floor_plate();
            outer_walls();
            cradle(0);
            cradle(pitch);
            esp_standoffs();
            m3_bosses();
        }
        port_cutouts();
    }
}

// ── Lid ──────────────────────────────────────────────────────────────────

// Alignment lip around the inside of the walls, interrupted at the bosses.
module lid_lip() {
    difference() {
        difference() {
            translate([in_x0 + lip_c, in_y0 + lip_c, z_ceil - lip_h])
                cube([(in_x1 - in_x0) - 2 * lip_c, (in_y1 - in_y0) - 2 * lip_c, lip_h]);
            translate([in_x0 + lip_c + lip_w, in_y0 + lip_c + lip_w, z_ceil - lip_h - eps])
                cube([(in_x1 - in_x0) - 2 * (lip_c + lip_w),
                      (in_y1 - in_y0) - 2 * (lip_c + lip_w), lip_h + 2 * eps]);
        }
        for (p = m3_pos)
            translate([p[0], p[1], z_ceil - lip_h - eps])
                cylinder(d = m3_boss_od + 2 * lip_c, h = lip_h + 2 * eps);
    }
}

// Posts that reach down from the lid onto the pad-free corners of each board.
module press_posts(x0) {
    for (xr = press_x, yr = [press_in, press_out])
        translate([x0 + xr[0], yr[0], pcb_t])
            cube([xr[1] - xr[0], yr[1] - yr[0], z_ceil - pcb_t]);
}

module lid() {
    difference() {
        union() {
            translate([in_x0 - wall_t, in_y0 - wall_t, z_ceil])
                cube([(in_x1 - in_x0) + 2 * wall_t, (in_y1 - in_y0) + 2 * wall_t, lid_t]);
            lid_lip();
            press_posts(0);
            press_posts(pitch);
        }
        for (p = m3_pos) {
            translate([p[0], p[1], z_ceil - lip_h - eps])
                cylinder(d = m3_clear, h = lid_t + lip_h + 2 * eps);
            translate([p[0], p[1], z_lid_top - m3_cbore_h])
                cylinder(d = m3_cbore_d, h = m3_cbore_h + eps);
        }
    }
}

// ── Ghosts, preview only ─────────────────────────────────────────────────
module ghosts() {
    for (x0 = [0, pitch]) {
        %color("SteelBlue", 0.5) rp_outline(x0, pcb_t);
        %color("Silver", 0.6) rp_shell(x0, "out");
        %color("Silver", 0.6) rp_shell(x0, "in");
    }
    %color("DarkGreen", 0.5)
        translate([esp_x0, esp_y0, z_floor + esp_standoff])
            cube([esp_w, esp_d, esp_t]);
    %color("DimGray", 0.4)
        translate([esp_x0, esp_y0, z_floor + esp_standoff + esp_t])
            cube([esp_w, esp_d, esp_top_h]);
}

/* [Output] */
part = "preview"; // [preview, base, lid, open]

if (part == "base") {
    translate([0, 0, -z_bot]) base();
} else if (part == "lid") {
    // print outer face down: posts and lip point up, no supports
    translate([0, 0, z_lid_top]) rotate([180, 0, 0]) lid();
} else if (part == "open") {
    base();
    translate([0, (in_y1 - in_y0) + 12, 0]) lid();
} else {
    base();
    color("Gainsboro", 0.35) lid();
    ghosts();
}
