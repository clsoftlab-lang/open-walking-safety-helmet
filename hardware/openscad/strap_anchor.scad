// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - strap_anchor (spec §10): low-profile buckle for a
// 20 mm hook-and-loop strap. Sits on the shell on a removable Dual Lock pad (or loops through
// a vent) so modules can be strapped on and still break away under impact (P2). Qty 4.
// Print: PETG, flat side on the bed (as exported), no supports.

include <lib/owsh_common.scad>

// ----------------------------------------------------------------- parameters
anchor_t      = 5.0;     // thickness (top edge radius = anchor_t / 2)
bar_w         = 5.0;     // width of the bars around the slots
slot_gap      = 6.0;     // centre bar between the two strap slots
dual_lock_recess = [20, 0.4]; // shallow square recess on the underside for the Dual Lock pad

anchor_len = 2 * (strap_slot[1] + 2 * clr) + slot_gap + 2 * bar_w;
anchor_w   = strap_slot[0] + 2 * clr + 2 * bar_w;

module strap_anchor() {
    difference() {
        rounded_box([anchor_w, anchor_len, anchor_t], r = anchor_t / 2, r_plan = 5);
        for (s = [-1, 1]) translate([0, s * (slot_gap / 2 + (strap_slot[1] + 2 * clr) / 2), anchor_t / 2]) strap_slot_cut(anchor_t * 3, "x");
        translate([0, 0, -eps]) linear_extrude(dual_lock_recess[1]) square([dual_lock_recess[0], anchor_len - 2 * bar_w + 2], center = true);
    }
}

strap_anchor();
