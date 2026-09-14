// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - front sensor pod (v1.1, conformal): parameters, layout, geometry.
// Used by front_pod_base.scad, front_pod_cover.scad and assembly_preview.scad.
//
// Pod frame (worn, before the mounting pitch): origin = rear edge centre of the underside,
// +X right, +Y forward, +Z up; z = 0 is the top of the 3 mm TPU saddle at the centre line.
// The pod is a curved bar: every cross-section follows the shell across the head (radius
// `pod_R`), so the underside sits on a uniform thin saddle and the height above the shell is
// the same everywhere. Cross-sections are lowered along the WORLD vertical so the front face
// stays one plane that is vertical when worn.
// Contents (spec §4.3): C1 Camera Module 3 Wide (10 deg down, centre, never rolled),
// S1 TF-Luna forward (horizontal), S2 TF-Luna down-looking (50 deg). The LiDARs sit on the
// curved flanks, rolled about their OWN beam axis, so their beam directions are unchanged.

include <owsh_common.scad>

// ======================= parameters you will most likely adjust =============
mount_pitch_deg = 30;   // slope of the shell under the pod, nose-down, head level (phone inclinometer)
pod_R           = 110;  // shell radius ACROSS the head under the pod (measure; spec 95-130)
cam_tilt_deg    = 10;   // spec §4.3: camera 10 deg below horizontal
fwd_tilt_deg    = 0;    // spec §4.3: forward LiDAR horizontal
down_tilt_deg   = 50;   // spec §4.3 / §5.2 dropoff.tilt_deg

// ======================= Camera Module 3 Wide (spec §4.4) - verify with calipers
cam_pcb          = [25, 24];
cam_pcb_t        = 1.0;      // (verify)
cam_hole_pitch   = [21, 12.5];
cam_hole_top     = 2.0;
cam_lens_from_top = 9.5;
cam_lens_d       = 8.0;      // lens barrel diameter (verify)
cam_front_h      = 10.4;     // PCB front face -> lens tip (verify)
cam_block        = 8.6;      // square sensor housing (verify)
cam_block_h      = 4.5;      // (verify)
cam_back_h       = 1.5;      // back-side parts + FPC connector (verify)
cam_fpc_space    = 3.0;      // FPC exit and bend below the PCB
cam_standoff     = 1.2;
cam_lens_recess  = 0.5;
cam_hfov         = 102;      // spec §5.3
cam_vfov         = 67;       // (verify)
fov_margin       = 3;

// ======================= TF-Luna (spec §4.4) - verify with calipers =========
tfl              = [35, 21.25, 13.5];
tfl_aperture     = [24, 12];  // window in front of both lenses (verify)
tfl_hole_pitch   = 29;        // (verify)
tfl_hole_dz      = 0;         // (verify)
tfl_rear_space   = 10;        // JST-GH 6-pin cable space
tfl_beam_flare   = 2;

// ======================= housing ===========================================
pod_floor   = 1.2;
pod_top     = 1.5;    // cover thickness
pod_skin    = 1.6;    // front skin in front of a LiDAR face
bay_gap     = 3.0;
collar_t    = 1.6;
collar_len  = 6;
lip_len     = 5;      // rain visor reach beyond the front face
facet_bevel = 14;     // down-LiDAR facet bevel towards the camera (keeps the camera view clear)
cover_screw_boss_d = 4.6;
sensor_floor_gap = 0;    // sensors rest directly on the floor
sensor_top_gap   = 0.2;  // air gap under the cover
n_sections  = 16;     // cross-sections across the width (smoothness vs render time)

// ======================= derived layout (do not edit) =======================
m     = mount_pitch_deg;
t_cam = cam_tilt_deg  - m;
t_fwd = fwd_tilt_deg  - m;
t_dn  = down_tilt_deg - m;

cam_top_z = cam_lens_from_top;
cam_bot_z = cam_lens_from_top - cam_pcb[1];
cam_back  = -(cam_pcb_t + cam_back_h);

x_side = cam_pcb[0] / 2 + clr + bay_gap + tfl[0] / 2 + clr;
x_cam = 0; x_fwd = -x_side; x_dn = x_side;
r_cam = 0;
r_fwd = -asin(x_side / pod_R);   // roll about the beam axis to follow the shell
r_dn  =  asin(x_side / pod_R);
pod_W = 2 * (x_side + tfl[0] / 2 + clr) + 2 * wall;

// 3D point transform of the sensor frames: rotate([-t,0,0]) rotate([0,r,0])
function roty(p, r) = [p[0] * cos(r) + p[2] * sin(r), p[1], -p[0] * sin(r) + p[2] * cos(r)];
function rotxm(p, t) = [p[0], p[1] * cos(t) + p[2] * sin(t), -p[1] * sin(t) + p[2] * cos(t)];
function xf(p, t, r) = rotxm(roty(p, r), t);
function ps(x) = csag(x, pod_R);          // lateral sag of the shell

function box_pts(x0, x1, y0, y1, z0, z1) = [for (x = [x0, x1], y = [y0, y1], z = [z0, z1]) [x, y, z]];
cam_pts = concat(box_pts(-cam_pcb[0] / 2 - clr, cam_pcb[0] / 2 + clr, cam_back, cam_standoff, cam_bot_z - cam_fpc_space, cam_top_z + clr),
                 box_pts(-cam_lens_d / 2, cam_lens_d / 2, cam_front_h, cam_front_h, -cam_lens_d / 2, cam_lens_d / 2));
cam_rear_pts = box_pts(-cam_pcb[0] / 2, cam_pcb[0] / 2, cam_back - 5, cam_back - 5, cam_bot_z - cam_fpc_space, cam_top_z);
tfl_pts = box_pts(-tfl[0] / 2 - clr, tfl[0] / 2 + clr, -tfl[2] - clr, clr, -tfl[1] / 2 - clr, tfl[1] / 2 + clr);
tfl_rear_pts = box_pts(-tfl[0] / 2, tfl[0] / 2, -tfl[2] - tfl_rear_space, -tfl[2] - tfl_rear_space, -tfl[1] / 2, tfl[1] / 2);
// front points [x, y, z, skin]
cam_front_pts = [for (sx = [-1, 1], sz = [-1, 1]) [sx * cam_lens_d / 2, cam_front_h, sz * cam_lens_d / 2, cam_lens_recess],
                 for (sx = [-1, 1], z = [cam_top_z + 1.5, cam_bot_z - 1.5]) [sx * (cam_pcb[0] / 2 + 1.5), cam_standoff, z, 1.2]];
tfl_front_pts = [for (sx = [-1, 1], sz = [-1, 1]) [sx * (tfl[0] / 2 + 1), 0, sz * (tfl[1] / 2 + 1), pod_skin]];
tfl_front_dn  = [for (sx = [-1, 1]) [sx * (tfl[0] / 2 + 1), 0, -tfl[1] / 2 - 1, pod_skin]];  // chin facet covers the rest

// vertical placement: every corner above the local (curved) floor
function zplace(xs, pts, t, r) = max([for (p = pts) let(q = xf(p, t, r)) pod_floor + sensor_floor_gap - ps(xs + q[0]) - q[2]]);
function zspan(xs, zs, pts, t, r) = max([for (p = pts) let(q = xf(p, t, r)) zs + q[2] + ps(xs + q[0])]);
z_cam = zplace(x_cam, cam_pts, t_cam, r_cam);
z_fwd = zplace(x_fwd, tfl_pts, t_fwd, r_fwd);
z_dn  = zplace(x_dn,  tfl_pts, t_dn,  r_dn);
pod_H  = max(zspan(x_cam, z_cam, cam_pts, t_cam, r_cam), zspan(x_fwd, z_fwd, tfl_pts, t_fwd, r_fwd),
             zspan(x_dn, z_dn, tfl_pts, t_dn, r_dn)) + sensor_top_gap + pod_top;
pod_Hb = pod_H - pod_top;     // base / cover split (measured in each cross-section)

// front face (one plane): y = D - z tan(m); rear face of a section at x: y = ps(x) tan(m)
function k_of(pts, t, r, zs) = max([for (p = pts) let(q = xf([p[0], p[1], p[2]], t, r)) q[1] + (zs + q[2]) * tan(m) + p[3] / cos(m)]);
function rear_need(xs, pts, t, r, k) = max([for (p = pts) let(q = xf(p, t, r)) k - q[1] + ps(xs + q[0]) * tan(m)]);
k_cam = k_of(cam_front_pts, t_cam, r_cam, z_cam);
k_fwd = k_of(tfl_front_pts, t_fwd, r_fwd, z_fwd);
k_dn  = k_of(tfl_front_dn,  t_dn,  r_dn,  z_dn);
rear_min = wall + clr;
pod_D = max(rear_need(x_cam, cam_rear_pts, t_cam, r_cam, k_cam), rear_need(x_fwd, tfl_rear_pts, t_fwd, r_fwd, k_fwd),
            rear_need(x_dn, tfl_rear_pts, t_dn, r_dn, k_dn)) + rear_min;
function face_y(z) = pod_D - z * tan(m);
y_cam = pod_D - k_cam;
y_fwd = pod_D - k_fwd;
y_dn  = pod_D - k_dn;

// section placement: lowered by the shell sag along the world vertical
module at_x(x) translate([x, ps(x) * tan(m), -ps(x)]) children();
function sy(x) = ps(x) * tan(m);

boss_x = cam_pcb[0] / 2 + clr + bay_gap / 2;
boss_front_y = y_cam - 3;
boss_rear_x  = pod_W / 2 - wall - 2.2;
cover_screws = [[-boss_x, boss_front_y + sy(boss_x)], [boss_x, boss_front_y + sy(boss_x)],
                [-boss_rear_x, rear_min + 3.5 + sy(boss_rear_x)], [boss_rear_x, rear_min + 3.5 + sy(boss_rear_x)]];

echo(str("OWSH front pod: W=", pod_W, " D(bottom, centre)=", pod_D, " H=", pod_H, " -> height above shell = ",
         pod_H + saddle_t, " mm (uniform across the curved bar)"));
check_protrusion("front pod incl. saddle", pod_H + saddle_t);

// ======================= transforms =========================================
module at_cam() translate([x_cam, y_cam, z_cam]) rotate([-t_cam, 0, 0]) rotate([0, r_cam, 0]) children();
module at_fwd() translate([x_fwd, y_fwd, z_fwd]) rotate([-t_fwd, 0, 0]) rotate([0, r_fwd, 0]) children();
module at_dn()  translate([x_dn,  y_dn,  z_dn])  rotate([-t_dn,  0, 0]) rotate([0, r_dn, 0]) children();
module at_tfl() { at_fwd() children(); at_dn() children(); }

// ======================= cross-section sweep ================================
rp = 6;   // plan radius of the pod ends
xs_body = concat([for (a = [90, 70, 45, 20]) -(pod_W / 2 - rp) - rp * sin(a) * 0.999],
                 [for (i = [0 : n_sections]) -(pod_W / 2 - rp) + i * (pod_W - 2 * rp) / n_sections],
                 [for (a = [20, 45, 70, 90]) (pod_W / 2 - rp) + rp * sin(a) * 0.999]);
function end_inset(x) = abs(x) > pod_W / 2 - rp ? rp - sqrt(max(0, rp * rp - pow(abs(x) - (pod_W / 2 - rp), 2))) : 0;
xs_in = [for (i = [0 : n_sections]) -(pod_W / 2 - wall) + i * (pod_W - 2 * wall) / n_sections];

module yz(x) rotate([90, 0, 90]) linear_extrude(eps) children();   // 2D (y, z) at the current x

module section(kind, x) {
    e = end_inset(x); re = ext_fillet;
    at_x(x) yz(x) {
        if (kind == "outer") hull() {
            translate([e, 0]) square([pod_D - 2 * e, eps]);
            translate([e + re, pod_H - re]) circle(r = re, $fn = 16);
            translate([face_y(pod_H - re) - re - e, pod_H - re]) circle(r = re, $fn = 16);
        }
        else if (kind == "visor") hull() {
            translate([face_y(pod_H - re) + lip_len - re, pod_H - re]) circle(r = re, $fn = 16);
            translate([face_y(pod_H - re) - 4, pod_H - re]) circle(r = re, $fn = 16);
            translate([face_y(pod_H - 2 * re - 1.5) - 1, pod_H - 2 * re - 1.5]) circle(r = 0.4, $fn = 8);
        }
        else if (kind == "cavity") hull() {
            translate([-10, pod_floor]) square([face_y(pod_floor) - wall / cos(m) + 10, eps]);
            translate([-10, pod_H + 5]) square([face_y(pod_H + 5) - wall / cos(m) + 10, eps]);
        }
        else if (kind == "base_zone")  translate([-60, -40]) square([260, pod_Hb + 40]);
        else if (kind == "cover_zone") translate([-60, pod_Hb]) square([260, 60]);
        else if (kind == "facet_zone") translate([-60, 0]) square([260, pod_H - ext_fillet]);
        else if (kind == "floor_up")   translate([-60, pod_floor - eps]) square([260, 80]);
        else if (kind == "saddle")     translate([0, -saddle_t]) square([pod_D, saddle_t]);
        else if (kind == "rear_wall")  translate([clr, pod_floor + clr]) square([wall, pod_Hb - pod_floor - clr + eps]);
    }
}
module sweep(kind, xs) for (k = [0 : len(xs) - 2]) hull() { section(kind, xs[k]); section(kind, xs[k + 1]); }

// ======================= outer envelope =====================================
module pod_outer() {
    sweep("outer", xs_body);
    intersection() { dn_facet(); sweep("facet_zone", xs_body); }
    sweep("visor", [for (i = [0 : n_sections]) -(pod_W / 2 - 9) + i * (pod_W - 18) / n_sections]);
}

// facet perpendicular to the down-looking LiDAR (short window); its inner edge is bevelled
// along the camera field of view so the cut is clean
module dn_facet() {
    hx = tfl[0] / 2 + clr + wall - ext_fillet;
    hz = tfl[1] / 2 + clr + wall - ext_fillet + 1;
    difference() {
        // the inner-top corner (towards the camera) is pulled back: a smooth bevel outside the camera view
        hull() for (dy = [0, -25]) translate([0, dy, 0]) at_dn()
            for (sx = [-1, 1], sz = [-1, 1]) translate([sx * hx, pod_skin - ext_fillet - ((sx < 0 && sz > 0) ? facet_bevel : 0), sz * hz]) sphere(r = ext_fillet, $fn = 24);
        at_cam() cam_fov_keepout(1);
    }
}

// clean, rounded notch in the rain visor over the camera field of view
module visor_notch() {
    lens_y = y_cam + tf_lens_y();
    d0 = face_y(pod_H) - lens_y + 1; d1 = d0 + lip_len + 2;
    w0 = cam_lens_d / 2 + d0 * tan(cam_hfov / 2 + fov_margin) + 2;
    w1 = cam_lens_d / 2 + d1 * tan(cam_hfov / 2 + fov_margin) + 2;
    hull() for (p = [[w0, face_y(pod_H) - 2], [w1, face_y(pod_H) + lip_len + 4]], s = [-1, 1])
        translate([s * (p[0] - 3), p[1], pod_H - 2 * ext_fillet - 4]) cylinder(r = 3, h = 20, $fn = 24);
}
function tf_lens_y() = xf([0, cam_front_h, 0], t_cam, r_cam)[1];

module pod_cavity() sweep("cavity", xs_in);

// ======================= sensor clearance / apertures ======================
module cam_envelope() {
    translate([-cam_pcb[0] / 2 - clr, cam_back - 3, cam_bot_z - cam_fpc_space]) cube([cam_pcb[0] + 2 * clr, 3 - cam_back + eps, cam_pcb[1] + cam_fpc_space + clr]);
    translate([-cam_pcb[0] / 2 - clr, -eps, cam_bot_z - clr]) cube([cam_pcb[0] + 2 * clr, cam_standoff + eps, cam_pcb[1] + 2 * clr]);
}
module cam_fov_keepout(extra = 0) {
    L = 45;
    hx = tan(cam_hfov / 2 + fov_margin + extra); hz = tan(cam_vfov / 2 + fov_margin + extra);
    y0 = cam_front_h - cam_lens_recess;
    hull() {
        translate([0, y0, 0]) cube([cam_lens_d + 2 * clr, eps, cam_lens_d + 2 * clr], center = true);
        translate([0, y0 + L, 0]) cube([cam_lens_d + 2 * L * hx, eps, cam_lens_d + 2 * L * hz], center = true);
    }
}
module cam_optics_cut() {
    translate([-cam_block / 2 - clr, -eps, -cam_block / 2 - clr]) cube([cam_block + 2 * clr, cam_block_h + 2 * eps, cam_block + 2 * clr]);
    rotate([-90, 0, 0]) cylinder(d = cam_lens_d + 2 * clr, h = cam_front_h + 1, $fn = 32);
    cam_fov_keepout(0);
}
module cam_holes() {
    for (sx = [-1, 1], z = [cam_top_z - cam_hole_top, cam_top_z - cam_hole_top - cam_hole_pitch[1]])
        translate([sx * cam_hole_pitch[0] / 2, cam_standoff - 1, z]) rotate([-90, 0, 0]) cylinder(d = m2_pilot_d(), h = 7, $fn = fn_hole);
}
module tfl_envelope() {
    translate([-tfl[0] / 2 - clr, -tfl[2] - clr, -tfl[1] / 2 - clr]) cube([tfl[0] + 2 * clr, tfl[2] + 2 * clr, tfl[1] + 2 * clr]);
}
module tfl_aperture_cut() {
    L = 60; g = L * tan(tfl_beam_flare);
    hull() {
        translate([0, -eps, 0]) cube([tfl_aperture[0] + 2 * clr, eps, tfl_aperture[1] + 2 * clr], center = true);
        translate([0, L, 0]) cube([tfl_aperture[0] + 2 * clr + 2 * g, eps, tfl_aperture[1] + 2 * clr + 2 * g], center = true);
    }
}
module tfl_holes() {
    for (sx = [-1, 1]) translate([sx * tfl_hole_pitch / 2, -1, tfl_hole_dz]) rotate([-90, 0, 0]) cylinder(d = m2_pilot_d(), h = 7, $fn = fn_hole);
}
module optical_clearance() {
    at_cam() cam_optics_cut();
    at_tfl() tfl_aperture_cut();
    visor_notch();
}
// sensor bodies extended horizontally to the rear (cable space)
module sensor_voids() {
    hull() { at_cam() cam_envelope(); translate([0, -60, 0]) at_cam() cam_envelope(); }
    hull() { at_fwd() tfl_envelope(); translate([0, -60, 0]) at_fwd() tfl_envelope(); }
    hull() { at_dn() tfl_envelope(); translate([0, -60, 0]) at_dn() tfl_envelope(); }
}

// ======================= internal structure =================================
module pod_mounts() {
    // camera: mount plate + standoff bosses
    at_cam() {
        translate([-cam_pcb[0] / 2 - 2, cam_standoff, cam_bot_z - 2]) cube([cam_pcb[0] + 4, 14, cam_pcb[1] + 4]);
        for (sx = [-1, 1], z = [cam_top_z - cam_hole_top, cam_top_z - cam_hole_top - cam_hole_pitch[1]])
            translate([sx * cam_hole_pitch[0] / 2, -eps, z]) rotate([-90, 0, 0]) cylinder(d = 4.2, h = cam_standoff + 2 * eps, $fn = fn_hole);
    }
    // TF-Luna: front frame around the window + cradle rails (sides and bottom)
    at_tfl() {
        translate([-tfl[0] / 2 - 3, 0, -tfl[1] / 2 - 3]) cube([tfl[0] + 6, 8, tfl[1] + 6]);
        translate([-tfl[0] / 2 - clr - collar_t, -collar_len, -tfl[1] / 2 - clr - collar_t]) cube([tfl[0] + 2 * (clr + collar_t), collar_len + eps, tfl[1] * 0.75]);
    }
    // cover screw bosses (vertical) + ties to the side walls
    for (p = cover_screws) translate([p[0], p[1], -30]) cylinder(d = cover_screw_boss_d, h = 90, $fn = fn_hole);
    for (sx = [-1, 1]) translate([sx * (pod_W / 2 - wall - 1.5), cover_screws[2][1], 0]) cube([3.2, 3, 90], center = true);
}

// ======================= base =================================================
module front_pod_base() {
    difference() {
        union() {
            intersection() {
                pod_outer();
                sweep("base_zone", xs_body);
                union() {
                    difference() { pod_outer(); pod_cavity(); }
                    intersection() { pod_cavity(); sweep("floor_up", xs_body); pod_mounts(); }
                }
            }
            // strap tabs, rolled to the shell at the ends
            for (sx = [-1, 1]) let(x = sx * (pod_W / 2 - 1))
                translate([x, pod_D / 2 + sy(x), -ps(x)]) rotate([0, sx * asin((pod_W / 2) / pod_R), 0])
                    mirror([sx < 0 ? 1 : 0, 0, 0]) strap_tab();
            // embossed label on the floor behind the camera
            intersection() {
                translate([0, 7, pod_floor - 1.2]) part_label("FRONT POD", 3.2, 1.8);
                pod_cavity();
            }
        }
        sensor_voids();
        optical_clearance();
        at_cam() cam_holes();
        at_tfl() tfl_holes();
        for (p = cover_screws) translate([p[0], p[1], pod_Hb - ps(p[0]) + eps]) pilot_hole(m2_pilot_d(), 7);
        // drain holes at the front (the pod is pitched nose-down)
        for (sx = [-1, 1]) let(x = sx * boss_x) translate([x, boss_front_y + sy(x) + cover_screw_boss_d / 2 + 2.5, -5]) cylinder(d = 2.5, h = 10, $fn = 16);
    }
}

// ======================= cover (curved top plate + rear wall) ===============
fpc_slot  = [18, 3];
wire_slot = [14, 8];

module front_pod_cover() {
    difference() {
        union() {
            intersection() { pod_outer(); sweep("cover_zone", xs_body); }
            sweep("rear_wall", [for (i = [0 : n_sections]) -(pod_W / 2 - wall - clr) + i * (pod_W - 2 * (wall + clr)) / n_sections]);
        }
        optical_clearance();
        for (p = cover_screws) translate([p[0], p[1], pod_Hb - ps(p[0]) - 1]) cylinder(d = m2_clear_d, h = 20, $fn = fn_hole);
        // cable exits in the rear wall, open toward the floor (sheltered)
        for (c = [[0, fpc_slot[0], fpc_slot[1] + 1], [-x_side, wire_slot[0], wire_slot[1]], [x_side, wire_slot[0], wire_slot[1]]])
            translate([c[0], clr + sy(c[0]), pod_floor + clr - ps(c[0]) - 1]) cable_gland_slot(c[1], c[2] + 1, wall * 4);
        // debossed label on the rear wall
        translate([0, clr - 0.2, pod_floor + 13]) rotate([90, 0, 0]) translate([0, 0, -label_depth - 0.2]) label_text("OWSH", 4, label_depth + 0.2);
    }
}

// print orientations (both need supports only under the curved underside / curved top)
module front_pod_base_print()  front_pod_base();
module front_pod_cover_print() translate([0, 0, pod_H]) rotate([180, 0, 0]) front_pod_cover();

function pod_footprint() = [pod_W, pod_D];
function pod_height() = pod_H;
function pod_mount_pitch() = m;
function pod_radius() = pod_R;
function pod_sensor_frames() = [[x_cam, y_cam, z_cam, t_cam, r_cam], [x_fwd, y_fwd, z_fwd, t_fwd, r_fwd], [x_dn, y_dn, z_dn, t_dn, r_dn]];
function pod_cam_lens_h() = cam_front_h;

// TPU saddle in the worn frame (for the assembly) and its flat development (for printing)
module pod_saddle_worn() sweep("saddle", xs_body);
function pod_saddle_outline(n = 24) = let(sw = pod_R * 2 * asin(pod_W / 2 / pod_R) * PI / 180)
    concat([for (i = [0 : n]) let(x = -pod_W / 2 + i * pod_W / n) [pod_R * asin(x / pod_R) * PI / 180, sy(x)]],
           [for (i = [n : -1 : 0]) let(x = -pod_W / 2 + i * pod_W / n) [pod_R * asin(x / pod_R) * PI / 180, sy(x) + pod_D]]);
