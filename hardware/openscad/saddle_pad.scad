// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - saddle_pad (spec §10, v1.1): thin uniform TPU 95A saddles for the
// front pod, main case and aux pod (all three on this plate). The modules' undersides already follow
// the shell, so each saddle is a flat 3 mm sheet with relief slits that lets it bend over the doubly
// curved shell. 3M Dual Lock on both faces or hook-and-loop; never glue to the shell (P1/P2).
// Print: TPU 95A, flat, 3 walls, 15 % infill (or 100 % for 3 mm), no supports.

include <lib/owsh_common.scad>
use <lib/front_pod_lib.scad>
use <lib/main_case_lib.scad>
use <lib/aux_pod_lib.scad>

slit_w   = 1.2;   // relief slit width
slit_len = 0.25;  // slit length as a fraction of the dimension it cuts into
slit_pitch = 16;

module slits(size) {
    // slits from all four edges so the sheet can take a double curvature (they never meet)
    lx = size[1] * slit_len; ly = size[0] * slit_len;
    for (x = [-size[0] / 2 + slit_pitch : slit_pitch : size[0] / 2 - slit_pitch / 2], s = [-1, 1])
        if (abs(x) < size[0] / 2 - ly - 3) translate([x, s * (size[1] / 2 - lx / 2 + 0.5), 0]) square([slit_w, lx + 1], center = true);
    for (y = [-size[1] / 2 + slit_pitch : slit_pitch : size[1] / 2 - slit_pitch / 2], s = [-1, 1])
        if (abs(y) < size[1] / 2 - lx - 3) translate([s * (size[0] / 2 - ly / 2 + 0.5), y, 0]) square([ly + 1, slit_w], center = true);
}
module sheet(size, name, outline = undef) {
    linear_extrude(saddle_t) difference() {
        if (outline == undef) rounded_rect2d(size, 5); else translate([0, -size[1] / 2]) offset(r = 2) offset(delta = -2) polygon(outline);
        slits(size);
    }
}
worn_id = 0;      // 0 = print plate; 1 / 2 / 3 = curved pod / case / aux saddle in the worn frame (assembly_preview)
part = ["plate", "worn_pod", "worn_case", "worn_aux"][worn_id];
pf = pod_footprint(); cf = case_footprint(); af = aux_footprint();
function pod_R_arc() = pf[0] * 1.04;
if (part == "plate") {
    translate([-68, 0, 0]) sheet(cf, "case");
    translate([45, 26, 0]) sheet([pod_R_arc(), pf[1]], "pod", pod_saddle_outline());
    translate([45, -30, 0]) sheet(af, "aux");
}
if (part == "worn_pod")  pod_saddle_worn();
if (part == "worn_case") case_saddle_worn();
if (part == "worn_aux")  aux_saddle_worn();
