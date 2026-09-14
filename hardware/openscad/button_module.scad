// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - button_module (spec §10, §7.2): housing for three
// 12 x 12 mm tactile switches. Worn on the right side above the ear: B1 front (+Y, circle),
// B2 middle (triangle), B3 rear (square). Attach with strap anchor + Dual Lock (spec §4.3).
// Print: PETG, floor on the bed (as exported); the angled strap tabs need a little support (or print
// them flat with `side_R = 1e6`). Top plate bridges < 20 mm.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
sw_size       = 12.0;   // tactile switch body (verify with calipers)
sw_body_h     = 3.5;    // body height without the actuator (verify)
sw_leg_open   = [13.4, 7]; // opening for the 4 legs under each switch
btn_pitch     = 22;     // centre distance between buttons (finger separation)
top_plate_t   = 5.0;
wire_space    = 8.0;    // cavity for bent legs + Dupont housings laid flat
floor_t       = 2.0;
guard_h       = 1.5;    // tactile guard ridges between the buttons
housing_w     = 26;
side_R        = 140;    // shell radius along the module (front-to-back, above the ear) - measure

bm_L = 3 * btn_pitch + 2 * wall;
bm_H = floor_t + wire_space + top_plate_t;
btn_y = [btn_pitch, 0, -btn_pitch];   // B1 front, B2 middle, B3 rear
tab_lift = (strap_tab_w + 3) * sin(asin((bm_L / 2) / side_R));   // tab tips end at the bed / shell

module button_module() {
    difference() {
        union() {
            rounded_box([housing_w, bm_L, bm_H], r = ext_fillet, r_plan = 5);
            // guard ridges between buttons (rounded)
            for (y = [btn_pitch / 2, -btn_pitch / 2]) translate([0, y, bm_H - 1])
                hull() for (sx = [-1, 1]) translate([sx * (housing_w / 2 - 5), 0, 0]) sphere(r = guard_h + 1, $fn = fn_round);
            // strap tabs at both ends (slot across the strap)
            // strap tabs at both ends, angled down to follow the shell (radius side_R along the module)
            for (sy = [-1, 1]) translate([0, sy * (bm_L / 2 - 1), tab_lift]) rotate([-sy * asin((bm_L / 2) / side_R), 0, 0])
                rotate([0, 0, sy > 0 ? 90 : -90]) difference() { strap_tab(); translate([-10, -20, -10]) cube([10, 40, 30]); }
        }
        // cavity for wiring
        translate([0, 0, floor_t]) linear_extrude(wire_space) rounded_rect2d([housing_w - 2 * wall, bm_L - 2 * wall], 2);
        for (y = btn_y) translate([0, y, 0]) {
            // switch pocket from the top
            translate([0, 0, bm_H - sw_body_h]) linear_extrude(sw_body_h + 5) square(sw_size + 2 * clr, center = true);
            // leg opening into the cavity
            translate([0, 0, floor_t + 1]) linear_extrude(bm_H) square(sw_leg_open, center = true);
        }
        // wire exit at the rear end, open toward the shell (sheltered)
        translate([0, -bm_L / 2 + wall / 2, 0]) cable_gland_slot(10, floor_t + 5, wall * 3);
        // debossed "1 2 3" on the outer side face (for sighted helpers) and OWSH label on the other side
        for (i = [0 : 2]) translate([housing_w / 2 + 0.2, btn_y[i], bm_H / 2]) rotate([90, 0, 90]) translate([0, 0, -label_depth - 0.2]) label_text(str("B", i + 1), 4, label_depth + 0.4);
        translate([-housing_w / 2 - 0.2, 0, bm_H / 2]) rotate([90, 0, -90]) translate([0, 0, -label_depth - 0.2]) label_text("OWSH BUTTONS", 3.5, label_depth + 0.4);
    }
}

button_module();
