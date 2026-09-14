// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - main_case_lid (spec §10). Printed in PETG/ASA, oriented for printing.
// All dimensions and tolerances are parameters in lib/main_case_lib.scad and lib/owsh_common.scad
// (override from the command line, e.g. openscad -D pi_standoff_h=5 -D clr=0.4 ...).

include <lib/main_case_lib.scad>

worn = false;   // true: export in the worn frame (used by assembly_preview)
if (worn) main_case_lid(); else main_case_lid_print();
