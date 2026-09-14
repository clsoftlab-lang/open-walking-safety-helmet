#!/usr/bin/env bash
# SPDX-License-Identifier: CERN-OHL-P-2.0
# Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
# Open Walking Safety Helmet (OWSH) - export every printable part to hardware/stl/<name>.stl,
# PNG previews to hardware/renders/<name>.png and the assembly from 3 angles.
# Usage:  hardware/scripts/render_all.sh [part ...]      (OPENSCAD=/path/to/openscad to override)
set -uo pipefail

HW="$(cd "$(dirname "$0")/.." && pwd)"
SCAD="$HW/openscad"; STL="$HW/stl"; PNG="$HW/renders"
mkdir -p "$STL" "$PNG"

if [ -z "${OPENSCAD:-}" ]; then
  for c in openscad openscad.com "/c/Program Files/OpenSCAD/openscad.com" "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then OPENSCAD="$c"; break; fi
  done
fi
[ -n "${OPENSCAD:-}" ] || { echo "OpenSCAD not found - set OPENSCAD=/path/to/openscad"; exit 1; }

# part name -> preview camera (gimbal rot_x,rot_y,rot_z)
declare -A CAM=(
  [front_pod_base]="60,0,200"   [front_pod_cover]="40,0,20"   [main_case_base]="55,0,25"
  [main_case_lid]="235,0,25"    [saddle_pad]="55,0,25"         [button_module]="50,0,35"
  [button_caps]="40,0,10"       [haptic_pad]="55,0,25"         [strap_anchor]="55,0,25"
  [cable_clip]="55,0,25"        [fpc_cover]="55,0,25"          [rain_gutter_segment]="50,0,30"
  [rain_nozzle_rear]="50,0,210" [aux_pod_base]="55,0,25"     [aux_pod_lid]="235,0,25"
)
PARTS=(front_pod_base front_pod_cover main_case_base main_case_lid aux_pod_base aux_pod_lid saddle_pad button_module
       button_caps haptic_pad strap_anchor cable_clip fpc_cover rain_gutter_segment rain_nozzle_rear)
[ $# -gt 0 ] && PARTS=("$@")

LOG="$PNG/render_log.txt"; : > "$LOG"
fail=0
for p in "${PARTS[@]}"; do
  [ "$p" = "assembly_preview" ] && continue
  t0=$(date +%s)
  out=$("$OPENSCAD" -o "$STL/$p.stl" "$SCAD/$p.scad" 2>&1)
  t1=$(date +%s)
  warn=$(printf '%s\n' "$out" | grep -E "WARNING|ERROR" || true)
  size=$(stat -c %s "$STL/$p.stl" 2>/dev/null || echo 0)
  if [ "$size" -lt 1000 ]; then echo "FAIL $p: STL empty or missing"; fail=1; fi
  # PNG from the exported mesh (fast, identical geometry)
  tmp="$STL/_preview_$p.scad"
  echo "import(\"$p.stl\");" > "$tmp"
  "$OPENSCAD" -o "$PNG/$p.png" --render --imgsize=1200,900 --colorscheme=Tomorrow \
      --viewall --autocenter --camera=0,0,0,${CAM[$p]:-55,0,25},0 "$tmp" >/dev/null 2>&1
  rm -f "$tmp"
  line=$(printf '%-22s %4ss  %9s bytes' "$p" "$((t1 - t0))" "$size")
  echo "$line"; echo "$line" >> "$LOG"
  [ -n "$warn" ] && { printf '%s\n' "$warn" | sed 's/^/    /'; printf '%s\n' "$warn" | sed 's/^/    /' >> "$LOG"; }
  printf '%s\n' "$out" | grep -E "^ECHO: \"OWSH" | sed 's/^/    /' >> "$LOG"
done

if [ $# -eq 0 ] || printf '%s
' "$@" | grep -qx assembly_preview; then
  # worn-frame exports used by assembly_preview.scad
  mkdir -p "$STL/worn"
  t0=$(date +%s)
  for p in front_pod_base front_pod_cover main_case_base main_case_lid aux_pod_base aux_pod_lid; do
    "$OPENSCAD" -D worn=true -o "$STL/worn/$p.stl" "$SCAD/$p.scad" >/dev/null 2>&1
  done
  i=1; for w in pod case aux; do "$OPENSCAD" -D worn_id=$i -o "$STL/worn/saddle_$w.stl" "$SCAD/saddle_pad.scad" >/dev/null 2>&1; i=$((i+1)); done
  i=1; for g in R1 R2; do "$OPENSCAD" -D seg_id=$i -o "$STL/worn/gutter_$g.stl" "$SCAD/rain_gutter_segment.scad" >/dev/null 2>&1; i=$((i+1)); done
  line=$(printf '%-22s %4ss' "worn exports" "$(( $(date +%s) - t0 ))"); echo "$line"; echo "$line" >> "$LOG"
  for v in "front:65,0,150:p" "rear:60,0,-30:p" "side:90,0,90:o"; do
    IFS=: read -r name rot proj <<<"$v"
    t0=$(date +%s)
    "$OPENSCAD" -o "$PNG/assembly_$name.png" --preview --projection="$proj" --imgsize=1600,1200         --colorscheme=Tomorrow --viewall --autocenter --camera=0,0,0,$rot,0 "$SCAD/assembly_preview.scad" >/dev/null 2>&1
    line=$(printf '%-22s %4ss' "assembly_$name" "$(( $(date +%s) - t0 ))"); echo "$line"; echo "$line" >> "$LOG"
  done
fi
exit $fail
