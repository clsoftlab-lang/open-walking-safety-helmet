// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - rain_nozzle_rear (spec §10, patent nozzle 113): clips over
// the rear rim, receives the left and right gutter spouts and drains the water backwards and
// downwards, away from the neck. Parameters are in lib/rain_gutter_lib.scad.
// Print: TPU 95A, upright as exported, no supports (the outlet is solid down to the bed).

include <lib/rain_gutter_lib.scad>

translate([-nozzle_len / 2, 0, 0]) rain_nozzle_rear();
