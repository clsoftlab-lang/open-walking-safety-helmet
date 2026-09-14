// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
// Open Walking Safety Helmet (OWSH) - assembly_preview (spec §10, §4.3; v1.1). NOT PRINTED.
// All modules on a helmet envelope of a typical adult M/L bicycle helmet: 270 L x 210 W x 155 H mm.
// The envelope is only a design stand-in: use a real certified helmet (P1).
// Modules are imported from hardware/stl/worn/*.stl (worn-frame exports written by the render
// scripts), so run scripts/render_all.* first. Beams: red = camera axis (10 deg down),
// green = forward LiDAR (horizontal), blue = down LiDAR (50 deg below horizontal).

use <lib/front_pod_lib.scad>
use <button_caps.scad>

W = "../stl/worn/";   // worn-frame STL folder (relative to this file)
P = "../stl/";

// ----------------------------------------------------------------- envelope
// Superellipsoid |x/a|^e + |y/b|^e + |z/c|^e = 1 (upper half). e = 2.35 gives crown radii of about
// 110-140 mm (spec §4.4: 95-130) so the conformal modules sit within 5 mm of the shell everywhere.
ha = 105; hb = 135; hc = 155; he = 2.35;
shell_t = 20;
show_helmet = true;
show_beams  = true;
show_gutter = true;

C_HELMET = [0.86, 0.86, 0.83, 0.6];
C_RIGID  = [0.18, 0.38, 0.68];
C_LID    = [0.30, 0.52, 0.82];
C_TPU    = [0.12, 0.12, 0.12];
C_BTN    = [0.95, 0.65, 0.10];
C_GUTTER = [0.10, 0.55, 0.45];

function spow(v, p) = (v < 0 ? -1 : 1) * pow(abs(v), p);
function se_z(x, y, a = ha, b = hb, c = hc) = c * pow(max(0, 1 - pow(abs(x) / a, he) - pow(abs(y) / b, he)), 1 / he);
function se_x(y, z, a = ha, b = hb, c = hc) = a * pow(max(0, 1 - pow(abs(y) / b, he) - pow(abs(z) / c, he)), 1 / he);
function e_pt(x, y) = [x, y, se_z(x, y)];
function e_n(p, a = ha, b = hb, c = hc) = let(v = [spow(p[0], he - 1) / pow(a, he), spow(p[1], he - 1) / pow(b, he), spow(p[2], he - 1) / pow(c, he)]) v / norm(v);
function unit(v) = v / norm(v);

// place a module frame: origin at point o, local X along (x projected on the tangent plane), Z along n
module frame(o, n, xdir) {
    X = unit(xdir - (xdir * n) * n); Y = cross(n, X);
    multmatrix([[X[0], Y[0], n[0], o[0]], [X[1], Y[1], n[1], o[1]], [X[2], Y[2], n[2], o[2]], [0, 0, 0, 1]]) children();
}
module on_shell(p, xdir, lift = 3) let(n = e_n(p)) frame(p + lift * n, n, xdir) children();

module superellipsoid(a, b, c, nu = 96, nv = 28) {
    pts = concat([for (k = [0 : nv - 1], j = [0 : nu - 1]) let(v = k * 90 / nv, u = j * 360 / nu)
                    [a * spow(cos(v), 2 / he) * spow(cos(u), 2 / he), b * spow(cos(v), 2 / he) * spow(sin(u), 2 / he), c * spow(sin(v), 2 / he)]],
                 [[0, 0, c]]);
    T = nv * nu;
    faces = concat([[for (j = [0 : nu - 1]) j]],
        [for (k = [0 : nv - 2], j = [0 : nu - 1]) [k * nu + j, (k + 1) * nu + j, (k + 1) * nu + (j + 1) % nu, k * nu + (j + 1) % nu]],
        [for (j = [0 : nu - 1]) [T, (nv - 1) * nu + (j + 1) % nu, (nv - 1) * nu + j]]);
    polyhedron(pts, faces);
}
module helmet() color(C_HELMET) difference() {
    superellipsoid(ha, hb, hc);
    translate([0, 0, -0.5]) superellipsoid(ha - shell_t, hb - shell_t, hc - shell_t);
    for (x = [-50, -17, 17, 50]) translate([x, 0, 0]) rotate([0, x / 3, 0]) hull() for (y = [-30, 20]) translate([0, y, 100]) cylinder(d = 10, h = 80, $fn = 16);
    for (x = [-75, 75]) translate([x, 30, 0]) rotate([0, x / 1.6, 0]) hull() for (y = [-20, 20]) translate([0, y, 70]) cylinder(d = 9, h = 80, $fn = 16);
    for (x = [-35, 35]) translate([x, -100, 0]) rotate([-50, 0, 0]) hull() for (xx = [-10, 10]) translate([xx, 0, 60]) cylinder(d = 9, h = 80, $fn = 16);
}

// ----------------------------------------------------------------- front pod (front-top)
pod_pitch = pod_mount_pitch();
function slope_at(y) = let(n = e_n(e_pt(0, y))) atan2(abs(n[1]), n[2]);
function find_slope(target, lo, hi, it = 40) = it == 0 ? (lo + hi) / 2 :
    let(mid = (lo + hi) / 2) slope_at(mid) < target ? find_slope(target, mid, hi, it - 1) : find_slope(target, lo, mid, it - 1);
pod_y = find_slope(pod_pitch, 1, hb * 0.95);
pf = pod_footprint();

module front_pod_on_helmet() on_shell(e_pt(0, pod_y), [1, 0, 0]) translate([0, -pf[1] / 2, 0]) {
    color(C_TPU) import(str(W, "saddle_pod.stl"));
    color(C_RIGID) import(str(W, "front_pod_base.stl"));
    color(C_LID) import(str(W, "front_pod_cover.stl"));
    if (show_beams) {
        sf = pod_sensor_frames();
        for (i = [0 : 2]) translate([sf[i][0], sf[i][1], sf[i][2]]) rotate([-sf[i][3], 0, 0])
            color([[1, 0, 0], [0, 0.8, 0], [0, 0.3, 1]][i]) rotate([-90, 0, 0]) cylinder(d = 1.5, h = [70, 160, 140][i], $fn = 8);
    }
}

// ----------------------------------------------------------------- main case (rear-top, long axis front-back)
case_y = -45;
module main_case_on_helmet() on_shell(e_pt(0, case_y), [1, 0, 0]) {
    color(C_TPU) import(str(W, "saddle_case.stl"));
    color(C_RIGID) import(str(W, "main_case_base.stl"));
    color(C_LID) import(str(W, "main_case_lid.stl"));
}

// ----------------------------------------------------------------- aux pod (back of the head)
aux_y = -118;
module aux_pod_on_helmet() on_shell(e_pt(0, aux_y), [1, 0, 0]) {
    color(C_TPU) import(str(W, "saddle_aux.stl"));
    color(C_RIGID) import(str(W, "aux_pod_base.stl"));
    color(C_LID) import(str(W, "aux_pod_lid.stl"));
}

// ----------------------------------------------------------------- button module (right side, above the ear)
module buttons_on_helmet() {
    p = [se_x(5, 45), 5, 45];
    n = e_n(p);
    frame(p + 1 * n, n, [0, 0, -1]) {     // module +Y stays world forward
        color(C_RIGID) import(str(P, "button_module.stl"));
        for (i = [0 : 2]) translate([0, [22, 0, -22][i], 15 + 1.3]) color(C_BTN) button_cap(["circle", "triangle", "square"][i], i + 1);
    }
}

// ----------------------------------------------------------------- haptic pads (inside, on comfort pads)
module pads_inside() {
    ia = ha - shell_t - 8; ib = hb - shell_t - 8; ic = hc - shell_t - 8;
    for (d = [[-1, 0.45, 0.30], [0, 0, 0.30], [1, 0.45, 0.30]]) {
        z = d[2] * ic;
        p = (d[0] == 0) ? [0, se_x(0, z, ib, ia, ic), z] : [d[0] * se_x(d[1] * ib, z, ia, ib, ic), d[1] * ib, z];
        n = e_n(p, ia, ib, ic);
        frame(p - 5.5 * n, n, [0, 0, 1]) color(C_TPU) import(str(P, "haptic_pad.stl"));
    }
}

// ----------------------------------------------------------------- rain gutter, bent along the rim
seg_len = 140; overlap = 12; nozzle_len = 70; clip_floor = 2; n_slices = 7;
function rim_pt(t) = [ha * spow(cos(t), 2 / he), hb * spow(sin(t), 2 / he)];
function chord_t(t0, L, lo, hi, n = 40) = n == 0 ? (lo + hi) / 2 :
    let(mid = (lo + hi) / 2) norm(rim_pt(mid) - rim_pt(t0)) < L ? chord_t(t0, L, mid, hi, n - 1) : chord_t(t0, L, lo, mid, n - 1);
function chain(t0, step, n) = n == 0 ? [t0] : concat([t0], chain(chord_t(t0, step, t0, t0 + 60), step, n - 1));
t_noz = -acos(pow((nozzle_len / 2) / ha, he / 2));
ts = chain(t_noz, seg_len / n_slices, 2 * n_slices);

module gutter_right() for (seg = [0, 1], j = [0 : n_slices - 1]) {
    // seg 1 (rear) spans chain points 0..n, seg 0 (front) spans n..2n; local x decreases toward the rear point
    base = (seg == 1) ? 0 : n_slices;
    Pr = rim_pt(ts[base + j]); Pf = rim_pt(ts[base + j + 1]);
    x1 = seg_len - j * seg_len / n_slices; x0 = x1 - seg_len / n_slices;
    d = Pr - Pf;
    translate([Pf[0], Pf[1], -clip_floor]) rotate([0, 0, atan2(d[1], d[0])])
        intersection() {
            translate([-x0, 0, 0]) import(str(W, seg == 1 ? "gutter_R2.stl" : "gutter_R1.stl"));
            translate([0, -60, -5]) cube([(x1 - x0) + (j == 0 ? overlap + 1 : 0.2), 120, 60]);
        }
}
module gutter_on_helmet() color(C_GUTTER) {
    gutter_right();
    mirror([1, 0, 0]) gutter_right();
    translate([0, rim_pt(t_noz)[1], -clip_floor]) rotate([0, 0, 180]) import(str(P, "rain_nozzle_rear.stl"));
}

// ----------------------------------------------------------------- FPC cover path (pod -> case)
module fpc_path() color(C_RIGID) {
    ys = [for (k = [0 : 8]) pod_y - 25 + (case_y + 52 - (pod_y - 25)) * k / 8];
    for (k = [0 : 7]) hull() for (y = [ys[k], ys[k + 1]]) let(q = e_pt(-20, y))
        on_shell(q, [1, 0, 0], 0) translate([0, 0, 1.5]) cube([22, 1, 3], center = true);
}

echo(str("OWSH assembly: envelope 270 x 210 x 155 mm, pod at y=", pod_y, " (slope ", slope_at(pod_y), " deg)"));
if (show_helmet) helmet();
front_pod_on_helmet();
main_case_on_helmet();
aux_pod_on_helmet();
buttons_on_helmet();
pads_inside();
if (show_gutter) gutter_on_helmet();
fpc_path();
