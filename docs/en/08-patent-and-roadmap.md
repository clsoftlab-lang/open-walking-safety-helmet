# 08 · Patent Mapping and Roadmap

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This document shows how the reference design relates to Korean Patent No. 10-2560496, and where the
project is heading. Paragraph numbers in square brackets, such as [0033], refer to the patent
specification (`1020210101227.pdf` in the repository root, Korean).

> **Not legal advice.** The claim summaries below are informal English summaries for engineers.
> The official Korean text is authoritative. The permission to use the patent is set out in
> [PATENT_PLEDGE.md](../../PATENT_PLEDGE.md); where its Korean and English texts differ, the Korean text prevails.

## Contents

1. [Bibliographic data and the patent pledge](#1-bibliographic-data-and-the-patent-pledge)
2. [The claims in plain English](#2-the-claims-in-plain-english)
3. [Element-by-element mapping to v1.0](#3-element-by-element-mapping-to-v10)
4. [Description features beyond the claims](#4-description-features-beyond-the-claims)
5. [Roadmap principles](#5-roadmap-principles)
6. [Roadmap](#6-roadmap)
7. [How to help](#7-how-to-help)

## 1. Bibliographic data and the patent pledge

| Item | Value |
|---|---|
| Title (Korean) | 주변 인식이 가능한 보행 안전 헬멧 |
| Title (English) | Walking safety helmet capable of recognizing surroundings |
| Registration number | 10-2560496 (B1) |
| Registration date | 2023-07-24 (published 2023-07-26) |
| Application number | 10-2021-0101227, filed 2021-08-02 (examination requested the same day) |
| Laid-open publication | 10-2023-0019569, 2023-02-09 |
| Inventor | Lee Il-guk (이일국) |
| Patent holder | Dr. Lee Il-guk (이일국) of CLSOFTLAB (씨엘소프트랩), patentee and inventor of record |
| IPC | A42B 3/30, A42B 3/04, G01C 21/34, G06F 18/00, G08B 3/10, G08B 6/00, G08B 7/06, G09B 21/00 |
| Claims | 3 in force: claims 1, 4 and 5 (claims 2 and 3 deleted) |

The patent is a Korean patent. What the [patent pledge](../../PATENT_PLEDGE.md) says, in short:

- **Everyone, worldwide,** may make, use, improve, reproduce, sell, rent, import and export products based on the
  patent (and any divisional, conversion or foreign counterpart patents), **free, non-exclusive and royalty-free**.
- **Commercial and non-commercial use are both allowed.** No application, contract, report or payment is needed.
- Publishing and distributing derivative designs based on this repository is allowed.
- **Terms may change, but only for the future.** The patent holder may change the terms **prospectively**, from the
  date a change is published in the repository.
- **Existing implementers are protected:** products made, sold or distributed (or whose production had started)
  and derivative designs published before a change stay covered by the old terms, including use, repair and
  resale. A new owner of the patent must honour this protection.
- **Defensive termination:** the permission ends for anyone who first files a patent infringement lawsuit
  against the patent holder or a project contributor concerning these patents or this project.
- It is a patent permission only: no warranty, no trademark rights, and builders must follow local safety,
  medical-device and radio rules. Copyright terms for code, hardware and documents are in `LICENSE` and `NOTICE`.
- Requests, not obligations: credit the design, keep devices affordable, share field-test results.

## 2. The claims in plain English

### Claim 1 (independent)

A walking safety helmet comprising:

- **1a** a case unit;
- **1b** a camera unit on the case that captures images of the walker's surroundings;
- **1c** a vibration unit on the case that gives the walker vibration signals based on the images;
- **1d** a speaker unit on the case that gives the walker sound signals based on the images;
- **1e** a position sensor unit on the case that measures the walker's position;

wherein

- **1f** the camera unit includes an image module, a character (text) recognition module for text
  around the walker, and a face recognition module that recognises preset faces to tell whether a person
  is an acquaintance;
- **1g** when text is recognised, the camera unit sends electrical signals to the vibration and speaker units
  to guide the walker;
- **1h** when an acquaintance is recognised, the camera unit sends electrical signals to the vibration and
  speaker units;
- **1i** the vibration and speaker units receive those signals and guide the walker with vibration and sound;
- **1j** the camera unit learns, by deep learning, the criteria for sending those signals;
- **1k** the case includes an **air-curtain module** that blows high-pressure air from a compressor outward
  to change the direction of fluid (rain) falling toward the walker, a **flow-channel module** that forms a
  channel so fluid running down the case does not reach the walker, and a **nozzle module** that discharges
  the channelled fluid at the rear of the case;
- **1l** the air-curtain module and the flow-channel module each run along the circumference of the case;
- **1m** the nozzle module is at the rear of the case and connects to the flow channel;
- **1n** the air-curtain module blows air downward, at a diagonal;
- **1o** the flow channel becomes lower from the front of the case toward the rear.

### Claim 4 (depends on claim 1)

Adds a **navigation unit** on the case that, when the walker's final destination is entered, provides route
guidance based on the walker's position.

### Claim 5 (depends on claim 1)

Adds a **communication unit** on the case that can communicate externally, and a **microphone unit** on the
case or the speaker unit that picks up the walker's voice. The microphone works with the communication
unit to allow **voice calls**.

## 3. Element-by-element mapping to v1.0

This table expands [spec §2](00-system-design-spec.md#2-patent-feature-mapping). Status values are the spec's.

| Patent element | Claim | Paragraphs | v1.0 implementation | Status |
|---|---|---|---|---|
| Case unit 110 | 1a | [0024], [0027]–[0028] | A certified bicycle/multisport helmet with printed clip-on modules (front pod, main case, aux pod, button module) on conformal 3 mm TPU saddles. The patent says the case protects the head and may have vent holes [0028]. v1.0 keeps the certified helmet intact and uses its vents for straps. | v1.0 |
| Camera unit 120 / image module 121 | 1b, 1f | [0030], [0033], [0050] | Camera Module 3 Wide, NanoDet-Plus detector, IoU tracker, time-to-contact (spec §5.3) | v1.0 |
| Danger: objects approaching the walker | 1b | [0033] | APPROACH P1 / P2 alerts with side (spec §5.3) | v1.0 |
| Danger: stairs or cliff on the walking path | — | [0033] | Down-looking TF-Luna drop-off detector (spec §5.2). Implemented with LiDAR rather than the camera, so it works without AI (P5). | v1.0 |
| Surrounding object information | — | [0050] | "Describe scene" on △ B2 (spec §5.3) | v1.0 |
| Character recognition module 122: text and simple figures | 1f, 1g | [0035] | Button-triggered OCR (RapidOCR, optional install) | v1.0 (optional install) |
| Sign text judged dangerous | 1g | [0036] | Danger keyword list per language; "Warning sign:" prefix (spec §5.5) | v1.0 |
| Elevator buttons, door open/close, floor; hand guided to button | — | [0037] | Planned: OCR of button labels and hand tracking | Roadmap v1.2 |
| Face recognition module 123: acquaintance | 1f, 1h | [0038] | YuNet + SFace, local enrolment, tag `friend` | v1.0 |
| Face recognition: person to avoid | — | [0039] | Tag `avoid`, P2 WARNING (spec §5.4) | v1.0 |
| Face recognition with a mask | — | [0040] | Partial faces accepted when detector confidence ≥ 0.6; configurable threshold | v1.0 |
| Deep learning for signal criteria | 1j | [0031] | Neural detectors (NanoDet-Plus, YuNet, SFace) trained by deep learning feed the rule-based arbiter. Thresholds are explicit and reviewable for safety. | v1.0 |
| Accessible facility recognition | — | [0034] | Custom detector for tactile paving, ramps, crossings | Roadmap v1.3 (needs dataset) |
| Rain and fog removal by deep learning | — | [0033] | CLAHE-based dehaze pre-filter (`vision.dehaze`); learned model later | v1.0 basic, learned model roadmap |
| Cameras front/back/left/right or 360° | — | [0032] | One front wide camera; rear camera expansion | v1.0 front, rear roadmap |
| Vibration unit 130 on the inner surface | 1c, 1i | [0041] | 3 coin ERM motors in TPU pads on the comfort padding | v1.0 |
| Vibration useful for hearing-impaired walkers | — | [0042] | Complete haptic language; haptic-only mode planned | v1.0 haptics; mode roadmap |
| Vibration intensity and pattern by signal type; side-specific | 1c | [0043] | Priorities P0–P4 and the pattern table (spec §6) | v1.0 |
| Number shown by vibration count | — | [0044] | Pattern `count_n` | v1.0 |
| Speaker unit 140 near both ears | 1d, 1i | [0045]–[0046] | USB audio to open-ear or bone-conduction headset. The patent also mentions headphones, earphones and a hearing-aid function; v1.0 deliberately keeps ears open for traffic sounds. | v1.0 |
| Sound by signal type ("danger", "move left"); numbers and letters | 1d | [0047]–[0049] | Priority speech queue, i18n phrases (spec §7.1) | v1.0 |
| Position sensor unit 150 | 1e | [0051], [0053] | Phone GPS over BLE (`loc` message); optional helmet GPS on UART | v1.0 phone, helmet GPS optional |
| Warning when in a dangerous area | — | [0051] | Not yet implemented | Roadmap v1.1 |
| Position sensor and navigation in one terminal | — | [0025] | The phone provides location | v1.0 |
| Navigation unit 160: destination, route guidance by vibration/sound or external device | 4 | [0054]–[0056] | Destination beacon and integration with existing accessible navigation apps; `turn_left` / `turn_right` patterns reserved | Roadmap v1.1 |
| Communication unit 170 | 5 | [0057] | Encrypted, bonded BLE Nordic UART Service link to the phone app (spec §8, §8.3) | v1.0 |
| Emergency report to 119 / 112 via phone over Bluetooth, with location | — | [0052], [0058] | SOS by long press or fall detection; app shows location and one-tap call / SMS. User or bystander confirms (web platform limit). | v1.0 (user confirms call) |
| Emergency report and calls with a SIM in the helmet | — | [0059] | Not in v1.0 | Roadmap (cellular option) |
| Microphone unit 180, voice call | 5 | [0060]–[0061] | Headset mic through the phone's Bluetooth audio | v1.0 via phone |
| Voice input of destination | 4 | [0054], [0060] | Planned with navigation, on the phone | Roadmap v1.1 |
| Fan in the case | — | [0028] | Passive vents; Pi Active Cooler for electronics only | v1.0 passive |
| Battery module, wired/wireless charging, detachable | — | [0029] | USB-C power bank in pocket or waist bag with breakaway cable, so no battery mass on the head | v1.0 |
| Air-curtain module 111 with compressor and injectors | 1k, 1l, 1n | [0062]–[0064] | Concept and experimental module documentation only (see [6.8](#68-air-curtain-experiment)) | Experimental |
| Flow-channel module 112 | 1k, 1l, 1o | [0065]–[0067] | Printed TPU rain gutter segments along the lower rim, front high → rear low, with outer lip. Currently about 86 g, over budget (see [6.9](#69-lighter-rain-gutter)). | v1.0 optional print |
| Nozzle module 113 at the rear | 1k, 1m | [0065], [0068] | Printed TPU rear nozzle collecting both sides | v1.0 optional print |

## 4. Description features beyond the claims

The description includes ideas that are not required by any claim but are part of the inventor's vision.
They guide the roadmap:

- **Hearing-impaired walkers** [0001], [0004], [0042], [0046]: vibration as the main channel, hearing-aid
  function in the speaker.
- **Distracted sighted pedestrians** [0003]–[0004]: the same warnings help anyone looking at a phone. The
  project's focus stays on blind and low-vision users.
- **Escalators and moving walkways** [0004] are named as dangerous for cane users. No v1.0 feature targets them.
- **Detachable injectors** of several types (shear, swirl, pintle, jet) [0063].
- **A lip on the outer edge** of the flow channel [0067], included in the gutter design.

## 5. Roadmap principles

- **Safety before features.** No feature may weaken the helmet (P1), the reflex path (P5) or FAULT
  reporting (P4).
- **Spec first.** Every roadmap item starts as a change to the
  [system design specification](00-system-design-spec.md), then implementation, then tests.
- **Alert logic changes need a safety review** ([GOVERNANCE.md](../../GOVERNANCE.md)).
- **Permissive licences only** (P9). For example, AGPL-licensed detectors and training frameworks cannot
  be part of the default build.
- **No dates are promised.** Items move when contributors, testers and evidence are ready.

## 6. Roadmap

### 6.1 v1.1 · Navigation

Patent: claim 4, [0051], [0054]–[0056].

- **Destination beacon.** The user sets a destination on the phone (screen reader or voice). The phone
  computes the bearing to the next waypoint. The helmet gives `turn_left` / `turn_right` cues (already
  reserved in spec §6.2) and short voice hints.
- **Integration, not reinvention.** Hand off to existing accessible navigation apps and open map data where
  possible, rather than building a new routing engine.
- **Dangerous-area warnings** [0051]: user- or instructor-defined zones (a construction site, a busy
  junction) that trigger a warning when entered.
- **Honest limits.** Phone GPS is often 5–10 m off in cities. That is not accurate enough to line up with a
  crossing or find a door. Navigation cues are hints; they never override hazard warnings.
- **Needs:** protocol messages for waypoints (spec §8 change), arbiter rules so navigation never masks P0–P2,
  field tests in several countries.

### 6.2 v1.2 · Elevator buttons and hand guidance

Patent: [0035], [0037].

- **Recognise the panel.** OCR of floor numbers and labels, plus the "simple figures" [0035] for door open
  and close (◀▶ and ▶◀ shapes) and the alarm bell.
- **Guide the hand.** Track the user's hand with a permissively licensed hand-landmark model. Guide the
  fingertip to the chosen button with left/right vibration and short voice cues ("up", "down", "press").
  Confirm the button name by voice before the user presses.
- **Safety.** Never guide to the alarm button without an explicit request. Report confidence honestly; say
  "not sure" rather than guess.
- **Needs:** a dataset of elevator panels from many countries and manufacturers, including braille labels
  and worn buttons; evaluation of guidance accuracy with blind testers.

### 6.3 v1.3 · Accessible facility detector — call for dataset contributors worldwide

Patent: [0034].

The helmet should recognise the things built to help blind people. No good open dataset covers them
across countries, so **we need your help.**

**Target classes (draft v0):**

- Tactile paving: warning (dot) blocks and guiding (bar) blocks
- Kerb ramps and dropped kerbs
- Pedestrian crossings (zebra and other markings)
- Accessible pedestrian signal push buttons
- Stair handrails, stair nosing contrast strips
- Elevator doors and call buttons
- Accessible entrance signs

**How to contribute images:**

- Capture from **head height (about 1.6 m)**, camera tilted about 10° down, with a wide lens (a Camera Module 3
  Wide, or a phone's wide camera).
- Cover **variety**: countries, day and night, rain, snow, worn and dirty paving, different colours and materials.
- **Privacy first:** blur faces and vehicle licence plates **before** uploading. Do not photograph private
  property without permission. Do not include people who have not agreed.
- **Licence:** contribute under **CC BY 4.0** or **CC0**, and confirm you took the photos or have the right to
  share them.
- **Annotation:** bounding boxes in COCO JSON or YOLO text format, using the class list above. Polygons for
  tactile paving are welcome.
- Include a short **data card**: country, city (no exact addresses), device, lighting, weather.

**How the model will be built:** a small detector with a permissive licence, trained with permissively
licensed code, evaluated with a separate test split for each country so we can see where it fails.

Open a feature request or discussion before starting a large collection, so work is not duplicated.

### 6.4 Rear camera

Patent: [0032].

- The Pi 5 has a second camera connector (CAM/DISP 1). A rear camera can watch for **bicycles and e-scooters
  approaching from behind** on shared paths.
- **Costs:** about 1 W more power, lower frame rate for both cameras, more mass at the rear.
- **Needs:** a spec change for the rear haptic cue (for example a new pattern), a rear mount that meets P2,
  and T6-style tests from behind.

### 6.5 Native Android and iOS apps with automatic SOS

Patent: [0052], [0058].

- The current web app needs someone to confirm the emergency call or SMS. That is a platform rule for web apps.
- **Android:** a native app can place a call or send an SMS automatically with the user's permission. App-store
  rules restrict SMS and call permissions, so the app will need to follow those policies carefully.
- **iOS:** apps cannot place a call or send an SMS without the user confirming. Automatic alerts on iOS would
  need another route, for example a notification to a guardian's app, or an online messaging service. Those
  add internet dependency and privacy questions.
- Both apps should also keep the BLE connection alive reliably in the background (web pages are paused when the
  screen is off), with full screen reader support, and keep the encrypted pairing of spec §8.3.
- An automatic SOS must still give the user a clear, accessible way to cancel, and guardians must know what an
  automatic message means.
- **Needs:** mobile developers, accessibility testers, and a clear privacy design.

### 6.6 Learned dehaze

Patent: [0033].

- Replace or complement the CLAHE pre-filter with a small learned dehaze or de-rain network.
- It must **earn its place**: measured detection improvement in fog and rain, against its frame-rate cost on the Pi.
- Run it only when needed (for example when image contrast is low), so clear-weather performance is not reduced.
- **Needs:** paired or labelled rain and fog footage from head height, and a permissively licensed model.

### 6.7 Cellular option and haptic-only mode

Patent: [0042], [0046], [0059].

- **Cellular modem (optional).** A small LTE module with a SIM could send an emergency message without a phone.
  Costs: power, mass, a SIM plan, and regional certification.
- **Haptic-only mode** for deafblind and hearing-impaired users: every spoken message gets a haptic equivalent;
  longer count patterns; optional pairing with hearing aids.

### 6.8 Air-curtain experiment

Patent: claim 1 (1k, 1l, 1n), [0062]–[0064].

The patent describes an air curtain that blows high-pressure air downward and outward around the helmet, so that
rain is deflected away from the walker. We will document an **experimental** module. Here is an honest
first estimate of why it is hard to make practical.

**Order-of-magnitude estimate (assumptions stated):**

| Quantity | Assumption / result |
|---|---|
| Curtain length | Helmet rim perimeter ≈ 0.75 m |
| Slot width | 1 mm, so outlet area ≈ 7.5 × 10⁻⁴ m² |
| Rain drops | 2 mm drops fall at about 6.5 m/s; 5 mm drops at about 9 m/s |
| Jet speed needed | A thin air jet slows quickly. To still have about 10 m/s a few cm from the slot, the outlet speed must be roughly 30 m/s. |
| Air flow | 7.5 × 10⁻⁴ m² × 30 m/s ≈ 0.023 m³/s ≈ **1 350 L/min** |
| Jet kinetic power | ½ × 1.2 kg/m³ × 7.5 × 10⁻⁴ m² × (30 m/s)³ ≈ **12 W** |
| Electrical power | Small blowers are roughly 25–40 % efficient, plus duct losses: **about 30–50 W** |
| Compare | All v1.0 electronics use about **8 W** |
| Battery effect | A 20 000 mAh power bank would last about **1–1.5 h** instead of about 7 h |
| Compressor option | Small 12 V diaphragm pumps deliver roughly 15–30 L/min at 12–24 W: **50–100 times too little flow** for a continuous full-rim curtain |
| Noise | Small high-speed blowers and air jets are typically 55–70 dB(A) at 1 m, and louder at the ear |

**Why noise matters most.** Blind pedestrians rely on hearing traffic. Quiet electric vehicles are required in
many regions to emit only modest warning sounds at low speed. An air curtain next to the ears could mask exactly
those sounds. A feature that keeps the user dry but hides an approaching car makes walking **less** safe.

**A smaller experiment that may be worth doing:** a short **air knife over the camera and LiDAR windows only**
(about 10 cm of slot), to keep rain drops off the lenses. Flow and power fall roughly in proportion to slot length,
so this might need only a few watts. Noise still has to be measured.

**Experiment protocol (proposal):**

1. Build a front-sector air knife on a test helmet (never for real walks at first).
2. Measure electrical power with a USB power meter.
3. Measure sound level at the ear position with a sound level meter, air knife on and off.
4. Spray-rig test: detection rate and `camera_blocked` faults with and without the air knife.
5. Report all results, including failures.

Proposed go/no-go criteria for discussion: under 3 W added, no audible masking at the ear (target: added level
under about 45 dB(A)), and a measurable reduction in rain-related faults.

The passive parts of the patent's rain design, the flow channel and rear nozzle, need no power and are already
printable in v1.0.

### 6.9 Lighter rain gutter

Patent: claim 1 (1k, 1l, 1o), [0065]–[0068].

- The printed TPU gutter (4 segments, about 86 g) and rear nozzle (about 9 g) together weigh about 95 g, above the
  60 g budget in spec §4.3. With the gutter, the added mass is about 425 g, over the 380 g limit.
- Ideas: thinner walls, shorter or fewer segments covering only the front and sides, a lip-only profile, lighter
  or foamed TPU, or combining the channel with the saddles.
- It must still clip on without glue, detach under impact (P2), keep the front-high → rear-low slope, and not trap
  water near the electronics.
- **Needs:** designs, printed prototypes, weight measurements and spray-rig or real-rain tests.

### 6.10 VL53L1X driver for a budget build

- A budget build with ST VL53L1X sensors instead of the TF-Luna is described in the
  [bill of materials](01-bill-of-materials.md#budget-variant). **Firmware v1.0 does not support it.**
- A driver would need: I2C address assignment at every boot using one XSHUT GPIO per sensor (a spec §4.2 pin map
  change), long-distance mode and timing budget settings, mapping of its signal status to "no return", and a
  simulator back end.
- Honest limits to test and document: short range in sunlight (often under 1 m), a wide field of view (about 27°)
  that changes zone behaviour, and whether the down-looking drop-off detector can work at all outdoors.
- It must pass T2, T4, T5 and T7 before any build using it is recommended for walking.

### 6.11 Lighter and cheaper compute

The Pi 5 uses about 6.5 W and needs a cooler. Options to explore:

- **Reflex-only helmet.** A microcontroller (for example an RP2040 or ESP32-S3 board) with the two TF-Luna sensors,
  the IMU, the motors and the buttons. No camera. Under 1 W, very cheap, many hours of battery. Keeps the safety
  path (P5). Loses approach warnings, text reading and faces.
- **Raspberry Pi AI Camera** (Sony IMX500 with on-sensor neural network processing). Moves detection into the camera,
  so a smaller, cooler board could run the rest. Needs model conversion and a check of frame rate and field of view.
- **AI accelerator on the Pi 5** (for example a Hailo-8L based kit). Much faster detection, but more power and mass.
  Better suited to adding the rear camera or facility detection than to saving energy.
- **Other boards with an NPU** (for example Rockchip RK3566 / RK3588). Good performance per watt; software support
  and global availability vary.
- **Phone as the computer.** Cheap, but adds wireless latency, phone battery drain and privacy concerns, and breaks
  offline-first if the phone is lost. Not recommended for the safety path.

Every option must pass the same tests (T1–T12, and the proposed T13–T15) before it is recommended.
A lower-profile compute module would also help the main case, which needs up to 40 mm of height for the Pi 5
and its cooler.

## 7. How to help

- Pick a roadmap item and open a feature request: [CONTRIBUTING.md](../../CONTRIBUTING.md).
- Share field tests: [field test report](../../.github/ISSUE_TEMPLATE/field_test_report.yml).
- Translate: [09 · Translation guide](09-translation-guide.md).
