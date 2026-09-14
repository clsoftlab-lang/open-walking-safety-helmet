// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - cable_clip (spec §10): snap clips on a Dual Lock base,
// "bundle" type for Dupont bundles and "fpc" type that snaps over the fpc_cover channel.
// Qty 6 (this plate: 3 bundle + 3 fpc). Clips are placed under the straps, never glued to EPS.
// Print: PETG, lying on the side (profile on the bed, as exported), no supports.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
clip_width  = 8;      // along the cable
base        = [20, 2.0];
bundle_d    = 6.0;    // Dupont bundle diameter
hoop_t      = 1.6;
snap_open   = 0.7;    // opening as fraction of bundle_d
fpc_cover_w = 24.2;   // outer width of fpc_cover body (see fpc_cover.scad) + clearance
fpc_cover_h = 3.9;
n_bundle    = 3;
n_fpc       = 3;

module bundle_profile() {
    r = bundle_d / 2;
    difference() {
        union() {
            translate([-base[0] / 2, 0]) square([base[0], base[1]]);
            translate([0, base[1] + r]) circle(r = r + hoop_t, $fn = 40);
        }
        translate([0, base[1] + r]) circle(r = r, $fn = 40);
        translate([-bundle_d * snap_open / 2, base[1] + r]) square([bundle_d * snap_open, r + hoop_t + 1]);
    }
}

module fpc_profile() {
    w = fpc_cover_w; h = fpc_cover_h; t = hoop_t;
    difference() {
        translate([-(w / 2 + t + 3), 0]) square([w + 2 * t + 6, h + t]);
        translate([-w / 2, -1]) square([w, h + 1]);
        // snap hooks: small inward lips at the feet
    }
    for (s = [-1, 1]) translate([s * (w / 2 - 0.4), 0.3]) circle(r = 0.7, $fn = 12);
}

module soft_clip(size) {
    intersection() {
        children();
        translate([0, size[1] / 2 - 1, 0]) rounded_box([size[0] + 2, size[1] + 4, clip_width], r = 1.5, r_plan = 1.5, flat_bottom = true);
    }
}

for (i = [0 : n_bundle - 1]) translate([i * 24, 0, 0])
    soft_clip([base[0], base[1] + bundle_d + 2 * hoop_t]) linear_extrude(clip_width) bundle_profile();
for (i = [0 : n_fpc - 1]) translate([i * 38, 20, 0])
    soft_clip([fpc_cover_w + 2 * hoop_t + 6, fpc_cover_h + hoop_t]) linear_extrude(clip_width) fpc_profile();
