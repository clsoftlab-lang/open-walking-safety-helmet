// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - aux_pod_lid (v1.1, new part). PETG/ASA. Holds D1 ULN2003 + A1 USB
// audio adapter on the back of the head. Parameters are in lib/aux_pod_lib.scad and lib/owsh_common.scad.
// Print as exported; enable supports from the build plate (only the curved underside / top needs them).

include <lib/aux_pod_lib.scad>

worn = false;   // true: export in the worn frame (used by assembly_preview)
if (worn) aux_pod_lid(); else aux_pod_lid_print();
