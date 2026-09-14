// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - passive rain flow channel (patent KR 10-2560496,
// flow-channel module 112 + nozzle 113; spec §2, §4.3, §10). TPU 95A, no power.
//
// Segment frame: +X along the rim from FRONT (x = 0, high) to REAR (x = seg_len, low),
// +Y outward (away from the head), +Z up. The helmet rim sits in the U clip at y < 0; rain
// running down the shell drops over the clip's outer wall into the channel and flows rearward.
// Left-side segments are mirror images (mirror([0,1,0])).

include <owsh_common.scad>

// ----------------------------------------------------------------- helmet rim (verify!)
rim_t          = 22;    // thickness of the shell + EPS edge at the rim (measure with calipers)
clip_depth     = 10;    // how far the clip walls reach up over the rim
clip_wall      = 2.0;
clip_floor     = 2.0;
clip_grip      = 0.8;   // inward bump on the inner wall for a snap grip (TPU flexes)

// ----------------------------------------------------------------- channel
seg_len        = 140;   // segment length along the rim (fits a 220 mm bed)
seg_count      = 2;     // segments per side (front-to-rear chain)
slope_deg      = 1.2;   // channel slope, front high -> rear low (added to the rim's own slope)
channel_w      = 9;     // water channel width
channel_depth  = 6;     // lip height above the channel floor
lip_t          = 3;     // outer lip thickness (fully rounded top)
base_floor     = 6;     // floor height at the rear end of the last segment (z above rim bottom)
overlap        = 12;    // spout / socket overlap between segments
spout_t        = 1.2;

seg_drop = seg_len * tan(slope_deg);
function floor_front(i) = base_floor + (seg_count - i) * seg_drop;
function floor_rear(i)  = base_floor + (seg_count - 1 - i) * seg_drop;
ch_y0 = clip_wall;                 // channel inner side (shell side)
ch_y1 = clip_wall + channel_w;     // channel outer side
lip_y1 = ch_y1 + lip_t;

// 2D helper in the (y, z) plane, extruded along X
module yz_extrude(len) rotate([90, 0, 90]) linear_extrude(len) children();

// U clip that receives the rim edge. The outer wall is continuous (it is the channel's shell-side
// wall); the floor and inner wall are only present at `clip_count` short clips to save mass.
clip_count = 3;     // number of rim clips per segment
clip_len   = 16;    // length of each clip along the rim
module rim_clip(len, n = clip_count) {
    yz_extrude(len) {
        square([clip_wall, clip_floor + clip_depth]);
        translate([0, clip_floor + clip_depth]) square([0.8, 2.5]);    // thin flexible wiper
    }
    step = (n > 1) ? (len - 10 - clip_len) / (n - 1) : 0;
    for (k = [0 : n - 1]) translate([(n > 1) ? 5 + k * step : (len - clip_len) / 2, 0, 0]) yz_extrude(clip_len) {
        translate([-rim_t - clip_wall, 0]) square([rim_t + 2 * clip_wall, clip_floor]);                // floor under the rim
        translate([-rim_t - clip_wall, 0]) square([clip_wall, clip_floor + clip_depth - 1]);           // inner wall
        translate([-rim_t - clip_wall + clip_wall / 2, clip_floor + clip_depth - 1]) circle(d = clip_wall, $fn = 16);
        translate([-rim_t, clip_floor + clip_depth * 0.6]) circle(r = clip_grip, $fn = 12);            // snap bump
    }
}

// 45-degree relief groove under the channel floor (open to the bed, prints without supports)
module floor_relief(x0, x1, fmin) {
    gw = min(channel_w - 1, 2 * (fmin - 1.6));
    if (gw > 2) hull() {
        translate([x0, (ch_y0 + ch_y1) / 2 - gw / 2, -1]) cube([x1 - x0, gw, 1]);
        translate([x0, (ch_y0 + ch_y1) / 2 - eps, -1]) cube([x1 - x0, 2 * eps, gw / 2 + 1]);
    }
}

// convex channel body between x0 (floor f0) and x1 (floor f1)
module channel_body(x0, x1, f0, f1) {
    hull() for (p = [[x0, f0], [x1, f1]]) translate([p[0], 0, 0]) yz_extrude(eps) {
        square([lip_y1 - ext_fillet, eps]);
        translate([0, 0]) square([ch_y1, p[1] - 0.01 + eps]);
        translate([lip_y1 - ext_fillet, ext_fillet]) circle(r = ext_fillet, $fn = 24);
        translate([ch_y1 + lip_t / 2, p[1] + channel_depth - lip_t / 2]) circle(d = lip_t, $fn = 16);
        square([ch_y1, p[1]]);
    }
}
module channel_cavity(x0, x1, f0, f1, extra_w = 0) {
    hull() for (p = [[x0, f0], [x1, f1]]) translate([p[0], 0, 0]) yz_extrude(eps)
        translate([ch_y0 - extra_w, p[1]]) square([channel_w + 2 * extra_w, channel_depth + 20]);
}

// spout that slides into the next segment's socket (or into the nozzle)
module spout(x0, f) {
    w = channel_w - 2 * clr;
    difference() {
        hull() for (x = [x0 - eps, x0 + overlap]) translate([x, 0, 0]) yz_extrude(eps)
            translate([ch_y0 + clr, f - spout_t]) square([w, spout_t + 3]);
        hull() for (x = [x0 - 1, x0 + overlap + 1]) translate([x, 0, 0]) yz_extrude(eps)
            translate([ch_y0 + clr + spout_t, f]) square([w - 2 * spout_t, 10]);
    }
}

module rain_gutter_segment(i = 0) {
    f0 = floor_front(i); f1 = floor_rear(i);
    difference() {
        union() {
            rim_clip(seg_len);
            channel_body(0, seg_len, f0, f1);
        }
        channel_cavity(i == 0 ? 2.5 : 0, seg_len + 1, f0, f1 - (1 / seg_len) * seg_drop);
        floor_relief(overlap + 4, seg_len - 2, f1 - 0.2);
        // socket at the front end for the previous segment's spout
        if (i > 0) channel_cavity(-1, overlap + clr, f0 - spout_t - clr, f0 - spout_t - clr - (overlap / seg_len) * seg_drop, 0);
        // label on the lip outside
        translate([seg_len / 2, lip_y1 + 0.2, 6.5]) rotate([90, 0, 0]) mirror([1, 0, 0]) translate([0, 0, 0])
            label_text(str("OWSH GUTTER ", i + 1), 3, 0.8);
    }
    spout(seg_len, f1);
}

// ----------------------------------------------------------------- rear nozzle (113)
nozzle_len    = 70;     // along the rear rim
nozzle_drop   = 3.0;    // floor drop from each inlet to the centre
outlet_len    = 14;     // outlet reach outward (backwards on the helmet)
outlet_w      = 8;
outlet_drop   = 2.0;    // extra fall along the outlet (drains backwards AND downwards)

// Nozzle frame: +X along the rear rim (user's left -> right), +Y outward = backwards, +Z up.
// Both rear segment spouts enter the sockets at x = 0 and x = nozzle_len.
module rain_nozzle_rear() {
    fe = base_floor;                  // inlet floor (= rear floor of the last segment)
    fc = fe - nozzle_drop;            // centre floor
    xm = nozzle_len / 2;
    fo = fc - outlet_drop;            // outlet tip floor
    difference() {
        union() {
            rim_clip(nozzle_len, 2);
            channel_body(0, xm, fe, fc);
            channel_body(xm, nozzle_len, fc, fe);
            // outlet block, solid down to the bed so it prints without supports
            hull() {
                translate([xm - outlet_w / 2 - 2.4, ch_y0, 0]) cube([outlet_w + 4.8, channel_w, fc + channel_depth - 1]);
                translate([xm, lip_y1 + outlet_len - ext_fillet, 0]) cylinder(r = ext_fillet + 1, h = fo + 2, $fn = 24);
            }
        }
        // sockets for the incoming spouts
        channel_cavity(-1, overlap + clr, fe - spout_t - clr, fe - spout_t - clr, 0);
        translate([nozzle_len, 0, 0]) mirror([1, 0, 0]) channel_cavity(-1, overlap + clr, fe - spout_t - clr, fe - spout_t - clr, 0);
        // collecting channel sloping to the centre
        channel_cavity(overlap - 1, xm, fe - (overlap / xm) * nozzle_drop, fc);
        channel_cavity(xm, nozzle_len - overlap + 1, fc, fe - (overlap / xm) * nozzle_drop);
        // outlet channel: from the centre outward and downward, open on top
        hull() {
            translate([xm - outlet_w / 2, ch_y0 + 1, fc]) cube([outlet_w, eps, 30]);
            translate([xm - outlet_w / 2 + 1, lip_y1 + outlet_len + 1, fo]) cube([outlet_w - 2, eps, 30]);
        }
        translate([16, lip_y1 + 0.2, 5.2]) rotate([90, 0, 0]) mirror([1, 0, 0]) label_text("OWSH", 3, 0.8);
    }
}

function gutter_seg_len() = seg_len;
function gutter_nozzle_len() = nozzle_len;
function gutter_clip_floor() = clip_floor;
