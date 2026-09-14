// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - fpc_cover (spec §10, §4.3): low channel that protects the
// camera FPC (C2) between the front pod and the main case. Printed straight and flat; the thin
// PETG section flexes to the shell curvature (strain ~ h/2R < 2 %). Held by cable clips and
// straps, never glued to the shell. Print 2-3 lengths as needed. Print: PETG, flat, no supports.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
fpc_len     = 150;     // fits a 220 mm bed diagonal comfortably; print several
fpc_ch      = [18, 2.2]; // inner channel (FPC 16 mm wide, 22-pin end ~ 11.5 mm)
roof        = 1.2;
side        = 1.6;
flange      = 6;       // flanges for straps / clips
flange_t    = 1.0;
flex_notch  = [2, 15]; // notch width and pitch in the flanges

body_w = fpc_ch[0] + 2 * side;
body_h = fpc_ch[1] + roof;

module fpc_cover() {
    difference() {
        intersection() {
            union() {
                // body with rounded top corners
                rotate([90, 0, 90]) linear_extrude(fpc_len, center = true)
                    hull() {
                        translate([-body_w / 2, 0]) square([body_w, eps]);
                        for (s = [-1, 1]) translate([s * (body_w / 2 - 1.5), body_h - 1.5]) circle(r = 1.5, $fn = 16);
                    }
                translate([0, 0, flange_t / 2]) cube([fpc_len, body_w + 2 * flange, flange_t], center = true);
            }
            // chamfered ends so nothing snags
            hull() {
                cube([fpc_len, 100, eps], center = true);
                translate([0, 0, body_h]) cube([fpc_len - 2 * body_h, 100, eps], center = true);
            }
        }
        translate([0, 0, -eps]) rotate([90, 0, 90]) linear_extrude(fpc_len + 2, center = true)
            translate([-fpc_ch[0] / 2, 0]) square([fpc_ch[0], fpc_ch[1]]);
        // flex notches in the flanges
        for (x = [-fpc_len / 2 + flex_notch[1] : flex_notch[1] : fpc_len / 2 - 1], s = [-1, 1])
            translate([x, s * (body_w / 2 + flange / 2 + 1), 0]) cube([flex_notch[0], flange + 2, 10], center = true);
        translate([-fpc_len / 2 + 25, 0, body_h - label_depth]) label_text("OWSH FPC", 3, label_depth + 0.2);
    }
}

fpc_cover();
