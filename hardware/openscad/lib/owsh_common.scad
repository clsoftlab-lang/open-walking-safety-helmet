// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - shared parameters and helper modules.
// Source of truth: docs/en/00-system-design-spec.md (§1 P1/P2, §4.4, §10).
//
// Usage from a part file:   include <lib/owsh_common.scad>
// Coordinate convention (worn): +X = user's right, +Y = forward, +Z = up.
// Tested with OpenSCAD 2021.01 (CGAL). Keep $fn modest, no minkowski().

// ---------------------------------------------------------------- tolerances
clr            = 0.3;    // general fit clearance per side (tune for your printer)
eps            = 0.01;   // tiny overlap for clean booleans

// ---------------------------------------------------------------- structure
wall           = 2.4;    // default wall (= 6 x 0.4 mm lines)
ext_fillet     = 3;      // spec P2: every external edge rounded, radius >= 3 mm
max_protrusion = 30;     // spec P2: max height above the helmet shell (mm)

// ---------------------------------------------------------------- helmet
helmet_radius      = 110; // local shell radius across the head (spec 95-130). MEASURE your helmet.
helmet_radius_long = 140; // local shell radius front-to-back (usually larger). MEASURE.

// ---------------------------------------------------------------- straps (W2)
strap_slot   = [21, 3.2]; // slot for a 20 mm hook-and-loop strap: length x width
strap_tab_t  = 6;         // thickness of strap tabs (allows a 3 mm top-edge radius)
strap_tab_w  = strap_slot[1] + 2 * wall + 2;   // tab reach beyond the body
strap_tab_l  = strap_slot[0] + 2 * wall + 2;

// ---------------------------------------------------------------- fasteners (F1)
use_heat_set   = false;   // true: holes for brass heat-set inserts; false: self-tapping screws
m2_clear_d     = 2.4;
m2_tap_d       = 1.8;     // pilot for M2 self-tapping into PETG
m2_insert_d    = 3.2;     // M2 x 3 heat-set insert (OD 3.5) - verify with your inserts
m2_head_d      = 4.2;
m25_clear_d    = 2.9;
m25_tap_d      = 2.2;     // pilot for M2.5 self-tapping
m25_insert_d   = 3.6;     // M2.5 x 4 heat-set insert (OD 4.0) - verify
m25_head_d     = 5.0;
function m2_pilot_d()  = use_heat_set ? m2_insert_d  : m2_tap_d;
function m25_pilot_d() = use_heat_set ? m25_insert_d : m25_tap_d;

// ---------------------------------------------------------------- resolution
fn_hole  = 24;
fn_round = 16;
fn_big   = 64;

// ---------------------------------------------------------------- labels
label_font  = "Liberation Sans:style=Bold";
label_depth = 0.6;

// ============================================================================
// Rounded box: footprint size[0] x size[1] centred on XY origin, z = 0..size[2].
// r      : radius of the top edges (and vertical edges if r_plan undefined)
// r_plan : plan (vertical-edge) radius, >= r
// flat_bottom = true keeps a sharp bottom edge so the part sits flat on the bed
//                    (bottom faces sit on a saddle or bed, not exposed).
module rounded_box(size, r = ext_fillet, r_plan = undef, flat_bottom = true, flat_top = false) {
    rp = (r_plan == undef) ? r : max(r_plan, r);
    re = min(r, size[2] / 2 - eps);
    dx = size[0] / 2 - rp;
    dy = size[1] / 2 - rp;
    hull() for (sx = [-1, 1], sy = [-1, 1]) translate([sx * dx, sy * dy, 0]) {
        if (flat_bottom) cylinder(r = rp, h = eps, $fn = 4 * fn_round);
        else translate([0, 0, re]) _corner_puck(rp, re);
        if (flat_top) translate([0, 0, size[2] - eps]) cylinder(r = rp, h = eps, $fn = 4 * fn_round);
        else translate([0, 0, size[2] - re]) _corner_puck(rp, re);
    }
}

// torus-like rounded disc used as a hull corner (radius rp, edge radius re)
module _corner_puck(rp, re) {
    if (rp - re < 0.05) sphere(r = re, $fn = fn_round);
    else rotate_extrude($fn = 4 * fn_round)
        intersection() {
            hull() {
                translate([rp - re, 0]) circle(r = re, $fn = fn_round);
                translate([0, -re]) square([eps, 2 * re]);
            }
            translate([0, -re - 1]) square([rp + 1, 2 * re + 2]);
        }
}

// 2D rounded rectangle centred on origin
module rounded_rect2d(size, r) {
    rr = min(r, min(size[0], size[1]) / 2 - eps);
    offset(r = rr, $fn = fn_round * 2) square([size[0] - 2 * rr, size[1] - 2 * rr], center = true);
}

// 2D slot (stadium) centred: length along X
module slot2d(len, w) {
    hull() for (s = [-1, 1]) translate([s * (len - w) / 2, 0]) circle(d = w, $fn = fn_hole);
}

// ============================================================================
// Strap slot cutter: vertical through-slot, long axis along `axis` ("x" or "y")
module strap_slot_cut(h = 50, axis = "y") {
    rotate([0, 0, axis == "y" ? 90 : 0])
        translate([0, 0, -h / 2]) linear_extrude(h) slot2d(strap_slot[0] + 2 * clr, strap_slot[1] + 2 * clr);
}

// Strap tab: rounded lug attached to a body side. Origin = attachment line centre,
// tab extends toward +X by `reach`, slot long axis along Y.
module strap_tab(reach = strap_tab_w + 3, len = strap_tab_l, t = strap_tab_t) {
    difference() {
        translate([reach / 2 - 3, 0, 0])
            rounded_box([reach + 6, len, t], r = min(3, t / 2), r_plan = 5);
        translate([reach - wall - strap_slot[1] / 2 - 1, 0, t / 2]) strap_slot_cut(t * 3, "y");
    }
}

// ============================================================================
// Screw boss (vertical cylinder) with pilot hole from the top.
module screw_boss(h, d_out = 6, pilot_d = 2.2, pilot_depth = 8) {
    difference() {
        cylinder(d = d_out, h = h, $fn = fn_hole);
        translate([0, 0, h - pilot_depth]) cylinder(d = pilot_d, h = pilot_depth + 1, $fn = fn_hole);
    }
}

// Pilot hole cutter pointing -Z from origin (for bosses built into solid blocks)
module pilot_hole(d, depth) {
    translate([0, 0, -depth]) cylinder(d = d, h = depth + eps, $fn = fn_hole);
}

// ============================================================================
// Louvre vent grille cutter for a wall lying in the XZ plane (wall normal = +Y,
// outside at +Y). Slots are inclined so the OUTER opening is LOWER than the inner
// one: rain hitting the wall cannot run inward (spec: louvres face down/back).
// size = [width along X, height along Z]; wall thickness t.
module louvre_vents(size, t = wall, slot_h = 2.0, pitch = 4.0, angle = 40) {
    n = max(1, floor((size[1] - slot_h) / pitch) + 1);
    run = t / cos(angle) + 4;
    for (i = [0 : n - 1])
        translate([0, 0, -size[1] / 2 + slot_h / 2 + i * pitch])
            rotate([-angle, 0, 0])
                hull() for (s = [-1, 1])
                    translate([s * (size[0] / 2 - slot_h / 2), -run / 2, 0])
                        rotate([-90, 0, 0]) cylinder(d = slot_h, h = run, $fn = 12);
}

// Straight vent grille (rounded slots) through a plate in XY plane, thickness t
module vent_grille(size, t = wall, slot_w = 2.0, pitch = 4.0) {
    n = max(1, floor((size[1] - slot_w) / pitch) + 1);
    for (i = [0 : n - 1])
        translate([0, -size[1] / 2 + slot_w / 2 + i * pitch, -1])
            linear_extrude(t + 2) slot2d(size[0], slot_w);
}

// ============================================================================
// Cable gland slot cutter: U-shaped notch open toward -Z, through a wall in the
// XZ plane (thickness along Y). Cables enter from below (sheltered from rain).
module cable_gland_slot(w = 12, h = 6, t = wall) {
    translate([0, t / 2 + 1, 0]) rotate([90, 0, 0]) linear_extrude(t + 2)
        hull() {
            translate([-w / 2, -1]) square([w, eps]);
            for (s = [-1, 1]) translate([s * (w / 2 - min(w, h) / 2), h - min(w, h) / 2]) circle(d = min(w, h), $fn = fn_hole);
        }
}

// ============================================================================
// Helmet envelope (ellipsoid cap) whose top point sits at z = 0 and whose local
// radii at that point are R_lat (X) and R_long (Y). Used for saddles.
module helmet_local_surface(R_lat = helmet_radius, R_long = helmet_radius_long) {
    translate([0, 0, -R_lat]) scale([1, R_long / R_lat, 1]) sphere(r = R_lat, $fn = 120);
}

// Saddle block: footprint prism with a flat top at z = t_min and a concave bottom
// conforming to the helmet surface. Children = 2D footprint.
module saddle_surface(t_min = 2, R_lat = helmet_radius, R_long = helmet_radius_long, depth = 40) {
    difference() {
        translate([0, 0, -depth]) linear_extrude(depth + t_min) children();
        helmet_local_surface(R_lat, R_long);
    }
}

// sag of the helmet surface below its top at offset (x, y)
function helmet_sag(x, y, R_lat = helmet_radius, R_long = helmet_radius_long) =
    R_lat - R_lat * sqrt(max(0, 1 - pow(x / R_lat, 2) - pow(y / R_long, 2)));

// ============================================================================
// Text label solid (centre-aligned, extruded +Z by depth). Use in union() for an
// embossed label, in difference() for a debossed one. External faces use debossed
// text so no sharp raised features face outward (spec P2).
module label_text(txt, size = 5, depth = label_depth, halign = "center") {
    linear_extrude(depth) text(txt, size = size, font = label_font, halign = halign, valign = "center", $fn = 16);
}

// Two-line part label: "OWSH" + part name
module part_label(name, size = 4, depth = label_depth) {
    translate([0, size * 0.75, 0]) label_text("OWSH", size, depth);
    translate([0, -size * 0.75, 0]) label_text(name, size * 0.8, depth);
}

// Report the height of a part above the helmet shell against spec P2
module check_protrusion(name, h) {
    if (h > max_protrusion)
        echo(str("OWSH NOTE: ", name, " height above shell = ", h, " mm > ", max_protrusion, " mm (spec P2) - see README"));
    else
        echo(str("OWSH OK: ", name, " height above shell = ", h, " mm <= ", max_protrusion, " mm"));
}

// ============================================================================
// CONFORMAL HELPERS (v1.1). A module's worn frame has z = 0 at the top of its TPU saddle at
// the module centre; the shell is locally an ellipsoid cap with radii R_lat (X) and R_long (Y).
// Offset surfaces d mm above the saddle top are approximated by concentric ellipsoids.
saddle_t = 3;          // uniform TPU saddle thickness under every conformal module
conf_fn  = 128;        // facet count of the offset ellipsoids (render time vs smoothness)

function csag(x, R) = R - sqrt(max(0, R * R - x * x));            // cylinder sag
function esag(x, y, Rl, Rg) = helmet_sag(x, y, Rl, Rg);           // ellipsoid-cap sag

// solid whose top surface is the offset surface at height d
module surf_solid(d, Rl, Rg) {
    translate([0, 0, -Rl]) scale([1, (Rg + d) / (Rl + d), 1]) sphere(r = Rl + d, $fn = conf_fn);
}
// everything above / below the offset surface d (bounded box of +-300 mm)
module above_surf(d, Rl, Rg, zmax = 150) difference() {
    translate([-300, -300, -150]) cube([600, 600, 150 + zmax]);
    surf_solid(d, Rl, Rg);
}
module below_surf(d, Rl, Rg, zmin = -150) intersection() {
    surf_solid(d, Rl, Rg);
    translate([-300, -300, zmin]) cube([600, 600, 450]);
}
// half-spaces bounded by a horizontal plane
module below_plane(z) translate([-300, -300, -150]) cube([600, 600, z + 150]);
module above_plane(z) translate([-300, -300, z]) cube([600, 600, 300]);
