// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - main case (v1.1, conformal, rear-top): parameters, geometry.
// Used by main_case_base.scad, main_case_lid.scad and assembly_preview.scad.
//
// Case frame (worn): origin = underside centre, z = 0 = top of the 3 mm TPU saddle there.
// Long axis FRONT-TO-BACK (+Y forward). The underside is a ribbed surface that follows the
// shell (radii case_R_lat across, case_R_long along the head); the Pi 5 floor inside stays flat.
// The lid top is capped by an offset of the shell so no point is more than `case_max_h` above it.
// Contents (v1.1): U1 Pi 5 + U2 Active Cooler, S3 GY-521 IMU, L1 LED window.
// D1 ULN2003 and A1 USB audio adapter moved to aux_pod (they cannot fit inside a ~100 x 72 mm
// footprint under the 40 mm height cap - see README).

include <owsh_common.scad>

// ======================= helmet + limits ======================================
case_R_lat  = 110;   // shell radius across the head under the case (measure)
case_R_long = 140;   // shell radius along the head under the case (measure)
case_max_h  = 39.6;  // cap: height above the shell at any point incl. 3 mm saddle (40 mm target, 0.4 mm margin)

// ======================= Raspberry Pi 5 (spec §4.4) - verify with calipers =====
pi_pcb          = [56, 85, 1.6];  // X (across) x Y (along) in this orientation
pi_hole_pitch   = [49, 58];
pi_hole_inset   = 3.5;
pi_standoff_h   = 5;      // spec F1
pi_total_h      = 22;     // top of Active Cooler above the PCB bottom
pi_cooler_rect  = [4, 6, 48, 62]; // cooler footprint on the PCB [x0, y0 from hole end, w, l] (verify)
pi_usb_overhang = 2.5;    // USB / Ethernet jacks overhang at the REAR end (-Y)
pi_usb_h        = 16;     // USB / Ethernet stack height above the PCB top
pi_usb_len      = 21;     // stack length along Y from the rear edge
pi_usbc_y       = 11.2;   // USB-C centre from the HOLE end (front) along the -X long edge (verify)
pi_usbc_open    = [13, 8];
pi_usb2_x       = 47;     // USB 2.0 stack centre from the -X edge (verify)
pi_header_x     = 52.5;   // 40-pin header centre from the -X edge
pi_header_y     = [7, 58];// header span from the hole end (front)
dupont_h        = 16;     // header pins + Dupont housings above the PCB top
led_d           = 3.0;

// ======================= IMU ===================================================
imu_size   = [21, 16, 3];   // GY-521 (card slot, stands upright at the front end)
imu_slot_w = 1.8;           // PCB thickness + clearance (verify)
imu_gap    = 6;             // length reserved for the IMU slot in front of the Pi

// ======================= housing ===============================================
cw        = 1.8;    // case wall (4 lines of 0.45)
cfloor    = 1.6;
clid      = 1.8;
c_gap     = 1.2;    // air gap cooler -> lid
rib_pitch = 16;
rib_t     = 1.6;
lid_boss_d = 6.4;

in_W = pi_pcb[0] + 2 * 1.5;
in_L = pi_pcb[1] + pi_usb_overhang + 1 + imu_gap + 1;
case_W = in_W + 2 * cw;
case_L = in_L + 2 * cw;
pf_z   = cfloor;                          // Pi floor top (flat)
pcb_bot = pf_z + pi_standoff_h;
pcb_top = pcb_bot + pi_pcb[2];
lid_under = pcb_bot + pi_total_h + c_gap; // flat part of the lid underside
lid_top   = lid_under + clid;
d_cap     = case_max_h - saddle_t;       // offset surface that caps the lid top
Rl = case_R_lat; Rg = case_R_long;

// PCB placement: centred across, rear (USB) edge near the rear wall
pi_x0 = -pi_pcb[0] / 2;
pi_y_rear = -in_L / 2 + pi_usb_overhang + 1;
pi_y_front = pi_y_rear + pi_pcb[1];
function pcb_xy(px, py_from_front) = [pi_x0 + px, pi_y_front - py_from_front];
pi_holes = [for (i = [0, 1], j = [0, 1]) pcb_xy(pi_hole_inset + i * pi_hole_pitch[0], pi_hole_inset + j * pi_hole_pitch[1])];
lid_bosses = [for (sx = [-1, 1], sy = [-1, 1]) [sx * (in_W / 2 - lid_boss_d / 2 + 1.2), sy * (in_L / 2 - lid_boss_d / 2 + 1.2)]];
imu_c  = [0, pi_y_front + 1 + imu_gap / 2];
led_xy = pcb_xy(pi_usb2_x - 18, pi_pcb[1] - 10);   // above the Ethernet / USB 3 stack (low part of the lid)

function surf_z(x, y, d) = d - esag(x, y, Rl + d, Rg + d);     // height of the offset surface d above (x, y)
function lid_under_at(x, y) = min(lid_under, surf_z(x, y, d_cap - clid));
// clearance checks of the tallest Pi parts against the capped lid underside
chk = [
  ["cooler", min([for (px = [pi_cooler_rect[0], pi_cooler_rect[0] + pi_cooler_rect[2]], py = [pi_cooler_rect[1], pi_cooler_rect[1] + pi_cooler_rect[3]])
                   let(p = pcb_xy(px, py)) lid_under_at(p[0], p[1]) - (pcb_bot + pi_total_h)])],
  ["USB stacks", min([for (px = [2, pi_pcb[0] - 2]) let(p = [pi_x0 + px, pi_y_rear - pi_usb_overhang]) lid_under_at(p[0], p[1]) - (pcb_top + pi_usb_h)])],
  ["header + Dupont", min([for (py = pi_header_y) let(p = pcb_xy(pi_header_x, py)) lid_under_at(p[0] + 3, p[1]) - (pcb_top + dupont_h)])],
  ["IMU", lid_under_at(imu_size[0] / 2, imu_c[1]) - (pf_z + imu_size[1] + 1)]
];
echo(str("OWSH main case: footprint ", case_L, " (along) x ", case_W, " (across) mm, centre height above shell ",
         lid_top + saddle_t, " mm, cap ", case_max_h, " mm"));
for (c = chk) echo(str("OWSH main case clearance ", c[0], ": ", c[1], " mm", c[1] < 0 ? "  <-- COLLISION" : ""));

// ======================= regions =================================================
module fp2d(grow = 0, r = 5) rounded_rect2d([case_W + 2 * grow, case_L + 2 * grow], r + grow);
module prism(grow = 0, r = 5) translate([0, 0, -80]) linear_extrude(200) fp2d(grow, r);

module case_openings() {
    // USB-C power on the -X long side
    p = pcb_xy(0, pi_usbc_y);
    translate([-case_W / 2 + cw / 2, p[1], pcb_top + 1.6]) rotate([0, 90, 0]) linear_extrude(cw * 4, center = true) rounded_rect2d([pi_usbc_open[1], pi_usbc_open[0]], 3);
    // USB 2.0 access at the rear end (short USB extension to the aux pod audio adapter)
    translate([pi_x0 + pi_usb2_x, -case_L / 2 + cw / 2, pcb_top + 7]) rotate([90, 0, 0]) linear_extrude(cw * 4, center = true) rounded_rect2d([16, 15], 3);
    // sheltered cable notches at the bottom of the walls (open toward the shell)
    for (c = [[-12, case_L / 2, 18, 4], [12, case_L / 2, 14, 8], [18, -case_L / 2, 14, 8]])   // front: FPC + I2C; rear: GPIO
        translate([c[0], c[1] - sign(c[1]) * cw, -esag(c[0], c[1], Rl, Rg) - 1]) cable_gland_slot(c[2], c[3] + esag(c[0], c[1], Rl, Rg) + 1 + cfloor, cw * 4);
    // louvres (outer opening lower than the inner one): both long sides + rear end
    for (sx = [-1, 1]) translate([sx * (case_W / 2 - cw / 2), 8, pcb_top + 9]) rotate([0, 0, sx > 0 ? -90 : 90]) louvre_vents([44, 10], cw, 1.8, 3.6);
    // drain holes at the rear corners
    for (sx = [-1, 1]) translate([sx * (in_W / 2 - 4), -in_L / 2 + 3, -20]) cylinder(d = 2.5, h = 30, $fn = 16);
}

module plinth_cells() {
    // cells between ribs, open toward the shell (keeps mass low; the saddle bridges them)
    intersection() {
        prism(-cw);
        below_plane(0);
        difference() {
            below_plane(0);
            for (x = [-60 : rib_pitch : 60]) translate([x - rib_t / 2, -100, -100]) cube([rib_t, 200, 200]);
            for (y = [-80 : rib_pitch : 80]) translate([-100, y - rib_t / 2, -100]) cube([200, rib_t, 200]);
        }
    }
}

module case_inner_parts() {
    for (p = pi_holes) translate([p[0], p[1], pf_z - eps]) screw_boss(pi_standoff_h + eps, 5.6, m25_pilot_d(), pi_standoff_h + 1);
    // IMU card slot (two grooved posts), board across X
    for (sx = [-1, 1]) translate([sx * (imu_size[0] / 2 - 0.5), imu_c[1], pf_z - eps]) difference() {
        translate([0, 0, 4]) cube([4, imu_slot_w + 3.2, 8], center = true);
        translate([sx < 0 ? 1 : -1, 0, 4.5]) cube([4, imu_slot_w, 10], center = true);
    }
    for (p = lid_bosses) translate([p[0], p[1], -20]) cylinder(d = lid_boss_d, h = 80, $fn = fn_hole);
}

module main_case_base() {
    difference() {
        union() {
            intersection() {
                prism();
                above_surf(0, Rl, Rg);
                below_plane(lid_under);
                below_surf(d_cap - clid, Rl, Rg);
                union() {
                    difference() { prism(); prism(-cw); }
                    intersection() { prism(-cw); below_plane(pf_z); }       // floor + plinth
                    intersection() { prism(-cw + eps); above_plane(pf_z - eps); case_inner_parts(); }
                }
            }
            // strap tabs on both long sides, following the shell
            for (sx = [-1, 1]) let(x = sx * (case_W / 2 - 1))
                translate([x, 0, -esag(x, 0, Rl, Rg)]) rotate([0, sx * asin((case_W / 2) / Rl), 0]) mirror([sx < 0 ? 1 : 0, 0, 0])
                    difference() { strap_tab(); translate([-10, -20, -10]) cube([10, 40, 30]); }
        }
        plinth_cells();
        case_openings();
        for (p = lid_bosses) translate([p[0], p[1], lid_under_at(p[0], p[1]) + eps]) pilot_hole(m25_pilot_d(), 8);
    }
}

// ======================= lid =================================================
module lid_under_solid() intersection() { below_plane(lid_under); below_surf(d_cap - clid, Rl, Rg); }
module lid_top_solid()   intersection() { below_plane(lid_top);   below_surf(d_cap, Rl, Rg); }

module main_case_lid() {
    difference() {
        union() {
            intersection() {
                prism(0.6);
                difference() { lid_top_solid(); lid_under_solid(); }
            }
            // locating lip inside the walls
            intersection() {
                difference() { prism(-cw - clr); prism(-cw - clr - 1.2); }
                difference() { lid_under_solid(); translate([0, 0, -3]) lid_under_solid(); }
            }
            // LED holder tube
            intersection() {
                translate([led_xy[0], led_xy[1], -10]) cylinder(d = led_d + 3.2, h = 60, $fn = fn_hole);
                difference() { lid_under_solid(); translate([0, 0, -3]) lid_under_solid(); }
            }
        }
        for (p = lid_bosses) translate([p[0], p[1], -10]) {
            cylinder(d = m25_clear_d, h = 80, $fn = fn_hole);
            translate([0, 0, min(lid_top, surf_z(p[0], p[1], d_cap)) + 10 - 1.2]) cylinder(d = m25_head_d + 0.6, h = 5, $fn = fn_hole);
        }
        for (p = lid_bosses) intersection() { translate([p[0], p[1], -10]) cylinder(d = lid_boss_d + 2 * clr, h = 80, $fn = fn_hole); lid_under_solid(); }
        translate([led_xy[0], led_xy[1], -10]) cylinder(d = led_d + 2 * clr, h = 80, $fn = fn_hole);
        // extra air over the fan
        intersection() {
            p = pcb_xy(pi_cooler_rect[0] + pi_cooler_rect[2] / 2, pi_cooler_rect[1] + pi_cooler_rect[3] / 2);
            translate([p[0], p[1], lid_under - eps]) linear_extrude(0.8) rounded_rect2d([40, 40], 4);
        }
        translate([0, -8, lid_top - label_depth]) rotate([0, 0, 90]) part_label("MAIN CASE", 5, label_depth + 0.2);
    }
}

module main_case_base_print() main_case_base();
module main_case_lid_print()  translate([0, 0, lid_top]) rotate([180, 0, 0]) main_case_lid();

function case_footprint() = [case_W, case_L];   // [across, along]
function case_height() = lid_top + saddle_t;
module case_saddle_worn() intersection() { prism(); above_surf(-saddle_t, Rl, Rg); below_surf(0, Rl, Rg); }
