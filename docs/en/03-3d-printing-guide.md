# 03 · 3D Printing Guide

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This guide covers printing the clip-on modules. All parts are parametric OpenSCAD models. They fit
a 220 × 220 × 250 mm FDM printer.

- OpenSCAD sources: [`hardware/openscad/`](../../hardware/openscad/)
- Ready-to-print STL files: [`hardware/stl/`](../../hardware/stl/)
- Preview images: [`hardware/renders/`](../../hardware/renders/)
- Measured sizes, masses and parameters: [`hardware/README.md`](../../hardware/README.md)
- Part list authority: [spec §10](00-system-design-spec.md#10-printable-parts-list-openscad-parametric)

> **Never 3D-print the helmet shell.** Only the add-on modules are printed. The protective helmet
> is always a certified, store-bought helmet (spec principle P1).

## Contents

1. [Parts to print](#1-parts-to-print)
2. [Measure your helmet first](#2-measure-your-helmet-first)
3. [Materials](#3-materials)
4. [Print settings and supports](#4-print-settings-and-supports)
5. [Orientation](#5-orientation)
6. [Heights and masses](#6-heights-and-masses)
7. [Post-processing and test fit](#7-post-processing-and-test-fit)
8. [Rendering STL files from OpenSCAD](#8-rendering-stl-files-from-openscad)
9. [Troubleshooting](#9-troubleshooting)

## 1. Parts to print

This table follows spec §10. STL files in `hardware/stl/` have the same base name as the `.scad` file.

| File | Part | Material | Qty | Notes |
|---|---|---|---|---|
| `front_pod_base.scad` | Front pod body with camera bay (10° down), forward LiDAR bay, down LiDAR bay (50°) | PETG/ASA | 1 | Rain lip above lenses, strap slots 21 × 3.2 mm, curved underside |
| `front_pod_cover.scad` | Rear cover with FPC and cable exit | PETG/ASA | 1 | |
| `main_case_base.scad` | Pi 5 case base with standoffs, IMU slot, vents | PETG/ASA | 1 | Openings for USB-C power, USB-A and cooler exhaust; curved, ribbed underside |
| `main_case_lid.scad` | Lid with LED light pipe hole and drip edge | PETG/ASA | 1 | |
| `aux_pod_base.scad` | Aux pod base: ULN2003 and USB audio adapter cradles | PETG/ASA | 1 | Curved underside, headset-jack opening |
| `aux_pod_lid.scad` | Aux pod lid | PETG/ASA | 1 | |
| `saddle_pad.scad` | Conformal 3 mm TPU saddles under pod, case and aux pod | TPU | 3 sheets on 1 plate | Flat sheets with relief slits that bend onto the shell |
| `button_module.scad` | Button housing for 3 × 12 mm switches | PETG | 1 | |
| `button_caps.scad` | Caps ○ △ □ with raised tactile edges | PETG | 1 set | ○ 1 dot, △ 2 dots, □ 3 dots |
| `haptic_pad.scad` | Coin-motor pad with Velcro recess | TPU | 3 | |
| `strap_anchor.scad` | 20 mm strap anchor / buckle | PETG | 4 | Slots 21 × 3.2 mm |
| `cable_clip.scad` | Cable clip for FPC cover and Dupont bundles | PETG | 6 | |
| `fpc_cover.scad` | Camera cable cover channel | PETG | 1 | |
| `rain_gutter_segment.scad` | Flow-channel segment (front high → rear low), clip-over-rim | TPU | 4 | Patent 112, optional |
| `rain_nozzle_rear.scad` | Rear nozzle collecting both sides | TPU | 1 | Patent 113, optional |
| `assembly_preview.scad` | Whole assembly on a helmet envelope (not printed) | — | — | For renders |

Notes:

- In the v1.1 hardware the ULN2003 and USB audio adapter moved from the main case to the **aux pod**
  on the back of the head. They did not fit under the main case height limit.
- The rain gutter and nozzle are **optional**. Together they weigh about 95 g, more than their 60 g budget.
  A lighter gutter is on the [roadmap](08-patent-and-roadmap.md#69-lighter-rain-gutter).
- **About `hardware/stl/worn/`:** these meshes are the parts rotated into the position they have **on the
  head**, used for the assembly preview. They are **not oriented for printing. Print only from
  `hardware/stl/`.**

**Suggested print order.** Print `button_caps` and one `strap_anchor` first. They are small and quick,
and they show whether your fit and settings work. Then measure the helmet (next section), render the
curved parts for it, and print them.

## 2. Measure your helmet first

The front pod, main case and aux pod have **curved undersides** that follow the shell. Each sits on a
uniform **3 mm TPU saddle**, with no stilts and no gap larger than 5 mm (spec P2). The curve is fixed when
you print, so **measure your helmet before printing** those parts. The design envelope is a local radius of
**95–130 mm** (spec §4.4).

### How to measure a shell radius

You need a straight ruler (or any straight edge) and calipers.

1. Put the ruler on the shell exactly where the module will sit.
2. Read the **chord length** `L` between the two points where the ruler touches the shell. For example, 100 mm.
3. Measure the **gap** `h` between the ruler's middle and the shell, straight down. For example, 11 mm.
4. Calculate: **R ≈ L² ÷ (8 × h)**. Example: 100² ÷ (8 × 11) ≈ **114 mm**.
5. Measure **across** the head (left to right) and **along** the head (front to back) at each location.
   The value along the head is usually larger.

The spec calls these two values `helmet_radius` (across) and `helmet_radius_long` (along). They exist as
shared defaults in [`hardware/openscad/lib/owsh_common.scad`](../../hardware/openscad/lib/owsh_common.scad).
**In the v1.1 models, each module has its own parameters, and those are what shape the part:**

| Parameter | File | Default | Measure |
|---|---|---|---|
| `pod_R` | `lib/front_pod_lib.scad` | 110 mm | Across the head, under the front pod |
| `mount_pitch_deg` | `lib/front_pod_lib.scad` | 30° | Slope of the shell under the pod, head level (phone inclinometer). Sensor angles are compensated. |
| `case_R_lat`, `case_R_long` | `lib/main_case_lib.scad` | 110 / 140 mm | Across / along, under the main case |
| `aux_R_lat`, `aux_R_long` | `lib/aux_pod_lib.scad` | 110 / 140 mm | Around / up the back of the head, under the aux pod |
| `side_R` | `button_module.scad` | 140 mm | Along the shell above the right ear |
| `saddle_t` | `lib/owsh_common.scad` | 3 mm | Saddle thickness (keep ≤ 4 mm) |
| `clr` | `lib/owsh_common.scad` | 0.3 mm | Fit clearance per side |

Override on the command line without editing files, for example:

```bash
openscad -D pod_R=114 -D mount_pitch_deg=25 -o hardware/stl/front_pod_base.stl hardware/openscad/front_pod_base.scad
```

Or edit the values at the top of the library file, then re-render. Re-render **both** parts of a module
(base and lid or cover) and the `saddle_pad` plate after changing a module's radii. If your radius is far
from the default, check the gap under the ends of the pod: a very different shell can leave gaps.

If a measurement is outside 95–130 mm across the head, the helmet is outside the design envelope. Choose a
rounder helmet, or check the fit very carefully and report it in an issue.

## 3. Materials

| Material | Use for | Why |
|---|---|---|
| **PETG** | Pod, case, aux pod, lids, button housing, caps, clips, strap anchors, FPC cover | Tough, slightly flexible, handles about 70–80 °C, easy to print |
| **ASA** | Same rigid parts (not anchors or caps), as an alternative | Best UV and heat resistance for daily outdoor use. Needs an enclosure and ventilation. |
| **TPU 95A** | Saddles, haptic pads, rain gutter, nozzle | Soft and grippy. Follows the helmet's curve. Comfortable against the head. Gives way under impact. |

### Why not PLA?

- **PLA softens at about 55–60 °C.** A helmet on a car seat or a sunny bench goes past that easily.
  The Pi case can warp, the camera angle can shift, and the forward LiDAR can tilt. That silently
  changes where the sensors look.
- PLA becomes brittle outdoors and can crack into sharp pieces.
- PETG, ASA and TPU cost about the same and avoid all of this.

### Colour

- **Light colours** (white, light grey, yellow) heat up less in the sun. That helps the Pi stay cool: the
  cooler has only about 1.2 mm clearance under the main case lid.
- **High-visibility yellow or orange** helps drivers and cyclists see the wearer.
- Use **matte, dark** material around the camera window if you can, to reduce reflections into the lens.

## 4. Print settings and supports

Reference settings (spec §10 and `hardware/README.md`):

| Setting | Rigid parts (PETG/ASA) | TPU parts |
|---|---|---|
| Layer height | 0.2 mm | 0.2 mm |
| Walls / perimeters | 4 | 3 |
| Infill | 25 % gyroid (button caps, clips, FPC cover: 100 %) | 15 % (saddles: 100 %) |
| Nozzle temperature | PETG 240 °C · ASA 250–260 °C | 220–235 °C |
| Bed temperature | PETG 80 °C · ASA 90–100 °C | 40–60 °C |
| Speed | normal | slow: 20–25 mm/s |
| Retraction | normal | none or very short |
| Cooling fan | PETG 30–50 % · ASA 0–20 % | 50–100 % |
| Bed adhesion | PETG: glue stick or textured PEI | Clean PEI |

### Supports

- **Curved undersides and curved lids need supports from the build plate only.** Tree or organic supports
  are recommended. They touch only the face that sits on the saddle, or the curved top that no one touches.
- This applies to `front_pod_base`, `front_pod_cover`, `main_case_base`, `main_case_lid`, `aux_pod_base`
  and `aux_pod_lid`. `button_module` needs tiny supports under its angled strap tabs.
- All other overhangs are ≤ 45°. Saddles, pads, anchors, clips, FPC cover, gutter and nozzle need no supports.
- **Keep supports out of strap slots.** Clean any support or elephant foot from the slots afterwards.

Tips:

- **TPU:** a direct-drive extruder works best. On Bowden printers, print very slowly.
- **ASA:** print in an enclosure, away from people, with ventilation. It gives off fumes.
- **Dry your filament.** Wet PETG and TPU string badly and make weak parts. 4–6 hours at 55–65 °C
  in a filament dryer is usually enough.
- Values beyond the spec are starting points. Your filament maker's recommendations come first.

## 5. Orientation

The STL files in `hardware/stl/` are **already exported in print orientation**. Import them as they are.

| Part | Orientation (as exported) | Supports |
|---|---|---|
| `front_pod_base` | worn way up | yes, build plate only (curved underside) |
| `front_pod_cover` | top face down | yes, under the curved top |
| `main_case_base` | floor down | yes, under the ribs |
| `main_case_lid` | top face down | yes, under the curved rim |
| `aux_pod_base` | floor down | yes, under the curved floor |
| `aux_pod_lid` | top face down | yes |
| `saddle_pad` | flat | none |
| `button_module` | floor down | tiny, under the angled tabs |
| `button_caps` | socket side down | none |
| `haptic_pad` | skin membrane down | none |
| `strap_anchor` | flat | none |
| `cable_clip` | lying on the side | none |
| `fpc_cover` | flat | none |
| `rain_gutter_segment` | upright | none |
| `rain_nozzle_rear` | upright | none |

Strength note: FDM parts are weakest between layers. Straps pull on strap slots and anchors, so those parts
have layers **parallel** to the strap pull. That is why anchors print flat.

## 6. Heights and masses

Spec P2 height limits above the shell: **front pod ≤ 35 mm**, **main case ≤ 40 mm** (a Pi 5 with Active
Cooler cannot fit lower), **all other modules ≤ 30 mm**. Measured from the exported meshes
(`hardware/README.md`, including the 3 mm saddle):

| Module | Footprint (mm) | Max height above shell | Printed mass (est.) |
|---|---|---|---|
| Front pod (base + cover) | 107.6 × 42 (132 incl. strap tabs) | 34.8 mm | ≈ 40 g PETG |
| Main case (base + lid) | 99.1 × 62.6 (87.5 across incl. tabs) | 39.8 mm (34.6 mm at the centre) | ≈ 52 g PETG |
| Aux pod (base + lid) | 98.6 × 37.6 (123 incl. tabs) | 23.4 mm | ≈ 30 g PETG |
| Saddles (pod / case / aux) | as above, 3.0 mm thick | — | ≈ 13 / 18 / 11 g TPU |
| Button module + caps | 26 × 71 (96 incl. tabs) | ≈ 21 mm with caps | ≈ 22 g PETG |
| Rain gutter (4 segments) + nozzle | — | — | ≈ 86 g + 9 g TPU |

Total added mass with electronics is about **330 g without the rain gutter** (budget ≤ 380 g), and about
425 g with it. Masses are estimates from mesh volume; check your slicer.

## 7. Post-processing and test fit

1. **Remove supports and brims.** Use flush cutters and a craft knife. Cut away from your hand.
2. **Clear the strap slots.** All strap slots are **21 × 3.2 mm**. A 20 mm hook-and-loop strap must slide
   through freely. Remove any support, string or elephant foot.
3. **Round every outside edge.** External edges must stay rounded (fillet ≥ 3 mm) with no sharp
   points (spec P2). Sand or file any sharp corner, burr or support scar.
4. **Screw holes.** By default the holes are pilots for self-tapping screws. Drive each screw in once, back it
   out, then assemble. Do not over-tighten PETG. For brass heat-set inserts, set `use_heat_set = true` in
   `lib/owsh_common.scad`, re-export, and press the inserts in at about 230 °C.
5. **Test-fit electronics before final assembly:**
   - Raspberry Pi 5 with Active Cooler on the standoffs in `main_case_base`, lid on. The cooler must not
     touch the lid.
   - MPU-6050 in its slot; the 3 mm LED pressed into the lid from inside.
   - ULN2003 in its cradle and the USB audio adapter on its rails in `aux_pod_base`.
   - Camera Module 3 Wide in the camera bay. The lens must sit centred behind the window.
   - Both TF-Luna sensors in their bays. **Nothing may cover the TF-Luna lens aperture**, including
     stray plastic or a rain lip that hangs too low.
   - Coin motors slid into the `haptic_pad` pockets from the side.
   - 12 mm switches in `button_module`, caps pressed on.
6. **Check the angles.** With the pod on the helmet and the head level, use a phone inclinometer to check that
   the down-LiDAR facet faces about 50° below horizontal and the camera about 10° down. Note the values for
   calibration ([04 · Assembly guide](04-assembly-guide.md#part-h--calibration)).
7. **Feel the caps.** Close your eyes and check you can tell ○ (1 dot), △ (2 dots) and □ (3 dots) apart by
   touch alone, quickly. If not, reprint the caps slower, with a smaller layer height.
8. **Do not glue printed parts to the helmet.** Parts attach with straps and Dual Lock only.

## 8. Rendering STL files from OpenSCAD

The committed STL files use the default parameters. You only need OpenSCAD if you change a parameter or
improve a part. OpenSCAD 2021.01 or newer is required.

1. Install OpenSCAD from openscad.org (Windows, macOS, Linux). On Debian/Ubuntu/Raspberry Pi OS:
   ```bash
   sudo apt-get install -y openscad
   ```
2. Render one part (from the repository root):
   ```bash
   openscad -o hardware/stl/strap_anchor.stl hardware/openscad/strap_anchor.scad
   ```
3. Render everything with the project scripts. They write `stl/<part>.stl`, `renders/<part>.png`, the worn-frame
   meshes in `stl/worn/`, three assembly views and `renders/render_log.txt`. A full run takes about 17 minutes.
   ```bash
   hardware/scripts/render_all.sh                  # everything
   hardware/scripts/render_all.sh front_pod_base   # one part
   ```
   On Windows:
   ```powershell
   powershell -ExecutionPolicy Bypass -File hardware\scripts\render_all.ps1
   ```
4. `-D worn=true` exports a part in its worn position. Those meshes are for previews only.

Component dimensions (Pi 5, Camera Module 3 Wide, TF-Luna and others) are also parameters, listed in spec §4.4
and marked "verify" in the library files. **Measure your own parts with calipers**: camera lens barrel, TF-Luna
holes and window, Pi 5 cooler footprint, USB stack and header heights, GY-521 thickness, ULN2003 board and audio
adapter size, switch actuator, coin motor and helmet rim thickness.

If you improve a part, commit both the `.scad` change and the re-rendered STL so people without CAD can print it.
See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## 9. Troubleshooting

| Problem | Try |
|---|---|
| Gap under the ends of a pod or case | Re-measure the shell radii; set `pod_R` / `case_R_*` / `aux_R_*`; re-render |
| Support scars on the curved underside | Use tree supports from the build plate only; sand lightly; the saddle hides small marks |
| PETG strings between walls | Dry the filament, lower temperature by 5 °C, increase retraction slightly |
| PETG part stuck to smooth PEI | Use glue stick as a release layer or a textured sheet next time |
| TPU jams in the extruder | Slow down, reduce or disable retraction, loosen idler tension |
| Warped ASA corners | Enclosure, brim, higher bed temperature, no drafts |
| Strap does not slide through a slot | Clear support and elephant foot; file the slot |
| Parts too tight | Raise `clr` (for example 0.4) and re-render |
| Camera or LiDAR does not fit its bay | Measure the part; adjust the dimension parameter; re-render |
| Pi screw holes do not line up | Check the 58 × 49 mm hole pitch; check scale is 100 % |
| Cooler touches the lid | Check the cooler model and the `pi_cooler_rect` parameter; never run with the lid pressing on the fan |
| Caps hard to tell apart | Print caps slower, at 0.12 mm layers, with sharper raised edges and dots |

Next: [04 · Assembly guide](04-assembly-guide.md)
