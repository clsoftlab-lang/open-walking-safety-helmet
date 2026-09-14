// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - button_caps (spec §10, §7.2, P8): one set of three caps,
// distinguishable by touch alone:
//   B1 front  : CIRCLE   outline, raised circular edge,   1 raised dot
//   B2 middle : TRIANGLE outline (tip points forward),    2 raised dots
//   B3 rear   : SQUARE   outline, raised square edge,     3 raised dots
// Print: PETG, socket side on the bed (as exported), no supports.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
stem_shape   = "round"; // actuator of your 12 x 12 x 7.3 switch: "round" or "square" (verify)
stem_d       = 7.0;     // round actuator diameter incl. clearance (verify with calipers)
stem_sq      = 3.6;     // square stem size incl. clearance (for switches with a square stem)
socket_depth = 2.6;
cap_h        = 5.0;     // body height
ridge_h      = 1.0;     // raised tactile edge height
dot_r        = 1.1;     // raised dots (hemispheres)
dot_pitch    = 2.8;
circle_d     = 16;
square_s     = 15;
tri_r        = 11.5;    // triangle circumradius (keeps it inside the 22 mm button pitch)

module shape2d(kind, inset = 0) {
    if (kind == "circle") circle(d = circle_d - 2 * inset, $fn = 64);
    else if (kind == "square") rounded_rect2d([square_s - 2 * inset, square_s - 2 * inset], max(0.8, 2 - inset));
    else // triangle, bounding box centred on the stem, tip toward +Y
        translate([0, -tri_r / 4, 0]) offset(r = 1) offset(delta = -1 - inset)
            rotate(90) circle(r = tri_r, $fn = 3);
}

// soft-edged solid of a 2D convex shape
module soft_extrude(kind, h, edge = 1.5) {
    hull() {
        linear_extrude(h - edge) shape2d(kind, 0);
        translate([0, 0, h - edge]) linear_extrude(edge * 0.5) shape2d(kind, edge * 0.35);
        translate([0, 0, h - eps]) linear_extrude(eps) shape2d(kind, edge);
    }
}

module tactile_ridge(kind) {
    difference() {
        hull() {
            linear_extrude(eps) shape2d(kind, 1.5);
            translate([0, 0, ridge_h]) linear_extrude(eps) shape2d(kind, 1.8);
        }
        hull() {
            translate([0, 0, -eps]) linear_extrude(eps) shape2d(kind, 2.8);
            translate([0, 0, ridge_h + eps]) linear_extrude(eps) shape2d(kind, 2.5);
        }
    }
}

module button_cap(kind, dots) {
    yc = (kind == "triangle") ? -tri_r / 4 : 0;   // dots at the triangle centroid
    difference() {
        union() {
            soft_extrude(kind, cap_h);
            translate([0, 0, cap_h - 0.2]) tactile_ridge(kind);
            for (i = [0 : dots - 1]) translate([(i - (dots - 1) / 2) * dot_pitch, yc, cap_h - 0.3])
                intersection() { sphere(r = dot_r, $fn = 16); cylinder(r = dot_r, h = dot_r); }
        }
        // stem socket
        translate([0, 0, -eps]) {
            if (stem_shape == "round") cylinder(d = stem_d, h = socket_depth, $fn = 32);
            else linear_extrude(socket_depth) square(stem_sq, center = true);
        }
    }
}

translate([-22, 0, 0]) button_cap("circle", 1);
translate([0, 0, 0])   button_cap("triangle", 2);
translate([22, 0, 0])  button_cap("square", 3);
