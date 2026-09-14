# Open Walking Safety Helmet — System Design Specification (v1.0)

> **Status:** Reference design v1.0 · **This document is the single source of truth.**
> Firmware, 3D models, the phone app and all guides MUST follow the pin map, dimensions,
> haptic language and protocol defined here. Change this file first, then the implementations.

- Patent: KR 10-2560496 "Walking safety helmet capable of recognizing surroundings"
  (application 10-2021-0101227, filed 2021-08-02, registered 2023-07-24)
- Patent holder / inventor / project lead: **CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국 박사)**
- The patent holder releases this design free of charge for everyone. See `PATENT_PLEDGE.md`.
- Motto: *Until the day blind people everywhere can walk like anyone else.*
  (전 세계 시각장애인이 일반인처럼 다닐 수 있는 그날까지)

### Global project rules
- Default language of code, specs and issues: **English**. Every user-facing guide also in **Korean**.
- Voice/UI strings: `en` and `ko` are maintained by the core team. Additional languages
  (`es`, `fr`, `pt`, `ar`, `hi`, `zh-CN`, `ja`, `sw`, …) are welcome but a language is only marked
  **"verified"** after review by a native speaker who is blind or an O&M instructor — safety phrases
  must be unambiguous. Unverified languages are shipped with a first-boot notice.
- Emergency numbers are per-country settings, never hard-coded to one country.
- Units: metric by default, imperial selectable for voice.

---

## 1. Mission and design principles

**Mission:** let blind and low-vision people anywhere in the world walk as freely and safely
as sighted people, using parts anyone can buy and print.

**Why a helmet and not glasses:** a helmet protects the head if a collision or fall happens
anyway. The helmet's protective function is therefore **non-negotiable**:

| # | Principle | Consequence |
|---|---|---|
| P1 | **Never degrade impact protection** | Use a certified bicycle/multisport helmet (EN 1078, CPSC 1203, AS/NZS 2063, KC or equivalent). Never 3D-print the shell. Never drill, cut, glue into or melt the EPS liner or the shell. |
| P2 | **Breakaway, low-profile add-ons** | External modules attach with hook-and-loop straps through vents and/or removable adhesive pads so they detach under impact. Max height above the shell: **35 mm for the front pod, 40 mm for the main case** (a Pi 5 with Active Cooler cannot fit lower), **30 mm for all other modules**. Undersides are curved to the shell with a uniform 3 mm TPU saddle — no stilts or gaps > 5 mm. All external edges rounded (fillet ≥ 3 mm), no sharp points. |
| P3 | **Assist, never replace** | The helmet complements the white cane or guide dog. Docs and first-boot voice message say so. |
| P4 | **Silence must never mean "safe" when broken** | Every subsystem is watched. A failure produces a distinct FAULT pattern (§5.7, §6.2). |
| P5 | **Safety path independent of AI** | The LiDAR reflex path (§5.1) runs without the camera or neural networks. |
| P6 | **Offline first** | All hazard warnings are computed on the helmet. The phone/internet is only for location, SOS and optional services. |
| P7 | **Buildable worldwide** | Only globally available parts (AliExpress, DigiKey, Mouser, Pimoroni, local Raspberry Pi resellers). No soldering in the reference build (Dupont/JST connectors). Parts printable on a 220×220×250 mm FDM printer. |
| P8 | **Accessible by default** | Tactile buttons with distinct shapes, voice prompts in the user's language (ko, en first), screen-reader friendly phone app. |
| P9 | **Permissive licences** | Only Apache-2.0 / MIT / BSD models and libraries in the default build (no AGPL). |

---

## 2. Patent feature mapping

| Patent element (paragraph) | v1.0 implementation | Status |
|---|---|---|
| Case 110 — helmet | Certified helmet + printed clip-on modules | v1.0 |
| Camera 120 / image module 121 — hazard recognition, approaching objects [0033] | Camera Module 3 Wide + NanoDet-Plus detector + tracker + time-to-contact | v1.0 |
| Stairs / cliff on walking path [0033] | Down-looking LiDAR drop-off detector (§5.2) | v1.0 |
| Character recognition 122 — signs [0035–0036] | Button-triggered OCR (RapidOCR, optional package) | v1.0 (optional install) |
| Elevator buttons + hand guidance [0037] | OCR of button labels + hand tracking | Roadmap v1.2 |
| Face recognition 123 — acquaintance / person to avoid, with mask [0038–0040] | YuNet + SFace, local enrolment database, "friend" / "avoid" tags | v1.0 |
| Accessible facility recognition [0034] | Custom-trained detector (tactile paving, ramps, crossings) | Roadmap v1.3 (needs dataset) |
| Rain / fog removal [0033] | Lightweight dehaze pre-filter (CLAHE-based) | v1.0 basic, learned model roadmap |
| Four cameras or 360° camera [0032] | One front wide camera; rear camera expansion port | v1.0 front, rear roadmap |
| Vibration unit 130 — side-specific, intensity/pattern, count pulses [0041–0044] | 3 coin ERM motors (L / C / R), haptic language §6 | v1.0 |
| Speaker unit 140 — voice by signal type [0045–0049] | USB audio → open-ear / bone-conduction headset, priority speech queue | v1.0 |
| Position sensor 150, dangerous-area warning [0051] | Phone GPS via BLE; optional helmet GPS (UART) | v1.0 phone, helmet GPS optional |
| Navigation 160 [0054–0056] | Destination beacon + integration with existing accessible navigation apps | Roadmap v1.1 |
| Communication 170 + emergency report 112/119 [0057–0059] | BLE link to phone app; SOS by long-press or fall detection; app offers one-tap call/SMS with location | v1.0 (user confirms call — web platform limit) |
| Microphone 180, voice call [0060–0061] | Headset mic via phone Bluetooth audio | v1.0 via phone |
| Fan, removable rechargeable battery [0028–0029] | USB-C power bank in pocket/waist bag with breakaway cable; passive vents | v1.0 |
| Air-curtain module 111 [0062–0064] | Concept + experimental module docs only (power/noise) | Experimental |
| Flow-channel module 112 + nozzle 113 [0065–0068] | Printed TPU rain gutter segments + rear nozzle (passive, no power) | v1.0 optional print |

---

## 3. System architecture

```
                 ┌──────────────────────────── HELMET ────────────────────────────┐
                 │                                                                │
 Camera Module 3 ─┤► vision thread: capture → dehaze → detector → tracker → TTC ──┐│
 Wide (CSI)       │                          └► faces (on demand / low rate)      ││
                  │                          └► OCR (button-triggered)            ││
 TF-Luna FWD ─I2C─┤► reflex thread 50 Hz: head-height obstacle zones ────────────┤│
 TF-Luna DOWN ─I2C┤► reflex thread 50 Hz: drop-off / step detector ──────────────┤│
 MPU-6050 ────I2C─┤► imu thread 100 Hz: fall detection ──────────────────────────┤│
 3 buttons ──GPIO─┤► input thread: short / long / double press ──────────────────┤│
                  │                                                              ▼│
                  │                              EVENT BUS ──► hazard arbiter ─────┤
                  │                                               │                │
                  │           ┌───────────────────────────────────┼──────────┐     │
                  │           ▼                                   ▼          ▼     │
                  │   haptics (ULN2003 → 3 ERM)          audio (USB headset)  BLE link
                  │                                                              │ │
                  │  watchdog: heartbeats of every thread → FAULT events         │ │
                  └──────────────────────────────────────────────────────────────┼─┘
                                                                                 │ Nordic UART Service
                                                                   PHONE APP (PWA, Web Bluetooth)
                                                                   location · SOS · settings · log
```

Runtime: Raspberry Pi OS Bookworm 64-bit, Python ≥ 3.11, single process, one thread per
subsystem, thread-safe event bus. Runs as a systemd service with automatic restart.

---

## 4. Hardware reference design

### 4.1 Bill of materials (reference build)

| Ref | Part | Qty | Notes / global search keyword |
|---|---|---|---|
| H1 | Certified bicycle/multisport helmet with vents | 1 | EN 1078 / CPSC / KC mark. Size to user. Prefer rounded shell without visor. |
| U1 | Raspberry Pi 5, 4 GB (8 GB recommended) | 1 | Alternative: Raspberry Pi 4 4 GB (lower frame rate) |
| U2 | Raspberry Pi Active Cooler (official) | 1 | Required on Pi 5 |
| U3 | microSD 32 GB A2 (or NVMe via M.2 HAT) | 1 | |
| C1 | Raspberry Pi Camera Module 3 **Wide** (IMX708, 120°) | 1 | |
| C2 | Pi 5 camera cable 22-pin→15-pin, 300 mm | 1 | "Raspberry Pi 5 camera cable 300mm" |
| S1 | Benewake **TF-Luna** LiDAR (I2C mode) — forward | 1 | 0.2–8 m, 2° FOV |
| S2 | Benewake **TF-Luna** LiDAR (I2C mode) — down-looking | 1 | |
| S3 | MPU-6050 (GY-521) IMU | 1 | Fall detection |
| M1–M3 | Coin ERM vibration motor 10 × 2.7 mm, 3 V, with leads (type 1027) | 3 | Left / Center / Right |
| D1 | ULN2003 driver board (from 28BYJ-48 kit) | 1 | Drives the 3 motors |
| B1–B3 | 12 × 12 mm tactile button modules (3-pin) or bare 12 mm tactile switches + Dupont | 3 | Caps are printed with distinct shapes |
| L1 | 3 mm LED + 330 Ω (or LED module) | 1 | Status for sighted helpers |
| A1 | USB audio adapter with a real microphone input (not "line in") | 1 | Pi 5 has no 3.5 mm jack. Match the headset plug: a 4-pole (TRRS, CTIA) combo jack, or separate headphone + mic jacks plus a TRRS→2×TRS splitter |
| A2 | Open-ear / bone-conduction wired headset with mic | 1 | Must not block ambient sound |
| P1 | USB-C power bank, PD, ≥ 5 V 3 A output, 10 000–20 000 mAh | 1 | Carried in pocket / waist bag |
| P2 | USB-C cable 1.5 m + magnetic breakaway USB-C adapter rated 3 A | 1 | Breakaway prevents neck snagging |
| W4 | USB-A male → female extension cable, 10–15 cm | 1 | Pi 5 USB 2.0 port → audio adapter in the aux pod |
| W1 | Dupont jumper wires F-F 20 cm (40-pack), **6-pin** 1.25 mm leads for TF-Luna (pin 5 is needed for I2C mode) | 1 set | |
| W3 | Dupont 1-to-N female splitter cables (or 2×8 female header splitter) for shared SDA, SCL, 5 V, 3.3 V and GND lines | 1 set | 3 I2C devices and several 5 V loads share header pins. **Not** a Qwiic/STEMMA QT hub: those are 3.3 V-only with 1 mm JST-SH plugs, while TF-Luna needs 5 V |
| W2 | 20 mm hook-and-loop straps (200 mm), 3M Dual Lock / VHB pads | 1 set | |
| F1 | M2.5 × 6 screws + 5 mm standoffs (Pi), M2 × 5 screws (camera, TF-Luna) | 1 set | |
| G1 | Optional: u-blox NEO-M8N GPS (UART) | 0–1 | Phone-free location |
| R1 | Optional: TPU filament for rain gutter and haptic pads | — | |

Printed parts: PETG or ASA for rigid parts (PLA softens in summer sun / hot cars); TPU 95A for
haptic pads, saddles and rain gutter. Strap anchors are PETG.

### 4.2 Raspberry Pi 5 pin map (BCM numbering) — **authoritative**

| Function | BCM GPIO | Header pin | Direction | Notes |
|---|---|---|---|---|
| I2C1 SDA | GPIO2 | 3 | bus | TF-Luna FWD 0x10, TF-Luna DOWN 0x11, MPU-6050 0x68 |
| I2C1 SCL | GPIO3 | 5 | bus | 400 kHz (`dtparam=i2c_arm=on,i2c_arm_baudrate=400000`) |
| Haptic LEFT | GPIO17 | 11 | out | → ULN2003 IN1 → M1 |
| Haptic CENTER | GPIO27 | 13 | out | → ULN2003 IN2 → M2 |
| Haptic RIGHT | GPIO22 | 15 | out | → ULN2003 IN3 → M3 |
| Button B1 (circle) | GPIO5 | 29 | in, pull-up | active-low |
| Button B2 (triangle) | GPIO6 | 31 | in, pull-up | active-low |
| Button B3 (square) | GPIO26 | 37 | in, pull-up | active-low |
| Status LED | GPIO16 | 36 | out | via 330 Ω |
| GPS TX→Pi RX (optional) | GPIO15 | 10 | in | UART0, 9600 baud |
| GPS RX←Pi TX (optional) | GPIO14 | 8 | out | |
| 5 V | — | 2, 4 | power | ULN2003 +, TF-Luna ×2 (5 V). **Never power button modules from 5 V** (5 V on a GPIO damages the Pi) |
| 3.3 V | — | 1, 17 | power | MPU-6050, button modules (**3.3 V required**; modules must be active-low, otherwise set `buttons.active_high: true` — an unconfigured active-high module reads as permanently pressed) |
| GND | — | 6, 9, 14, 20, 25, 30, 34, 39 | | Common ground |

- **TF-Luna I2C mode:** connector pin 5 (configuration) tied to GND selects I2C. TF-Luna logic is
  3.3 V-compatible; power at 5 V. The down-looking unit's address is changed once from 0x10 to 0x11
  with `python -m owsh.tools.tfluna_addr --from 0x10 --to 0x11`.
- **ERM motors on ULN2003:** motor + to ULN2003 board "+" (5 V) and motor − to OUT1..OUT3.
  The ULN2003 Darlington drop (~1 V) gives ≈ 4 V; firmware caps PWM duty at 75 % (`haptics.max_duty`)
  so 3 V motors are not overdriven.
- **Camera:** CAM/DISP 0 connector on Pi 5.
- **Audio:** USB audio adapter in any USB 2.0 port (keep USB 3 ports free to reduce 2.4 GHz noise near BLE).
- **Power budget:** Pi 5 loaded ≈ 6.5 W, peripherals ≈ 1.5 W → ≈ 8 W. A 3 A supply limits USB
  peripherals to 600 mA which is sufficient. 10 000 mAh ≈ 3.5 h, 20 000 mAh ≈ 7 h (conservative).

### 4.3 Mechanical layout and mass budget

| Module | Location on helmet | Contents | Attachment | Mass budget |
|---|---|---|---|---|
| Front sensor pod | Front-top, centred, above forehead | C1 camera facing forward tilted 10° down, S1 LiDAR forward horizontal, S2 LiDAR tilted down 50° from horizontal | 2 × 20 mm straps (slot 21 × 3.2 mm) through front vents + Dual Lock on a 3 mm TPU saddle | ≤ 60 g (printed ≈ 40 g); curved bar 108 × 42 mm; height ≤ 35 mm |
| Main case | Top, behind the crown, long axis front-to-back | U1 + U2, S3 IMU, L1 LED window | 2 × 20 mm straps through vents + Dual Lock on a 3 mm TPU saddle | ≤ 150 g incl. Pi (printed ≈ 52 g); 99 × 63 mm; height ≤ 40 mm |
| Aux pod | Back of the head, below the main case | D1 ULN2003 driver, A1 USB audio adapter (via W4 extension) | Straps + Dual Lock on 3 mm TPU saddle | ≤ 70 g (printed ≈ 30 g); 99 × 38 mm; height ≤ 30 mm |
| Button module | Right side, above ear, lower rim | B1 front, B2 middle, B3 rear | Strap anchor + Dual Lock | ≤ 25 g; height ≈ 21 mm |
| Haptic pads ×3 | Inside, on comfort pads: left temple, forehead centre, right temple | M1, M2, M3 | Hook-and-loop to helmet comfort padding (do not glue to EPS) | ≤ 15 g total |
| Rain gutter (optional) | Along lower shell rim, sloping front → rear nozzle | TPU segments | Clips over rim + straps | ≤ 60 g |
| Cables | Along shell under straps | camera FPC in printed cover, Dupont bundles | Cable clips | ≤ 30 g |

Total added mass ≤ 380 g without the rain gutter (estimated ≈ 330 g; the optional gutter adds ≈ 95 g — lighter gutter is a roadmap item). Battery is not on the helmet. Keep the centre of mass near the helmet
centre: front pod and main case balance each other.

### 4.4 Key component dimensions (verify with calipers — all are OpenSCAD parameters)

| Component | Dimensions | Mounting |
|---|---|---|
| Raspberry Pi 5 | PCB 85 × 56 × 1.6 mm; height incl. Active Cooler ≈ 22 mm above PCB bottom | 4 × M2.5 holes, 3.5 mm from edges, pitch 58 × 49 mm |
| Camera Module 3 Wide | PCB 25 × 24 mm, depth ≈ 12.4 mm incl. lens | 4 × M2 holes, pitch 21 × 12.5 mm, top holes 2 mm below top edge; lens centre 9.5 mm below top edge |
| TF-Luna | 35 × 21.25 × 13.5 mm, 5 g | cradle + 2 × M2 holes (verify), clear aperture: never cover lens |
| MPU-6050 GY-521 | 21 × 16 × 3 mm | 2 × 3 mm holes |
| ULN2003 board | 35 × 32 × 15 mm | 4 × 3 mm holes (varies) — cradle design |
| USB audio adapter | ≈ 50 × 18 × 10 mm | cradle |
| Coin ERM 1027 | Ø 10 × 2.7 mm | pocket in TPU pad |
| Tactile switch 12 × 12 | 12 × 12 × 7.3 mm (plus cap stem) | pocket |
| Helmet shell (design envelope) | local radius 95–130 mm, vents ≥ 20 × 8 mm | TPU saddles conform to curvature |

---

## 5. Sensing and hazard logic

### 5.1 Reflex path — forward LiDAR (head-height obstacles)

Head-height obstacles (branches, truck mirrors, signs, open windows) are what a cane misses.
Loop 50 Hz, median of last 3 samples. Invalid reading (strength < 100 or distance = 0)
counts as "no return".

| Zone | Distance | Haptic (CENTER motor) | Voice |
|---|---|---|---|
| Z3 notice | 2.0 m ≥ d > 1.2 m | 2 Hz short pulses, 40 % | none |
| Z2 warning | 1.2 m ≥ d > 0.6 m | 5 Hz pulses, 70 % | "Obstacle ahead" once per 5 s |
| Z1 imminent | d ≤ 0.6 m | continuous 100 % | "Stop" (preempts) |

Hysteresis 0.1 m between zones. Zone thresholds are config values.
Near-range dropout: the TF-Luna returns nothing below 0.2 m. If the reading was in Z1 and becomes
no-return, Z1 is **held for 0.5 s** instead of going silent.

### 5.2 Reflex path — down-looking LiDAR (drop-off and steps)

Tilt θ = 50° below horizontal (config `dropoff.tilt_deg`). While walking on level ground the
expected distance d₀ is learned as a rolling median over 3 s of samples whose variance is low
(auto-calibration, clamped to 1.2–3.5 m). **Safety rule:** d₀ is never automatically increased while
longer distances are measured (standing still at a platform edge must not teach the track bed as ground);
a shorter stable ground distance is re-learned after 10 s (e.g. sitting down, slope).

- **DROP (stairs down, curb, platform edge):** d > d₀ × 1.30 **or** no-return, sustained ≥ 120 ms
  → P1 IMMINENT, all motors double long pulse, voice "Step down ahead" / "Drop ahead".
- **STEP UP / low obstacle:** d < d₀ × 0.70 sustained ≥ 120 ms → P2 WARNING, center motor
  3 short pulses, voice "Step up ahead".
- Cooldown 3 s per type. No-return on very dark / wet surfaces is reported as DROP because a missed
  drop is worse than a false alarm; users can lower sensitivity (`dropoff.no_return_is_drop: false`).

### 5.3 Vision path

- Capture 1280 × 720 → resize for detector. Target ≥ 8 FPS on Pi 5.
- Pre-filter: optional CLAHE on luminance for fog/rain/low light (`vision.dehaze: auto|on|off`).
- Detector: **NanoDet-Plus-m 416** (OpenCV Zoo `object_detection_nanodet_2022nov.onnx`,
  Apache-2.0) via `cv2.dnn`. Any compatible ONNX can be configured.
- Classes of interest (COCO): person, bicycle, car, motorcycle, bus, truck, dog, horse,
  bench, fire hydrant, stop sign, parking meter, traffic light, chair, potted plant, suitcase.
  "Movers" = person, bicycle, car, motorcycle, bus, truck, dog, horse.
- Tracker: IoU-greedy tracker, track kept 0.7 s without detections.
- Direction: horizontal angle from bbox centre using camera HFOV (Camera Module 3 Wide: 102°).
  LEFT < −15° ≤ CENTER ≤ +15° < RIGHT.
- Time-to-contact: TTC = Δt / (s − 1), s = bbox-height ratio over ≥ 0.4 s window (smoothed).
- Alerts:
  - **APPROACH P1:** mover with TTC < 1.5 s and bbox height > 20 % of frame.
  - **APPROACH P2:** mover with TTC < 3.0 s (vehicles: < 4.0 s) and bbox height > 10 % of frame.
  - The condition must hold on **2 consecutive processed frames** (suppresses bounding-box jitter).
- Per-track cooldown 5 s for the same level; escalation to a higher level bypasses cooldown.
- Detector input colour order is configurable (`color_order: rgb|bgr`, default rgb as in the OpenCV Zoo demo).
- **Describe scene (button):** up to 5 objects sorted by closeness (bbox height), grouped by
  class and direction: "2 people ahead, bicycle on the right".

### 5.4 Faces

- YuNet 2023mar detector + SFace 2021dec recogniser (OpenCV Zoo, MIT / Apache-2.0).
- Runs at ≤ 2 Hz on the most recent frame when persons are detected.
- Enrolment DB: `data/faces/<name>/{*.jpg}` + `data/faces/index.json` with `tag: friend|avoid`.
  Enrol with `python -m owsh.tools.enroll_face --name "Mina" --tag friend --camera 0` (or images).
- Match: cosine similarity ≥ 0.363 (SFace recommended threshold). Mask handling: accept
  partial faces if YuNet confidence ≥ 0.6; lower similarity threshold is configurable.
- friend → P3 INFO "Mina is ahead on the left", 2 short pulses on that side, cooldown 60 s per person.
- avoid → P2 WARNING with voice, cooldown 60 s.
- Privacy: embeddings and photos never leave the helmet; not sent over BLE except the name.

### 5.5 OCR (button-triggered)

- Backend `rapidocr_onnxruntime` (Apache-2.0) when installed, languages from config; otherwise
  voice "Text reading is not installed".
- Reads the centre 70 % crop of a fresh frame, orders lines top→bottom, speaks up to 200 characters.
  Long-press B1 repeats the last spoken message.
- Signs containing danger keywords (config list per language, e.g. "위험", "공사", "DANGER",
  "CAUTION", "WET FLOOR") are prefixed with "Warning sign:".

### 5.6 Fall detection (IMU)

- Free-fall |a| < 0.35 g for ≥ 80 ms followed by impact |a| > 2.5 g within 1 s, then
  low motion (|a| within 1 ± 0.15 g) for 2 s → FALL → SOS countdown (§7.3).

### 5.7 Watchdog

Each thread publishes a heartbeat. Timeouts: camera frames 2 s, LiDAR 0.5 s, IMU 1 s, audio
backend init failure immediate.

**Camera blocked / blind camera:** frames still arrive but the lens is covered (mud, rain film,
sticker, cap) or it is pitch dark. If mean luminance < 12 (0–255) **and** luminance std-dev < 6
for ≥ 3 s, **or** ≥ 97 % of pixels are darker than 12 for ≥ 3 s (privacy-shutter frames with a small
icon), raise FAULT `camera_blocked` (voice: "Camera is covered or too dark"). Also raise it
when the Laplacian variance (sharpness) stays < 5 for ≥ 5 s (smeared lens). The LiDAR reflex
path keeps working and the voice says so ("Distance sensors still active").

**Power and temperature (Pi):** poll the firmware `get_throttled` flags every 5 s. Under-voltage
(bit 0) continuously for ≥ 10 s → P2 "Power is low. Charge the battery soon." (at most once per
5 min). CPU ≥ 80 °C → P2 "Helmet is overheating." (at most once per 5 min, re-armed below 75 °C). Failure → FAULT event (component id). FAULT repeats every 10 s (P0) while active **for safety-relevant components** (camera, LiDARs,
haptics, IMU). Non-safety components (faces, OCR, BLE, config) are announced once at P2. Recovery → voice "<component> recovered".

---

## 6. Haptic language (motors L = left temple, C = forehead, R = right temple)

### 6.1 Priorities

| Level | Name | Examples | Preempts |
|---|---|---|---|
| P0 | CRITICAL | SOS countdown, system FAULT | everything |
| P1 | IMMINENT | Z1 obstacle, DROP, APPROACH P1 | P2–P4 |
| P2 | WARNING | Z2 obstacle, STEP UP, APPROACH P2, avoid-person | P3–P4 |
| P3 | INFO | Z3 notice, friend face, OCR result, scene description | P4 |
| P4 | STATUS | ready, button tick, mute toggled | — |

The haptic mixer renders every active pattern per motor and takes the **maximum** intensity per
motor at each 10 ms tick (continuous reflex patterns and one-shot patterns coexist). Audio uses
strict preemption (§7.1).

### 6.2 Pattern table (authoritative)

| Pattern id | Motors | Timing | Meaning |
|---|---|---|---|
| `tick` | C | 40 ms @ 60 % | Button acknowledged / "I'm alive" |
| `zone3` | C | repeat: 60 ms on / 440 ms off @ 40 % | Obstacle 1.2–2.0 m |
| `zone2` | C | repeat: 80 ms on / 120 ms off @ 70 % | Obstacle 0.6–1.2 m |
| `zone1` | C | continuous @ 100 % | Obstacle ≤ 0.6 m |
| `drop` | L+C+R | 2 × (400 ms on / 150 ms off) @ 100 % | Drop-off / stairs down |
| `step_up` | C | 3 × (100 ms on / 100 ms off) @ 80 % | Step up / low obstacle |
| `approach_left` / `approach_right` / `approach_center` | L / R / C | 3 × (150 ms on / 80 ms off) @ 100 % (P1) or 70 % (P2) | Moving object approaching from that side |
| `person_friend_<side>` | side | 2 × (80 ms on / 120 ms off) @ 60 % | Enrolled friend |
| `person_avoid_<side>` | side | 4 × (60 ms on / 60 ms off) @ 90 % | Enrolled person to avoid |
| `turn_left` / `turn_right` | L / R | 250 ms on / 750 ms off, repeat while active @ 70 % | Steering cue (navigation, roadmap) |
| `count_n` | C | n × (120 ms on / 280 ms off) @ 70 %, n ≤ 10 | Number (e.g. floor) [0044] |
| `sos_countdown` | L+C+R | 1 Hz 200 ms @ 100 % for 10 s | SOS will be sent |
| `fault` | C | 3 × (50 ms on / 50 ms off) @ 100 %, every 10 s | A subsystem failed — do not trust silence |
| `ready` | L → C → R | 100 ms each, sequential @ 60 % | Boot complete |

---

## 7. Audio, buttons, SOS

### 7.1 Speech

- Backends in order: `piper` CLI (if configured, natural voices), `espeak-ng` (Pi default, supports ko/en),
  `pyttsx3` (desktop development). Pre-rendered clips cached as WAV under `data/cache/tts/` for fixed phrases.
- Queue: a higher-priority message interrupts the current one; same or lower priority waits;
  queued P1/P2 messages older than 2 s are dropped; at most 3 queued items.
- Mute (B3 double press) silences P3–P4 speech only. P0–P2 are always spoken. **Answers to a button
  request (read text, describe, status, where am I, who is here) are spoken even when muted.**
- All phrases live in `owsh/i18n/<lang>.json` keyed by message id; `{placeholders}` allowed.

### 7.2 Buttons (B1 front ○ circle, B2 middle △ triangle, B3 rear □ square)

| Button | Short press (< 0.8 s) | Long press (≥ 1.5 s) | Double press (< 0.4 s gap) |
|---|---|---|---|
| B1 ○ | Read text (OCR) | Repeat last message | — |
| B2 △ | Describe scene | Where am I (location from phone) | Who is here (faces) |
| B3 □ | Status report | Hold 3 s: SOS countdown | Toggle voice mute (P3–P4) |

Timing: presses between 0.8 s and the long threshold are ignored. B3's long press is 3 s and fires
while still held. Every accepted press gives `tick` immediately. During SOS countdown any button cancels.

**Safe shutdown:** hold **B1 ○ + B3 □ together for 5 s** (press both within about 1 s) → voice
"Shutting down" + `ready` pattern reversed (R→C→L) → power off after 3 s. While both are held, the
B3 SOS long press and B1 long press are suppressed; releasing either early aborts.

### 7.3 SOS

1. Trigger: B3 hold 3 s, or FALL.
2. Countdown 10 s: `sos_countdown` + voice "Emergency alert in 10 seconds. Press any button to cancel."
3. If not cancelled: send `sos` over BLE (repeat every 5 s until phone acks), voice "Sending emergency alert";
   "Emergency alert sent" is spoken only after the phone's `ack`.
4. Phone app: loud alarm + vibration, shows location, big buttons "Call emergency number"
   (per-country setting: 112 / 119 / 911 …) and "Send SMS to guardians" (prefilled with map link).
   The web platform requires the user (or a bystander) to confirm the call/SMS; a native app can automate it (roadmap).
5. If no phone is connected: voice "Phone not connected" every 10 s and `sos_countdown` pattern continues
   for 60 s so bystanders notice (LED blinks fast). Any button press cancels.

---

## 8. Helmet ↔ phone protocol (BLE, Nordic UART Service)

- Service `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`
- RX (phone → helmet, write / write-without-response) `6E400002-B5A3-F393-E0A9-E50E24DCCA9E`
- TX (helmet → phone, notify) `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`
- Device name: `OWSH-XXXX` (last 4 hex of the Bluetooth MAC).
- Framing: UTF-8 JSON objects terminated by `\n`. Messages longer than the negotiated MTU − 3
  are split into chunks; the receiver buffers until `\n`. Max message 1024 bytes.
- Every message has `"t"` (type) and `"v": 1` (protocol version). Helmet messages carry `"ts"` (unix ms).

### 8.1 Helmet → phone

| t | Fields | When |
|---|---|---|
| `hello` | `fw`, `lang`, `features` [list] | on connect |
| `status` | `uptime_s`, `cpu_temp_c`, `fps`, `faults` [list], `muted` | every 10 s and on change |
| `alert` | `id`, `level` 0–4, `kind` (`obstacle`,`drop`,`step_up`,`approach`,`face`,`sign`,`fault`), `dir` (`left`,`center`,`right`,`all`), `dist_m`?, `label`?, `text` | each spoken/haptic alert ≥ P3 |
| `speech` | `text`, `level` | everything spoken (for the app's accessible log) |
| `sos` | `id`, `reason` (`button`,`fall`), `state` (`countdown`,`sent`,`cancelled`) | SOS flow |
| `need_location` | — | B2 long press |
| `pong` | `id` | reply to ping |

### 8.2 Phone → helmet

| t | Fields | Effect |
|---|---|---|
| `loc` | `lat`, `lon`, `acc_m`, `addr`? | Latest location; `addr` spoken for "Where am I" if present |
| `ack` | `id` | Acknowledges `sos` |
| `say` | `text`, `level` (default 3) | Speak text through the helmet |
| `cfg` | `lang`?, `muted`?, `volume`? (0–100), `dropoff_sensitivity`? (`low`,`normal`,`high`) | Update settings at runtime |
| `ping` | `id` | Liveness |

Unknown types are ignored (forward compatibility).

`status` also carries `undervoltage` and `throttled` (booleans, omitted when unknown).

### 8.3 Security
- The helmet requires an **encrypted, bonded** BLE link: RX has `encrypt-write`, TX has
  `encrypt-read` + `encrypt-notify` (Just Works pairing — the helmet has no display). The phone OS shows
  a standard pairing dialog on first connection.
- `ble.bonded_only: true` (default): messages from non-bonded devices are dropped. Pairing is open while
  no phone is bonded, and afterwards only for 120 s after each boot. A new pairing is announced by voice.
- Safety-reducing `cfg` changes are always confirmed aloud at P2 (heard even when muted): mute on,
  drop-off sensitivity low, volume set below 30 %.
- `say` from the phone is capped at P2 (can never interrupt P0/P1 speech) and rate-limited to 1 per 3 s.

---

## 9. Software layout and interfaces

```
firmware/
  pyproject.toml            # package "owsh"; extras: pi, ocr, ble, dev
  config/default.yaml       # all thresholds from this spec
  owsh/__main__.py          # python -m owsh [--config path] [--sim] [--video file] [--no-window]
  owsh/app.py               # wires threads, bus, arbiter, watchdog
  owsh/config.py            # dataclass config + YAML loader + validation
  owsh/events.py            # Event types, Level enum (P0..P4)
  owsh/bus.py               # thread-safe publish/subscribe
  owsh/arbiter.py           # hazard → haptic pattern + speech decisions, cooldowns
  owsh/i18n/__init__.py, ko.json, en.json
  owsh/vision/camera.py     # Picamera2 | OpenCV index | video file
  owsh/vision/preprocess.py # dehaze/CLAHE
  owsh/vision/detector.py   # NanoDet-Plus ONNX (cv2.dnn), class filter
  owsh/vision/tracker.py    # IoU tracker + TTC
  owsh/vision/describe.py   # scene description text
  owsh/vision/faces.py      # YuNet + SFace + DB
  owsh/vision/ocr.py        # RapidOCR optional
  owsh/sensors/tfluna.py    # I2C driver (smbus2) + simulated
  owsh/sensors/reflex.py    # zone logic (5.1) + drop-off logic (5.2)
  owsh/sensors/imu.py       # MPU-6050 driver + fall detector (5.6)
  owsh/output/haptics.py    # pattern engine + mixer; backends: gpiozero PWM | sim
  owsh/output/audio.py      # speech queue; piper | espeak-ng | pyttsx3 | print
  owsh/input/buttons.py     # gpiozero | keyboard (sim)
  owsh/link/ble.py          # NUS GATT server via "bless"; no-op when unavailable
  owsh/link/protocol.py     # message encode/decode/chunking (pure, tested)
  owsh/watchdog.py
  owsh/sim/dashboard.py     # desktop debug window: video, boxes, motor bars, sim LiDAR sliders
  owsh/tools/download_models.py, enroll_face.py, tfluna_addr.py, bench.py
  tests/                    # pytest: arbiter, reflex, dropoff, tracker/TTC, haptic mixer, protocol, buttons, fall
  scripts/setup_pi.sh       # apt + venv + config.txt I2C + systemd
  systemd/owsh.service
hardware/
  openscad/lib/*.scad       # common: rounded boxes, saddle, strap slots, parameters
  openscad/*.scad           # one file per printable part
  stl/                      # rendered outputs (committed for non-CAD users)
  renders/                  # PNG previews
  wiring/                   # wiring diagram (SVG) + pin table
app/                        # PWA: index.html, app.js, protocol.js, i18n/, sw.js, manifest
docs/en, docs/ko            # guides
```

**Simulation mode (`--sim`)** runs on any PC with a webcam or a video file: LiDARs and IMU are
simulated from dashboard sliders/keys, haptics are drawn as bars and printed, buttons are keys
(`1`/`2`/`3` short, `Shift+1..3` or `q`/`w`/`e` long, `a`/`s`/`d` double), speech uses pyttsx3.

---

## 10. Printable parts list (OpenSCAD, parametric)

| File | Part | Material | Qty | Notes |
|---|---|---|---|---|
| `front_pod_base.scad` | Front pod body with camera bay (10° down), forward LiDAR bay, down LiDAR bay (50°) | PETG/ASA | 1 | Rain lip above lenses, strap slots 21 × 3 mm |
| `front_pod_cover.scad` | Rear cover with FPC and cable exit | PETG/ASA | 1 | |
| `main_case_base.scad` | Pi 5 case base with standoffs, IMU, ULN2003 and audio adapter bays, vents | PETG/ASA | 1 | Opening for USB-C power and cooler exhaust facing down/back |
| `main_case_lid.scad` | Lid with LED light pipe hole and drip edge | PETG/ASA | 1 | |
| `aux_pod_base.scad` | Aux pod base: ULN2003 and USB audio adapter cradles | PETG/ASA | 1 | Curved underside |
| `aux_pod_lid.scad` | Aux pod lid | PETG/ASA | 1 | |
| `saddle_pad.scad` | Conformal TPU saddle (param. curvature) under pod/case | TPU | 2 | |
| `button_module.scad` | Button housing for 3 × 12 mm switches | PETG | 1 | |
| `button_caps.scad` | Caps ○ △ □ with raised tactile edges | PETG | 1 set | |
| `haptic_pad.scad` | Coin-motor pad with Velcro recess | TPU | 3 | |
| `strap_anchor.scad` | 20 mm strap anchor / buckle | PETG | 4 | |
| `cable_clip.scad` | Cable clip for FPC cover and Dupont bundles | PETG | 6 | |
| `fpc_cover.scad` | Camera cable cover channel | PETG | 1 | |
| `rain_gutter_segment.scad` | Flow-channel segment (front high → rear low), clip-over-rim | TPU | 4 | Patent 112 |
| `rain_nozzle_rear.scad` | Rear nozzle collecting both sides | TPU | 1 | Patent 113 |
| `assembly_preview.scad` | Whole assembly on a helmet envelope (not printed) | — | — | For renders |

Curved-underside parts (front pod, main case, aux pod) need slicer supports from the build plate under the curved face. The saddle/pod curvature is set at print time by `helmet_radius` / `helmet_radius_long` — measure the helmet first.

Print settings (reference): 0.2 mm layers, 4 walls, 25 % gyroid infill (rigid), TPU 100 % walls
(3) 15 % infill, supports only under curved undersides (other overhangs ≤ 45°), PETG 240 °C / 80 °C.

---

## 11. Verification plan (summary)

| ID | Test | Pass criterion |
|---|---|---|
| T1 | Unit tests `pytest` | all pass |
| T2 | Reflex latency LiDAR → motor | ≤ 60 ms (log timestamp) |
| T3 | Vision FPS on Pi 5 | ≥ 8 FPS NanoDet 416 |
| T4 | Head-height obstacle (branch mock at 1.8 m) | Z2 before 1.2 m, Z1 before 0.6 m, 20/20 trials |
| T5 | Stairs down (5 staircases, day/night) | DROP before first step edge 19/20 |
| T6 | Approaching bicycle / person | APPROACH alert with TTC ≥ 1.5 s, 18/20 |
| T7 | False alarm rate, 30 min city walk | ≤ 2 P1 false alarms / 10 min |
| T8 | Fault injection: unplug camera / LiDAR; cover the lens | FAULT within 3 s for unplug (2 s frame timeout), within 4 s for covered lens, within 1 s for LiDAR |
| T9 | SOS: hold B3, fall on mattress | countdown, phone receives `sos` |
| T10 | Battery 20 000 mAh continuous | ≥ 6 h |
| T11 | Impact: added modules detach / do not penetrate | visual check after 1 m drop of helmet on headform; never certification-test a modified helmet for sale without an accredited lab |
| T12 | User trials with blind walkers + O&M instructor | qualitative report, safety incidents = 0 |
