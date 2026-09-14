# 06 · Safety

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

Read this page before building, adjusting or walking with the helmet. Builders, users, families and
O&M instructors all share responsibility for safe use.

## Contents

1. [Core rules](#1-core-rules)
2. [Helmet integrity rules](#2-helmet-integrity-rules)
3. [Known failure modes](#3-known-failure-modes)
4. [What FAULT means](#4-what-fault-means)
5. [Electrical and battery safety](#5-electrical-and-battery-safety)
6. [Testing before real-world use](#6-testing-before-real-world-use)
7. [Privacy](#7-privacy)
8. [Bluetooth security](#8-bluetooth-security)
9. [Legal and medical disclaimer](#9-legal-and-medical-disclaimer)
10. [Reporting safety problems](#10-reporting-safety-problems)

## 1. Core rules

1. **Assist, never replace.** The helmet complements the white cane, a guide dog and O&M skills. It
   never replaces them (spec P3).
2. **Silence is not proof of safety.** Sensors have blind spots. Expect missed hazards.
3. **Never degrade impact protection.** A certified helmet, never modified (spec P1).
4. **FAULT means stop relying on the helmet** until it is checked.
5. **Test before trusting.** Every helmet, every change, every new user: test first
   ([07 · Test plan](07-test-plan.md)).

## 2. Helmet integrity rules

The helmet exists because sensors can fail. If a collision or fall happens anyway, the helmet must
still protect the head exactly as certified.

### Always

- Use a **new, certified** bicycle or multisport helmet (EN 1078, CPSC 1203, AS/NZS 2063, KC or equivalent),
  sized to the wearer.
- Attach modules only with **hook-and-loop straps through existing vents** and **removable pads**
  (3M Dual Lock or VHB) on the outer shell.
- Keep every module **low-profile** (spec P2). Maximum height above the shell: **35 mm for the front pod**,
  **40 mm for the main case** (a Pi 5 with Active Cooler cannot fit lower), **30 mm for every other module**.
  Measured on the v1.1 parts: 34.8 mm, 39.8 mm, aux pod 23.4 mm, button module about 21 mm.
- Undersides follow the shell on a **uniform 3 mm TPU saddle**: no stilts, and no gap larger than 5 mm that
  could catch a branch.
- All outer edges rounded (fillet ≥ 3 mm), no sharp points.
- Make sure modules can **break away** under impact rather than transmit force into the head.
- Keep the **total added mass ≤ 380 g** without the rain gutter, with the battery off the helmet. The reference
  build is about 330 g. The optional rain gutter adds about 95 g (about 425 g in total), which is over budget;
  leave it off or use fewer segments.
- Keep the **power cable breakaway** (magnetic adapter), routed down the back, never around the neck.
- Keep the **ears open**: open-ear or bone-conduction headset only.

### Never

- Never **3D-print a helmet shell** or use a non-certified hat, cap or shell.
- Never **drill, cut, glue into, heat or melt** the shell or the EPS foam liner.
- Never use **solvents, paints or strong adhesives** on the shell beyond the removable pads.
- Never replace straps with **screws, zip ties or glue**. Modules must be able to detach.
- Never add **rigid parts inside** the helmet between the liner and the head. Haptic pads are soft
  TPU on the comfort padding only.
- Never add a **visor, spike, antenna or rigid bracket** that sticks out.
- Never use a helmet that has had an **impact**, even if it looks undamaged. Move the modules to a new helmet.
- Never **sell a modified helmet as certified**. Certification tests apply to the helmet as sold.
  Adding modules can change the result, and only an accredited laboratory can test that.

## 3. Known failure modes

These are the situations where the helmet is known to work poorly, or not at all. Users, families
and instructors should know them.

### 3.1 Forward LiDAR (head-height obstacles)

- **Narrow beam.** The TF-Luna measures a 2° cone straight ahead: about 7 cm wide at 2 m. Anything
  beside that line is not measured. Turning the head slowly helps scan.
- **Thin objects.** Wires, thin branches, cables and chains hanging at head height can be missed.
  Branches with sparse leaves may return a distance only sometimes.
- **Glass and mirrors.** Glass doors, shop windows and glass barriers may let the beam pass through
  or reflect it away. The obstacle is then not detected. Mirrors and polished metal can give a
  wrong distance.
- **Bright sunlight.** Strong sunlight adds infrared noise. Range becomes shorter and readings noisier,
  so warnings can come later or not at all.
- **Dark, matte surfaces.** Black clothing, dark vehicles and dark painted poles reflect less. Range
  becomes shorter.
- **Very close objects.** The TF-Luna cannot measure closer than about 0.2 m. If an obstacle was in Z1 and the
  reading drops out, the `zone1` warning is held for 0.5 s, then stops. Something pressed against the pod gives
  no warning.
- **Head posture.** If the head tilts down, the beam hits the ground ahead. If it tilts up, the beam
  passes over obstacles. Calibrate with the real user ([04 · Assembly guide, part H](04-assembly-guide.md#part-h--calibration)).

### 3.2 Down-looking LiDAR (drop-offs and steps)

- **Dark or wet surfaces.** Wet asphalt, black rubber mats, puddles and very dark tiles can return no
  signal. By default this counts as a **DROP** (a false alarm), because a missed drop is worse. If a
  user lowers the sensitivity, real drops on dark surfaces may be **missed**.
- **Shallow steps.** Changes smaller than the thresholds (distance change of 30 % down or 30 % up) are
  not reported. Low kerbs and single shallow steps may be missed.
- **Learning the ground distance.** The expected ground distance is learned from about 3 seconds of steady
  samples. For safety it is **never increased automatically**: standing still at a platform edge must not teach
  the track bed as "ground". A shorter stable distance (sitting down, a slope) is re-learned only after 10 s.
  Consequences: the starting value `dropoff.sensor_height_m` must match the wearer, and right after sitting,
  bending or climbing, detection can be less reliable or give a "Step up ahead." warning until re-learned.
- **Descending ramps and slopes** change the expected distance slowly and may not trigger.
- **Escalators, moving walkways and platform edges** are not specifically recognised. Use your usual
  techniques and assistance.

### 3.3 Camera (approaching objects, text, faces)

- **Night and darkness.** The camera needs light. At night, approach warnings, text reading and face
  recognition may not work. In very dark places (or when at least 97 % of the image is dark) the helmet raises
  the FAULT `camera_blocked`. The LiDAR warnings still work.
- **Rain drops, mud, fog, condensation** on the lens blur the image. Detection gets worse. A covered or
  smeared lens raises FAULT `camera_blocked`.
- **Backlight and glare.** Walking toward a low sun can hide people and vehicles.
- **Fast vehicles.** Warnings are based on how quickly an object grows in the picture, and the condition must
  hold on 2 consecutive processed frames (to suppress jitter). At about 8 FPS that adds roughly 0.1 s. Fast
  vehicles may leave little time. The camera looks only **forward**, so nothing from behind is detected.
- **Unusual objects.** The detector recognises common classes (people, bicycles, cars, motorcycles,
  buses, trucks, dogs, horses and some street furniture). E-scooters, wheelchairs, strollers, carts and
  animals it was not trained on may be missed or mislabelled.
- **Text reading errors.** OCR can misread, skip or invent words, especially on curved, reflective,
  handwritten or distant signs. Never rely on OCR for medication, money or safety instructions.
- **Face recognition errors.** It can fail to recognise a friend, recognise the wrong person, or miss
  a person to avoid. Masks, hats, lighting and angle all affect it. Never rely on it for personal safety.
- **Processing speed.** When the Pi is hot or busy, the frame rate drops. Warnings then come later.

### 3.4 Weather

- **Heavy rain:** LiDAR beams can return from water drops and a water film on the window. Expect false
  near warnings, missed drops and camera faults.
- **Fog, mist, snow:** similar effects, with shorter range for both LiDAR and camera.
- **Heat:** direct sun on the case can make the Pi throttle. Printed PETG/ASA parts are chosen to keep
  their shape, but a helmet should not be left in a hot car.
- **Cold:** power banks deliver less capacity.
- The helmet is **not waterproof**.

### 3.5 Power and battery

- **No battery gauge.** The Pi cannot read the power bank's charge. It warns only when the supply voltage is
  already too low: under-voltage for 10 s or more gives "Power is low. Charge the battery soon." (P2, at most once
  every 5 minutes). Many power banks simply switch off when empty, with no under-voltage first. Then the helmet
  **stops without warning**, and silence means "no power", not "safe". Charge daily and carry a spare for long trips.
- **Weak power banks or thin cables** (below 5 V 3 A) cause under-voltage, slow processing and random restarts.
  The low-power warning points to this.
- **Overheating.** At a CPU temperature of 80 °C or more the helmet says "Helmet is overheating." (P2, at most once
  every 5 minutes). The Pi then slows down, so camera warnings come later. The LiDAR warnings keep working.
- **Cable disconnects.** The breakaway adapter is designed to separate under a pull. After it
  separates, the helmet is off. Reconnecting starts it again, which takes about a minute.
- **Memory card damage.** Sudden power loss can occasionally corrupt the microSD card. Use the safe shutdown
  (hold ○ B1 + □ B3 for 5 s) before unplugging.

### 3.6 Audio and attention

- The voice must never hide traffic sounds. Keep the volume moderate and use only open-ear or
  bone-conduction headsets.
- Too many warnings are tiring and can be ignored. Report false alarms so thresholds can be improved.
- **Mute** silences only low-priority speech. Warnings (P0–P2) and answers to the user's own button presses are
  always spoken.

### 3.7 Rain gutter

- The optional TPU rain gutter and nozzle weigh about 95 g, above their 60 g budget. With the gutter, the added mass
  is about 425 g, over the 380 g limit. A lighter gutter is on the roadmap.

## 4. What FAULT means

The helmet watches every part of itself (spec §5.7). When something fails:

- **Safety-relevant parts** (camera, LiDARs, vibration motors, IMU): three very quick buzzes on the forehead
  (`fault`) and a voice message, **repeating every 10 seconds** (P0) while the problem lasts.
- **Other parts** (face recognition, text reading, Bluetooth, settings file): announced **once** by voice (P2).
  They do not repeat, because they do not affect hazard warnings.
- **Voice:** names the failed part, for example "Front distance sensor not working." or "Camera is covered or too dark."
- **Phone app:** shows the fault in the status.

What it can mean:

| Fault | Typical cause | What still works |
|---|---|---|
| Camera (no frames for 2 s; FAULT within about 3 s) | Cable loose, camera broken, software crash | LiDAR warnings, buttons, SOS |
| `camera_blocked` (dark for 3 s, or smeared for 5 s; FAULT within about 4 s) | Lens covered, dirty, wet, or very dark place | LiDAR warnings ("Distance sensors still active") |
| LiDAR (no data for 0.5 s; FAULT within 1 s) | Loose wire, sensor broken | Camera warnings, if light is good. **The head-height or drop warning for that sensor is gone.** |
| IMU (no data for 1 s) | Loose wire | Everything except **fall detection** |
| Vibration motors | Driver or wiring problem | Voice warnings only. **Treat as a serious fault.** |
| Audio | Adapter unplugged, headset missing | Vibration only |
| Face recognition, text reading, Bluetooth, settings (announced once) | Missing model, optional package not installed, Bluetooth stack problem, error in the settings file | All hazard warnings. Without Bluetooth: no phone location and no SOS delivery to the phone. |

What to do:

1. **Stop relying on the helmet.** Continue with your cane or guide dog only.
2. If possible, get to a safe place and ask for help.
3. The builder checks connections, cleans the lenses, and reads the log (`journalctl -u owsh`).
4. When the part works again, the voice says it recovered.

The rule behind this: **silence must never mean "safe" when something is broken** (spec P4).

## 5. Electrical and battery safety

- Use a **quality USB-C PD power bank** from a known brand, with overcharge and short-circuit protection.
- Do not charge a **damaged, swollen, hot or wet** power bank. Recycle it properly.
- Do not charge the power bank while it is in a closed bag against the body.
- Airlines limit large power banks. Check before flying.
- Keep **wires enclosed** in the printed covers. No bare conductors near skin or hair.
- The haptic motors are 3 V parts driven at a capped duty. **Do not raise `haptics.max_duty`** above 75 %.
  Overdriven motors get hot.
- If you smell burning, feel unusual heat or hear crackling, unplug the power and stop using the helmet.

## 6. Testing before real-world use

**The builder is responsible for testing each helmet before anyone walks with it.** An O&M
instructor or experienced sighted companion should be present for the first outdoor walks.

Minimum before the first outdoor walk:

1. Pass the wiring checks ([02 · Wiring guide](02-wiring-guide.md#7-checks)).
2. Pair the user's phone and pass the first boot checklist ([04 · Assembly guide, part G](04-assembly-guide.md#part-g--first-boot-test-checklist)).
3. Run at least T2, T4, T5, T8, T9, T13 and T14 from [07 · Test plan](07-test-plan.md).
4. Calibrate with the actual user ([04 · Assembly guide, part H](04-assembly-guide.md#part-h--calibration)).
5. Train the user on the vibration language and limitations ([05 · User guide](05-user-guide.md)).

Repeat testing after:

- Any firmware or configuration change.
- Moving modules or changing the helmet.
- A drop, impact or water exposure.
- Any FAULT that was not simply a covered lens.

Test safely:

- Use soft mock obstacles (foam, cardboard, a pool noodle on a stand), never real hazards.
- Test stairs **with a sighted spotter** holding the tester's arm, starting at the bottom step or on a
  single kerb, never at the top of a long staircase.
- Test approaching bicycles and people at walking speed in a closed space, with a sighted person
  controlling the approach. **Never test with real traffic.**
- Stop any test immediately if the tester feels unsafe.

## 7. Privacy

- **Faces stay on the helmet.** Face photos and face data (embeddings) are stored only on the helmet's
  memory card (`data/faces/`). They are never sent over Bluetooth. Only the enrolled name is sent to the
  phone for the log (spec §5.4).
- **No cloud.** All hazard detection runs on the helmet. The camera image is not uploaded anywhere.
- **Consent.** Enrol a person's face only with their **clear consent**. Explain what is stored and how to
  delete it. Delete it when they ask: `python -m owsh.tools.enroll_face --remove "<name>"`.
- **"Avoid" tags** describe real people. Handle them with care, and only for the user's personal safety.
- **Local law.** In many places, face data is sensitive personal data (for example under the EU GDPR or
  Korea's Personal Information Protection Act). Rules on cameras in public places differ between countries.
  Check local rules before using face recognition, and consider leaving it off.
- **Paired phones only.** Names of recognised friends go only to the paired phone, over an encrypted link
  (section 8).
- **Losing the helmet** means someone could read the memory card. Keep enrolments minimal. Delete the
  face folder before giving the helmet away, repairing it, or recycling it.
- **The phone app** stores location, the helmet's speech log and guardian numbers on the phone. Protect
  the phone with a screen lock.

## 8. Bluetooth security

The phone link can change safety settings, so it is protected (spec §8.3):

- **Encrypted, paired link.** The helmet accepts commands only over an encrypted Bluetooth link from a
  **paired (bonded) phone** (`ble.bonded_only: true`). Messages from other devices are dropped.
- **Limited pairing window.** Pairing is open while no phone is paired. After that, it is open only for the first
  **2 minutes after each start**. Pairing uses "Just Works" (no PIN), because the helmet has no screen or keypad.
- **Every new pairing is announced:** "New phone paired: <name>." If the user hears this and did not pair a phone,
  someone else paired during the window. Remove all pairings (`bluetoothctl devices Paired`, then
  `bluetoothctl remove <address>`) and restart the helmet.
- **Safety-reducing changes are always spoken**, even when muted, so they can never happen silently:
  - "Voice info muted by phone. Warnings are still spoken."
  - "Drop-off sensitivity set to low by phone."
  - "Volume set to N percent by phone." (below 30 %)
  If the user hears one of these unexpectedly, check the phone and the pairings.
- **Phone speech is limited.** Text the phone asks the helmet to say is capped at priority P2, so it can never
  interrupt a "Stop." or a drop warning, and it is limited to one message every 3 seconds.

Remaining risks:

- "Just Works" pairing does not protect against an attacker who is nearby **during** the pairing window. Pair in
  a private place, and do not leave the helmet freshly restarted in crowded places without a paired phone.
- A lost or stolen paired phone can still control the helmet. Remove its pairing.
- Radio jamming can block the phone link. Hazard warnings do not depend on the phone.

Security problems are reported privately: see [SECURITY.md](../../SECURITY.md).

## 9. Legal and medical disclaimer

- The Open Walking Safety Helmet is an **open-source reference design for an assistive aid**. It is
  **not a certified medical device** in any country. It has not been approved or cleared by any
  regulator (for example MFDS in Korea, FDA in the USA, or under the EU MDR).
- It is provided **"as is", without warranty** of any kind, as stated in the software, hardware and
  documentation licences and the [patent pledge](../../PATENT_PLEDGE.md). The authors and contributors are
  not liable for injury, loss or damage from building or using it, to the extent the law allows.
- **v1.0 is not yet field-validated.** Performance numbers in the spec are design targets and test criteria,
  not guarantees.
- **Anyone who makes, gives away or sells** helmets based on this design is responsible for complying with
  local law. That can include product safety, medical device, radio equipment (Bluetooth), electrical
  safety, consumer protection, privacy and helmet standards.
- Traffic, pedestrian and cycling rules still apply to the wearer.
- This document is general safety information, not medical or legal advice. For mobility decisions,
  consult a qualified O&M instructor. For legal questions, consult a qualified professional in your country.

## 10. Reporting safety problems

- **A near miss, injury, or dangerous behaviour** (for example a missed drop, a false "all clear", a
  module that did not break away): open a [field test report](../../.github/ISSUE_TEMPLATE/field_test_report.yml)
  or bug report and mark it as safety-related. Remove personal details.
- **A security vulnerability** (for example someone can control the helmet over Bluetooth): report it
  **privately**, as described in [SECURITY.md](../../SECURITY.md).
- Changes to alert logic, thresholds or the haptic language always need a safety review
  ([GOVERNANCE.md](../../GOVERNANCE.md)).
