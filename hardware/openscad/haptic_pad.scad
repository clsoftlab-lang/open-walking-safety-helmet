// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - haptic_pad (spec §10, §4.3): TPU pad holding one coin
// ERM motor (type 1027, 10 x 2.7 mm). Qty 3: left temple (M1), forehead centre (M2), right
// temple (M3). Hook tape goes in the recess on the back; it grips the helmet comfort padding.
// Never glue anything to the EPS liner (P1).
// Print: TPU 95A, skin side (thin membrane) on the bed (as exported), no supports.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
motor_d      = 10.0;   // verify with calipers
motor_t      = 2.7;
pad_size     = [32, 26];
membrane_t   = 0.8;    // between motor and head: thin for a crisp vibration
roof_t       = 1.2;
velcro_recess = [26, 20, 0.6];
lead_channel = [3.0, 1.8];
pad_letter   = "C";    // "L", "C" or "R" - debossed in the velcro recess

pocket_d = motor_d + 2 * clr + 0.3;
pocket_h = motor_t + 0.2;
pad_t = membrane_t + pocket_h + roof_t + velcro_recess[2];

module haptic_pad(letter = pad_letter) {
    difference() {
        rounded_box([pad_size[0], pad_size[1], pad_t], r = 2, r_plan = 6);
        // motor pocket + side insertion slot + lead channel to the edge
        translate([0, 0, membrane_t]) {
            cylinder(d = pocket_d, h = pocket_h, $fn = 48);
            translate([0, -pocket_d / 2, 0]) cube([pad_size[0], pocket_d * 0.8, pocket_h]);
        }
        translate([0, -lead_channel[0] / 2, membrane_t]) cube([pad_size[0], lead_channel[0], lead_channel[1] + pocket_h]);
        // velcro recess on the back
        translate([0, 0, pad_t - velcro_recess[2]]) linear_extrude(1) rounded_rect2d([velcro_recess[0], velcro_recess[1]], 3);
        translate([-8, 6, pad_t - velcro_recess[2] - 0.4]) label_text(letter, 6, 1);
    }
}

haptic_pad();
