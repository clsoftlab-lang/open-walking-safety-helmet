# SPDX-License-Identifier: CERN-OHL-P-2.0
# Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
# Open Walking Safety Helmet (OWSH) - export every printable part to hardware\stl\<name>.stl,
# PNG previews to hardware\renders\<name>.png and the assembly from 3 angles.
# Usage:  powershell -ExecutionPolicy Bypass -File hardware\scripts\render_all.ps1 [-Parts a,b] [-OpenScad path]
param(
    [string[]]$Parts = @(),
    [string]$OpenScad = ""
)
$ErrorActionPreference = "Continue"

$HW   = Split-Path -Parent $PSScriptRoot
$Scad = Join-Path $HW "openscad"
$Stl  = Join-Path $HW "stl"
$Png  = Join-Path $HW "renders"
New-Item -ItemType Directory -Force -Path $Stl, $Png | Out-Null

if (-not $OpenScad) {
    $candidates = @("$env:ProgramFiles\OpenSCAD\openscad.com", "$env:ProgramFiles\OpenSCAD\openscad.exe",
                    "${env:ProgramFiles(x86)}\OpenSCAD\openscad.com")
    $cmd = Get-Command openscad -ErrorAction SilentlyContinue
    if ($cmd) { $candidates = @($cmd.Source) + $candidates }
    $OpenScad = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $OpenScad) { Write-Error "OpenSCAD not found - pass -OpenScad <path>"; exit 1 }

$Cam = @{
    front_pod_base = "60,0,200"; front_pod_cover = "40,0,20"; main_case_base = "55,0,25"
    main_case_lid = "235,0,25"; saddle_pad = "55,0,25"; button_module = "50,0,35"
    button_caps = "40,0,10"; haptic_pad = "55,0,25"; strap_anchor = "55,0,25"
    cable_clip = "55,0,25"; fpc_cover = "55,0,25"; rain_gutter_segment = "50,0,30"
    rain_nozzle_rear = "50,0,210"; aux_pod_base = "55,0,25"; aux_pod_lid = "235,0,25"
}
$All = @("front_pod_base","front_pod_cover","main_case_base","main_case_lid","aux_pod_base","aux_pod_lid","saddle_pad","button_module",
         "button_caps","haptic_pad","strap_anchor","cable_clip","fpc_cover","rain_gutter_segment","rain_nozzle_rear")
$doAssembly = ($Parts.Count -eq 0) -or ($Parts -contains "assembly_preview")
if ($Parts.Count -eq 0) { $Parts = $All }

$Log = Join-Path $Png "render_log.txt"
Set-Content -Path $Log -Value "" -Encoding UTF8
$fail = 0

function Invoke-OpenScad([string[]]$ArgList) {
    # OpenSCAD writes progress to stderr; capture everything as text
    $out = & $OpenScad @ArgList 2>&1 | ForEach-Object { "$_" }
    return ($out -join "`n")
}

foreach ($p in $Parts) {
    if ($p -eq "assembly_preview") { continue }
    $stlFile = Join-Path $Stl "$p.stl"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $out = Invoke-OpenScad @("-o", $stlFile, (Join-Path $Scad "$p.scad"))
    $sw.Stop()
    $size = if (Test-Path $stlFile) { (Get-Item $stlFile).Length } else { 0 }
    if ($size -lt 1000) { Write-Host "FAIL ${p}: STL empty or missing" -ForegroundColor Red; $fail = 1 }

    $tmp = Join-Path $Stl "_preview_$p.scad"
    Set-Content -Path $tmp -Value "import(`"$p.stl`");" -Encoding ASCII
    $camArg = if ($Cam.ContainsKey($p)) { $Cam[$p] } else { "55,0,25" }
    Invoke-OpenScad @("-o", (Join-Path $Png "$p.png"), "--render", "--imgsize=1200,900", "--colorscheme=Tomorrow",
                      "--viewall", "--autocenter", "--camera=0,0,0,$camArg,0", $tmp) | Out-Null
    Remove-Item $tmp -ErrorAction SilentlyContinue

    $line = "{0,-22} {1,5:N0}s {2,10} bytes" -f $p, $sw.Elapsed.TotalSeconds, $size
    Write-Host $line; Add-Content -Path $Log -Value $line
    ($out -split "`n") | Where-Object { $_ -match "WARNING|ERROR" } | ForEach-Object {
        Write-Host "    $_" -ForegroundColor Yellow; Add-Content -Path $Log -Value "    $_" }
    ($out -split "`n") | Where-Object { $_ -match '^ECHO: "OWSH' } | ForEach-Object { Add-Content -Path $Log -Value "    $_" }
}

if ($doAssembly) {
    # worn-frame exports used by assembly_preview.scad
    $Worn = Join-Path $Stl "worn"
    New-Item -ItemType Directory -Force -Path $Worn | Out-Null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    foreach ($p in @("front_pod_base","front_pod_cover","main_case_base","main_case_lid","aux_pod_base","aux_pod_lid")) {
        Invoke-OpenScad @("-D", "worn=true", "-o", (Join-Path $Worn "$p.stl"), (Join-Path $Scad "$p.scad")) | Out-Null
    }
    $i = 1
    foreach ($w in @("pod","case","aux")) {
        Invoke-OpenScad @("-D", "worn_id=$i", "-o", (Join-Path $Worn "saddle_$w.stl"), (Join-Path $Scad "saddle_pad.scad")) | Out-Null; $i++
    }
    $i = 1
    foreach ($g in @("R1","R2")) {
        Invoke-OpenScad @("-D", "seg_id=$i", "-o", (Join-Path $Worn "gutter_$g.stl"), (Join-Path $Scad "rain_gutter_segment.scad")) | Out-Null; $i++
    }
    $sw.Stop()
    $line = "{0,-22} {1,5:N0}s" -f "worn exports", $sw.Elapsed.TotalSeconds
    Write-Host $line; Add-Content -Path $Log -Value $line
    $views = @(@("front", "65,0,150", "p"), @("rear", "60,0,-30", "p"), @("side", "90,0,90", "o"))
    foreach ($v in $views) {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        Invoke-OpenScad @("-o", (Join-Path $Png "assembly_$($v[0]).png"), "--preview", "--projection=$($v[2])",
                          "--imgsize=1600,1200", "--colorscheme=Tomorrow", "--viewall", "--autocenter",
                          "--camera=0,0,0,$($v[1]),0", (Join-Path $Scad "assembly_preview.scad")) | Out-Null
        $sw.Stop()
        $line = "{0,-22} {1,5:N0}s" -f "assembly_$($v[0])", $sw.Elapsed.TotalSeconds
        Write-Host $line; Add-Content -Path $Log -Value $line
    }
}
exit $fail
