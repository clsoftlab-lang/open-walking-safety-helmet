<!-- SPDX-License-Identifier: CERN-OHL-P-2.0 -->
<!-- Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국) -->

# Open Walking Safety Helmet — printable hardware (v1.1, conformal)

Parametric OpenSCAD models, STL files, renders and wiring for the clip-on modules of the
Open Walking Safety Helmet (OWSH). The single source of truth is
[`docs/en/00-system-design-spec.md`](../docs/en/00-system-design-spec.md) (§1, §4, §10).

> [!CAUTION]
> **The helmet's protection comes first (spec P1/P2).**
> - Use a **certified** bicycle / multisport helmet (EN 1078, CPSC 1203, AS/NZS 2063, KC or equivalent).
> - **Never 3D-print the helmet shell. Never drill, cut, glue into or melt the shell or the EPS liner.**
> - Attach modules **only** with 20 mm hook-and-loop straps through existing vents and removable
>   3M Dual Lock pads, so they **detach under impact**. Do not replace straps with screws, zip ties or glue.
> - Keep every external module low and rounded. The modules sit directly on a thin saddle that follows
>   the shell — no stilts, no gaps that can catch a branch.
> - The helmet **assists, never replaces** the white cane or guide dog.
> - A modified helmet is no longer the certified product. Never sell one as certified without testing
>   by an accredited lab.

![Assembly, front](renders/assembly_front.png)

| Rear | Side (orthographic; red camera 10° down, green forward LiDAR horizontal, blue down LiDAR 50°) |
|---|---|
| ![Assembly, rear](renders/assembly_rear.png) | ![Assembly, side](renders/assembly_side.png) |

## What changed in v1.1

- **Conformal modules.** The front pod, main case and new aux pod have undersides that follow the shell,
  so each sits on a **uniform 3 mm TPU saddle** (was: flat modules on saddles up to 34 mm thick at the corners).
- **Front pod** is a curved bar: the LiDAR bays on the flanks are rolled about their own beam axis
  (beam directions unchanged), the rain visor has a rounded camera-view notch, and the down-LiDAR facet
  is bevelled cleanly away from the camera's field of view.
- **Main case** turned front-to-back, shrunk to 99 × 63 mm, ribbed curved underside, lid capped by an
  offset of the shell. It now holds only the Pi 5 + Active Cooler, IMU and LED.
- **New aux pod** (`aux_pod_base`, `aux_pod_lid`) on the back of the head holds the ULN2003 board and the
  USB audio adapter. They could not fit inside a ~100 × 72 mm case under a 40 mm height cap: beside the
  Pi the shell drops 6–10 mm, which pushes any 15 mm-tall board over 40 mm. The aux pod is also
  closer to the headset jacks and balances the front pod. Extra part: a short (10–15 cm) USB-A
  extension from the Pi to the audio adapter.
- Assembly envelope = typical adult M/L helmet, 270 L × 210 W × 155 H mm. The measured gap between
  saddle and shell is ≤ 4 mm everywhere.

## Measured numbers (from the exported meshes)

| Module | Footprint (mm) | Max height above shell, incl. 3 mm saddle | Printed parts, est. mass* |
|---|---|---|---|
| Front pod (base + cover) | 107.6 across × 42 deep (132 incl. strap tabs) | **34.8 mm**, uniform | 34.6 cm³ → ≈ 40 g PETG |
| Main case (base + lid) | 99.1 along × 62.6 across (87.5 across incl. tabs) | **39.8 mm** (34.6 mm at the centre) | 45.9 cm³ → ≈ 52 g PETG |
| Aux pod (base + lid) | 98.6 × 37.6 (123 incl. tabs) | **23.4 mm**, uniform | 26.7 cm³ → ≈ 30 g PETG |
| Saddles (pod / case / aux) | as above, 3.0 mm thick | — | 13.6 / 19.1 / 11.5 cm³ → ≈ 13 / 18 / 11 g TPU |
| Button module + caps | 26 × 71 (96 incl. tabs) | 16.5 mm housing, ≈ 21 mm with caps | 18.9 cm³ → ≈ 22 g PETG |

\* Mass = STL volume × density (PETG 1.27 g/cm³, TPU 1.21 g/cm³) × 0.9 for PETG parts (2 mm walls are
almost solid at 4 perimeters) and × 0.8 for TPU at 3 walls / 15 % infill. Check your slicer.
Main case clearances echoed by the model: cooler → lid 1.2 mm, USB stacks 2.9 mm, header + Dupont 5.2 mm.

## Folder layout

```
hardware/
  openscad/lib/owsh_common.scad     shared parameters + helpers (rounded boxes, conformal offset surfaces,
                                    strap slots, louvres, screw bosses, cable gland slots, labels)
  openscad/lib/front_pod_lib.scad   front pod parameters, sensor layout, cross-section sweep geometry
  openscad/lib/main_case_lib.scad   main case parameters, Pi 5 layout, clearance checks
  openscad/lib/aux_pod_lib.scad     aux pod (ULN2003 + USB audio adapter)
  openscad/lib/rain_gutter_lib.scad rain flow channel (patent 112) + rear nozzle (patent 113)
  openscad/<part>.scad              one file per printable part, oriented for printing
                                    (-D worn=true exports the worn frame)
  openscad/assembly_preview.scad    all modules on the helmet envelope (not printed)
  stl/                              print-ready meshes;  stl/worn/  worn-frame meshes for the assembly
  renders/                          PNG previews + render_log.txt
  scripts/render_all.ps1 / .sh      re-export everything
  wiring/wiring_diagram.svg, pinout.md
```

## Printed parts

| File (STL) | Part | Material | Qty | Print orientation (as exported) | Supports | Infill | Est. mass |
|---|---|---|---|---|---|---|---|
| `front_pod_base` | Curved pod body: camera bay (10° down), forward LiDAR, down LiDAR facet (50°), strap tabs | PETG/ASA | 1 | worn way up | **yes, build plate only** (curved underside) | 4 walls, 25 % gyroid | 28 g |
| `front_pod_cover` | Curved top plate with rain visor + camera notch, rear wall with FPC / cable exits | PETG/ASA | 1 | top face down | yes, under the curved top | 4 walls, 25 % | 12 g |
| `main_case_base` | Pi 5 base: standoffs, IMU slot, ribbed curved underside, louvres, USB-C / USB-A openings | PETG/ASA | 1 | floor down | yes, under the ribs | 4 walls, 25 % | 40 g |
| `main_case_lid` | Lid capped by the shell offset, LED light-pipe hole, fan air pocket | PETG/ASA | 1 | top face down | yes, under the curved rim | 4 walls, 25 % | 13 g |
| `aux_pod_base` | ULN2003 cradle + USB audio adapter rails, headset-jack opening | PETG/ASA | 1 | floor down | yes, under the curved floor | 4 walls, 25 % | 22 g |
| `aux_pod_lid` | Curved lid | PETG/ASA | 1 | top face down | yes | 4 walls, 25 % | 9 g |
| `saddle_pad` | Three flat 3 mm TPU sheets with relief slits (pod, case, aux) — they bend onto the shell | TPU 95A | 3 (1 plate) | flat | none | 100 % or 3 walls/15 % | 41 g (all three) |
| `button_module` | Housing for 3 × 12 mm tactile switches, guard ridges, angled strap tabs | PETG | 1 | floor down | tiny, under the angled tabs | 4 walls, 25 % | 19 g |
| `button_caps` | ○ 1 dot · △ 2 dots · □ 3 dots, raised tactile edges | PETG | 1 set | socket side down | none | 100 % | 3 g |
| `haptic_pad` | Coin ERM pad with side slot and hook-tape recess | TPU 95A | 3 | skin membrane down | none | 3 walls, 15 % | 3 g each |
| `strap_anchor` | 20 mm strap buckle, slots 21 × 3.2 mm | PETG | 4 | flat | none | 4 walls, 25 % | 3 g each |
| `cable_clip` | 3 bundle clips + 3 FPC-cover clips | PETG | 6 | lying on the side | none | 100 % | 4 g (plate) |
| `fpc_cover` | Low flexible channel for the camera FPC, 150 mm | PETG | 1–2 | flat | none | 100 % | 7 g |
| `rain_gutter_segment` | Flow channel, front high → rear low, 3 rim clips per segment; plate R1 R2 L1 L2 | TPU 95A | 4 | upright | none | 3 walls, 15 % | 86 g (all four) |
| `rain_nozzle_rear` | Rear nozzle joining both sides, outlet backwards/downwards | TPU 95A | 1 | upright | none | 3 walls, 15 % | 9 g |

All strap slots are **21 × 3.2 mm** (20 mm hook-and-loop strap + clearance). All parts fit a 220 × 220 × 250 mm bed.

<table>
<tr><td><img src="renders/front_pod_base.png" width="260"><br>front_pod_base</td><td><img src="renders/front_pod_cover.png" width="260"><br>front_pod_cover</td><td><img src="renders/main_case_base.png" width="260"><br>main_case_base</td></tr>
<tr><td><img src="renders/main_case_lid.png" width="260"><br>main_case_lid</td><td><img src="renders/aux_pod_base.png" width="260"><br>aux_pod_base</td><td><img src="renders/aux_pod_lid.png" width="260"><br>aux_pod_lid</td></tr>
<tr><td><img src="renders/saddle_pad.png" width="260"><br>saddle_pad</td><td><img src="renders/button_module.png" width="260"><br>button_module</td><td><img src="renders/button_caps.png" width="260"><br>button_caps</td></tr>
<tr><td><img src="renders/haptic_pad.png" width="260"><br>haptic_pad</td><td><img src="renders/strap_anchor.png" width="260"><br>strap_anchor</td><td><img src="renders/cable_clip.png" width="260"><br>cable_clip</td></tr>
<tr><td><img src="renders/fpc_cover.png" width="260"><br>fpc_cover</td><td><img src="renders/rain_gutter_segment.png" width="260"><br>rain_gutter_segment</td><td><img src="renders/rain_nozzle_rear.png" width="260"><br>rain_nozzle_rear</td></tr>
</table>

## Print settings (spec §10)

- 0.2 mm layers, 4 walls, 25 % gyroid infill for rigid parts; **PETG 240 °C / bed 80 °C** (or ASA).
  Do not use PLA: it softens in summer sun and in hot cars.
- The curved undersides and curved lids need **supports from the build plate only** (tree/organic
  supports recommended; they touch only the side that faces the saddle or the shell offset).
- TPU 95A: 3 walls, 15 % infill (saddles: 100 %), slow (20–25 mm/s), no or very short retraction.
- Test your fit first: print `button_caps` and one `strap_anchor`. If parts are too tight, raise `clr`.

## Assembly hardware and post-processing

| Where | Fastener | Self-tapping (default) | Heat-set inserts (optional) |
|---|---|---|---|
| Pi 5 → case standoffs | 4 × M2.5 × 6 | pilot 2.2 mm | M2.5 × 4 insert, hole 3.6 mm |
| Lid → main case, lid → aux pod | 4 × M2.5 × 8 pan head each | pilot 2.2 mm | hole 3.6 mm |
| Camera → pod | 4 × M2 × 5 | pilot 1.8 mm | M2 × 3 insert, hole 3.2 mm |
| TF-Luna → pod | 2 × M2 × 5 each | pilot 1.8 mm | hole 3.2 mm |
| Cover → pod | 4 × M2 × 8 | pilot 1.8 mm | hole 3.2 mm |

1. Remove supports and any elephant foot from the strap slots so the strap slides freely.
2. Self-tapping: drive each screw in once, back it out, then assemble. Do not over-torque PETG.
3. Heat-set inserts: set `use_heat_set = true` in `lib/owsh_common.scad`, re-export, press inserts at ~230 °C.
4. Press the 3 mm LED into the main case lid from inside.
5. Coin motors slide into the haptic pads from the side; stick hook tape into the recess (never glue to EPS).
6. Saddles: Dual Lock on both faces (or hook-and-loop). The saddle only rests on the shell.
7. Straps: down through a strap tab slot, through a helmet vent, back up. Snug, not tight.
8. Aux pod: plug the USB audio adapter onto a 10–15 cm USB-A extension from the Pi's USB 2.0 port
   (rear opening of the main case); the ULN2003 gets GPIO17/27/22 + 5 V + GND from the header, and the
   motor leads leave through the lower notch toward the comfort pads.
9. Gutter: push the rim into the clips, slide segment 2 over segment 1's spout, and both rear spouts into the nozzle.

## Customising

Everything is a named parameter at the top of the library files (uncertain values are marked "verify").
Edit the file or override on the command line, e.g.
`openscad -D mount_pitch_deg=22 -D pod_R=120 -o stl/front_pod_base.stl openscad/front_pod_base.scad`.

| Parameter | File | Default | What to do |
|---|---|---|---|
| `pod_R` | `lib/front_pod_lib.scad` | 110 mm | Shell radius across the head under the pod. |
| `case_R_lat`, `case_R_long` | `lib/main_case_lib.scad` | 110 / 140 mm | Shell radii across / along the head under the main case. |
| `aux_R_lat`, `aux_R_long` | `lib/aux_pod_lib.scad` | 110 / 140 mm | Shell radii at the back of the head. |
| `saddle_t` | `lib/owsh_common.scad` | 3 mm | Saddle thickness (keep ≤ 4 mm). |
| `mount_pitch_deg` | `lib/front_pod_lib.scad` | 30° | Slope of the shell under the pod (phone inclinometer, head level). Sensor angles are compensated. |
| `case_max_h` | `lib/main_case_lib.scad` | 39.6 mm | Height cap of the main case above the shell. |
| `clr` | `lib/owsh_common.scad` | 0.3 mm | Fit clearance per side. |
| `use_heat_set` | `lib/owsh_common.scad` | false | Self-tapping pilots vs. insert holes. |
| `rim_t`, `seg_len`, `slope_deg`, `clip_count` | `lib/rain_gutter_lib.scad` | 22, 140, 1.2°, 3 | Rim thickness, segment length, channel slope. |
| `stem_shape`, `stem_d` | `button_caps.scad` | round, 7.0 mm | Match your tactile switches. |
| `side_R` | `button_module.scad` | 140 mm | Shell radius along the button module (angles its strap tabs). |

**How to measure a shell radius:** place a straight edge of length L across the shell, measure the gap h in
the middle; R ≈ L² / (8 h). For example, L = 100 mm and h = 11 mm gives R ≈ 114 mm.

Check these with calipers before printing: camera lens barrel and height (`cam_*`), TF-Luna holes and window
(`tfl_*`), Pi 5 cooler footprint (`pi_cooler_rect`), USB stack height, header + Dupont height, GY-521
thickness (`imu_slot_w`), ULN2003 board and audio adapter size, switch actuator Ø, coin motor Ø, rim thickness.

## Re-rendering

Requires OpenSCAD 2021.01 or newer (tested with 2021.01 / CGAL).

```powershell
powershell -ExecutionPolicy Bypass -File hardware\scripts\render_all.ps1            # everything
powershell -ExecutionPolicy Bypass -File hardware\scripts\render_all.ps1 -Parts saddle_pad,assembly_preview
```
```bash
hardware/scripts/render_all.sh                    # everything (OPENSCAD=/path/to/openscad to override)
hardware/scripts/render_all.sh front_pod_base     # one part
```

The scripts write `stl/<part>.stl`, `renders/<part>.png`, the worn-frame meshes in `stl/worn/`, three
assembly views and `renders/render_log.txt`. Measured on OpenSCAD 2021.01: parts 9 min total
(slowest: `main_case_lid` 80 s, `aux_pod_base` / `aux_pod_lid` 75 s, `front_pod_base` 65 s),
worn exports 7.3 min, assembly views 12–22 s each — about 17 min for a full run.

## Known limitations / still out of the original spec

- **Height vs. spec P2 (≤ 30 mm):** front pod 34.8 mm and main case 39.8 mm (the Pi 5 + Active Cooler
  alone needs ~31.5 mm). The aux pod (23.4 mm) and button module (≈ 21 mm) are within 30 mm.
- **Rain gutter mass:** four segments ≈ 86 g + nozzle ≈ 9 g TPU, above the 60 g budget. Shorter or
  fewer segments, or the gutter left off, bring it down.
- **Total added mass** without the gutter is ≈ 330 g (printed parts ≈ 190 g incl. saddles + electronics),
  within the 380 g budget. With the gutter it is ≈ 425 g.
- **Supports:** the conformal parts need build-plate supports on their curved faces (v1.0 parts did not).
- **Cooler clearance** under the main case lid is 1.2 mm plus a 0.8 mm pocket; watch `cpu_temp_c` in hot weather.
- The front pod's curvature radius is fixed per print (`pod_R`); a very different shell radius can leave
  gaps under the pod's ends. Measure first.

## Wiring

See [`wiring/wiring_diagram.svg`](wiring/wiring_diagram.svg) and [`wiring/pinout.md`](wiring/pinout.md).
Pin assignments are unchanged in v1.1; only the ULN2003 and USB audio adapter moved to the aux pod.

## License

CERN-OHL-P-2.0 — see [`LICENSE`](LICENSE). Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국).
