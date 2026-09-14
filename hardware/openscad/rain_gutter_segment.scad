// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - rain_gutter_segment (spec §10, patent flow channel 112):
// TPU flow-channel segments that clip over the lower shell rim and slope from the front (high)
// to the rear (low). Qty 4 = 2 per side; this plate holds all four (R1, R2, L1, L2).
// Segment 1 is the front one (closed front end), segment 2 slides over its spout and feeds the
// rear nozzle. Parameters (rim thickness, length, slope ...) are in lib/rain_gutter_lib.scad.
// Print: TPU 95A, upright as exported (U-clip and channel open upward), no supports.
// The gutter is optional and must never be glued to the shell (P1).

include <lib/rain_gutter_lib.scad>

seg_id = 0;       // 0 = plate, 1 = R1, 2 = R2, 3 = L1, 4 = L2 (numeric so it is easy to pass with -D)
part = ["plate", "R1", "R2", "L1", "L2"][seg_id];
span = rim_t + clip_wall + lip_y1 + 4;   // one segment's width across the plate + gap

module seg(side, i) { if (side == "L") mirror([0, 1, 0]) rain_gutter_segment(i); else rain_gutter_segment(i); }

if (part == "plate") {
    // right parts extend further toward -Y, mirrored left parts toward +Y
    translate([-seg_len / 2, 82 - lip_y1, 0]) {
        translate([0, 0, 0]) seg("R", 0);
        translate([0, -span, 0]) seg("R", 1);
        translate([0, -2 * span - (rim_t + clip_wall - lip_y1) - 4, 0]) seg("L", 0);
        translate([0, -3 * span - (rim_t + clip_wall - lip_y1) - 4, 0]) seg("L", 1);
    }
} else seg(part[0], (part[1] == "1") ? 0 : 1);

echo(str("OWSH gutter: drop per segment = ", seg_drop, " mm, front floor = ", floor_front(0), " mm, rear floor = ", floor_rear(seg_count - 1), " mm"));
