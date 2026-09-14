// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - aux pod (v1.1, NEW): low conformal pod on the back of the
// head, below the main case. Holds D1 ULN2003 driver board and A1 USB audio adapter, which do
// not fit inside the main case under its 40 mm height cap. Fully conformal: floor, lid underside
// and lid top are offset surfaces of the shell, so the height above the shell is uniform.
//
// Pod frame (worn): origin = underside centre (top of the 3 mm saddle), +X along the long axis
// (across the back of the head, user's right), +Y up the head toward the crown, +Z outward.

include <owsh_common.scad>

aux_R_lat  = 110;   // shell radius along X (around the back of the head) - measure
aux_R_long = 140;   // shell radius along Y (up the back of the head) - measure

uln_size   = [35, 32, 15];   // ULN2003 board (verify; hole pattern varies -> corner cradle)
audio_size = [50, 18, 10];   // USB audio adapter (verify)
aw = 1.8; afloor = 1.6; alid = 1.8; agap = 0.6;
mid_gap = 8;                 // between the two bays (holds lid screws)

a_in_L = 1 + uln_size[0] + mid_gap + audio_size[0] + 1;
a_in_W = uln_size[1] + 2;
aux_L = a_in_L + 2 * aw;
aux_W = a_in_W + 2 * aw;
aRl = aux_R_lat; aRg = aux_R_long;
function chord_sag(len, R) = R - sqrt(R * R - len * len / 4);
a_d_under = afloor + max(uln_size[2] + chord_sag(uln_size[0], aRl + afloor), audio_size[2] + chord_sag(audio_size[0], aRl + afloor)) + agap;
a_d_top   = a_d_under + alid;
uln_x   = -a_in_L / 2 + 1 + uln_size[0] / 2;
audio_x =  a_in_L / 2 - 1 - audio_size[0] / 2;
gap_x   = -a_in_L / 2 + 1 + uln_size[0] + mid_gap / 2;
function az(x, y, d) = d - esag(x, y, aRl + d, aRg + d);
a_bosses = [[gap_x, a_in_W / 2 - 3.2], [gap_x, -a_in_W / 2 + 3.2], [a_in_L / 2 - 5, a_in_W / 2 - 3.2], [a_in_L / 2 - 5, -a_in_W / 2 + 3.2]];

echo(str("OWSH aux pod: footprint ", aux_L, " x ", aux_W, " mm, height above shell ", a_d_top + saddle_t, " mm"));

module a_prism(grow = 0) translate([0, 0, -80]) linear_extrude(200) rounded_rect2d([aux_L + 2 * grow, aux_W + 2 * grow], 5 + grow);
module a_under() below_surf(a_d_under, aRl, aRg);
module a_top()   below_surf(a_d_top, aRl, aRg);

module aux_pod_base() {
    difference() {
        union() {
            intersection() {
                a_prism(); above_surf(0, aRl, aRg); a_under();
                union() {
                    difference() { a_prism(); a_prism(-aw); }
                    intersection() { a_prism(-aw); below_surf(afloor, aRl, aRg); }
                    intersection() {
                        a_prism(-aw + eps); above_surf(afloor - eps, aRl, aRg);
                        union() {
                            // ULN2003 corner cradle posts
                            for (sx = [-1, 1], sy = [-1, 1]) translate([uln_x + sx * (uln_size[0] / 2 + clr), sy * (uln_size[1] / 2 + clr), -20])
                                difference() {
                                    translate([sx < 0 ? -1.6 : -6, sy < 0 ? -1.6 : -6, 0]) cube([7.6, 7.6, 20 + afloor + 7]);
                                    translate([sx < 0 ? 0 : -8, sy < 0 ? 0 : -8, -1]) cube([8, 8, 40]);
                                }
                            // audio adapter side rails
                            for (sy = [-1, 1]) translate([audio_x - audio_size[0] / 2 + 6, sy * (audio_size[1] / 2 + clr) + (sy < 0 ? -1.6 : 0), -20])
                                cube([audio_size[0] - 12, 1.6, 20 + afloor + 6]);
                            for (p = a_bosses) translate([p[0], p[1], -20]) cylinder(d = 6, h = 60, $fn = fn_hole);
                        }
                    }
                }
            }
            // strap tabs on both ends, following the shell
            for (sx = [-1, 1]) let(x = sx * (aux_L / 2 - 1))
                translate([x, 0, -esag(x, 0, aRl, aRg)]) rotate([0, sx * asin((aux_L / 2) / aRl), 0]) mirror([sx < 0 ? 1 : 0, 0, 0])
                    difference() { strap_tab(); translate([-10, -20, -10]) cube([10, 40, 30]); }
        }
        // headset jacks at the +X end
        translate([aux_L / 2 - aw / 2, 0, az(aux_L / 2, 0, afloor) + audio_size[2] / 2 + 0.5]) rotate([0, 90, 0])
            linear_extrude(aw * 4, center = true) rounded_rect2d([audio_size[2] + 2, audio_size[1]], 3);
        // cable notches, open toward the shell: USB extension + GPIO in (top wall), motor leads out (bottom wall)
        for (c = [[audio_x - 15, 1, 12, 7], [uln_x, 1, 14, 7], [uln_x, -1, 16, 6]])
            translate([c[0], c[1] * (aux_W / 2 - aw), -esag(c[0], c[1] * aux_W / 2, aRl, aRg) - 1])
                cable_gland_slot(c[2], c[3] + esag(c[0], c[1] * aux_W / 2, aRl, aRg) + 1, aw * 4);
        for (p = a_bosses) translate([p[0], p[1], az(p[0], p[1], a_d_under) + eps]) pilot_hole(m25_pilot_d(), 7);
        // drain holes at the lower corners
        for (sx = [-1, 1]) translate([sx * (a_in_L / 2 - 3), -a_in_W / 2 + 2.5, -30]) cylinder(d = 2.5, h = 40, $fn = 16);
    }
}

module aux_pod_lid() {
    difference() {
        union() {
            intersection() { a_prism(0.6); difference() { a_top(); a_under(); } }
            intersection() {
                difference() { a_prism(-aw - clr); a_prism(-aw - clr - 1.2); }
                difference() { a_under(); translate([0, 0, -2.5]) a_under(); }
            }
        }
        for (p = a_bosses) {
            translate([p[0], p[1], -20]) cylinder(d = m25_clear_d, h = 80, $fn = fn_hole);
            translate([p[0], p[1], az(p[0], p[1], a_d_top) - 1.2]) cylinder(d = m25_head_d + 0.6, h = 5, $fn = fn_hole);
            intersection() { translate([p[0], p[1], -20]) cylinder(d = 6 + 2 * clr, h = 80, $fn = fn_hole); a_under(); }
        }
        translate([-8, 0, az(0, 0, a_d_top) - label_depth]) part_label("AUX POD", 4.5, label_depth + 0.4);
    }
}

module aux_pod_base_print() aux_pod_base();
module aux_pod_lid_print() translate([0, 0, a_d_top]) rotate([180, 0, 0]) aux_pod_lid();
function aux_footprint() = [aux_L, aux_W];
function aux_height() = a_d_top + saddle_t;
module aux_saddle_worn() intersection() { a_prism(); above_surf(-saddle_t, aRl, aRg); below_surf(0, aRl, aRg); }
