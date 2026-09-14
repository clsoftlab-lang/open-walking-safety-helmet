// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - front_pod_cover (spec §10). Printed in PETG/ASA, oriented for printing.
// All dimensions and tolerances are parameters in lib/front_pod_lib.scad and lib/owsh_common.scad
// (override from the command line, e.g. openscad -D mount_pitch_deg=25 -D clr=0.4 ...).

include <lib/front_pod_lib.scad>

worn = false;   // true: export in the worn frame (used by assembly_preview)
if (worn) front_pod_cover(); else front_pod_cover_print();
