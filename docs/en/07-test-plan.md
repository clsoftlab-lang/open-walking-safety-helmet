# 07 · Test Plan

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This plan expands the verification summary in [spec §11](00-system-design-spec.md#11-verification-plan-summary)
into step-by-step procedures. Each test has an ID (T1–T12), setup, steps, pass criteria and what to record.
The pass criteria come from the spec. Where this plan adds detail (trial counts, tolerances, safety
precautions), it says so. T13–T15 are **proposed additions** for features added to the spec after §11 was
written (safe shutdown, Bluetooth security, power warnings); they are not yet part of spec §11.

Read [06 · Safety](06-safety.md) first. **Never test with real traffic or real dangerous drops.**

## Contents

1. [General rules](#1-general-rules)
2. [Record the build under test](#2-record-the-build-under-test)
3. [Summary](#3-summary)
4. [Procedures T1–T15](#4-procedures-t1t15)
5. [Results table template](#5-results-table-template)
6. [Per-trial log template](#6-per-trial-log-template)
7. [Field test report template](#7-field-test-report-template)

## 1. General rules

- **Safety first.** A sighted spotter accompanies every walking test. Use soft mock obstacles. Stop
  immediately if anyone feels unsafe.
- **Record everything,** including failures and odd behaviour. A failed test with good notes is valuable.
- **Use the helmet log and the phone app log** as the primary timing source. Every alert of level P3 or
  higher is sent to the phone as an `alert` message with a timestamp `ts` (spec §8.1). Keep the
  service log too: `journalctl -u owsh -o short-precise`.
- **Video helps.** A phone filming at 60 fps or more, with floor marks in view, lets you check distances
  and timing afterwards. Get consent before filming people.
- **One change at a time.** If you change configuration between trials, record it and restart the count.
- **Tolerances.** Measure distances with a tape measure to ±2 cm. Mark floor positions with tape.

## 2. Record the build under test

Fill this in once per test session.

```
Date / place:
Tester(s) and roles:
Firmware commit (git rev-parse --short HEAD):
Config file used and differences from default.yaml:
Raspberry Pi model / RAM:           OS image (Bookworm date):
Camera: Camera Module 3 Wide        LiDAR: TF-Luna ×2 (FWD 0x10, DOWN 0x11)
Helmet make / model / size:         Added mass (g):
Measured down-LiDAR tilt (deg):     Pod height above ground when worn (m):
Power bank model / capacity:
Weather / light / temperature:
```

## 3. Summary

| ID | Test | Pass criterion (spec §11) |
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

Proposed additions (this plan, not yet in spec §11):

| ID | Test | Pass criterion (this plan) |
|---|---|---|
| T13 | Safe shutdown: hold B1 + B3 for 5 s | 10/10 clean shutdowns, 10/10 aborts without side effects, no SOS triggered |
| T14 | Bluetooth: non-paired device rejected, safety changes confirmed | no effect from a non-paired device; spoken confirmations, `say` cap and rate limit as spec §8.3 |
| T15 | Power and temperature warnings | under-voltage warning after ≥ 10 s, not repeated within 5 min; overheating warning at ≥ 80 °C |

Recommended order: T1 → T8 → T13 → T14 → T15 → T2 → T3 → T9 → T4 → T5 → T6 → T10 → T7 → T11 (on a separate
helmet) → T12.

## 4. Procedures T1–T15

### T1 · Unit tests

**Purpose.** The pure logic (arbiter, reflex zones, drop-off, tracker/TTC, haptic mixer, protocol,
buttons, fall detection) behaves as specified.

**Setup.** Any PC (Linux, macOS, Windows) with Python 3.11 or 3.12, and the Raspberry Pi itself.

**Steps.**

1. On a PC, from the repository root:
   ```bash
   pip install -e "firmware[dev]"
   cd firmware && python -m pytest -q
   ```
2. On the Raspberry Pi, from the `firmware` folder: `.venv/bin/python -m pytest -q`.
3. For app changes, also run (Node 22): `cd app && node --test tests/*.test.mjs`.

**Pass.** All tests pass on both machines. No skipped safety tests without a written reason.

**Record.** Commit, Python version, number of tests passed, any skips.

---

### T2 · Reflex latency, LiDAR → motor

**Purpose.** The head-height reflex path reacts fast enough (spec §5.1, P5).

**Setup.**

- Helmet running on the bench, forward LiDAR pointing at an empty space more than 3 m deep.
- A flat card (A4 cardboard) to swing into the beam at about 0.4 m.
- The firmware log records the latency directly: lines `reflex zone=… sample_ts=…` and
  `haptic_on … latency_ms=…`. Follow it with `journalctl -u owsh -f -o short-precise`.
- Optional cross-check: a phone filming at 240 fps showing both the card and a motor (a small paper
  flag taped to the pad makes vibration visible).

**Steps.**

1. Swing the card quickly into the beam at 0.4 m and hold it.
2. From the log, read `latency_ms` on the `haptic_on` line for `zone1`. It is measured from the LiDAR sample
   timestamp (`sample_ts`) to the motor output.
3. Cross-check a few trials against the video, if you filmed them.
4. Remove the card, wait 3 s, repeat. Do **20 trials**.

**Pass.** Latency ≤ 60 ms in **every** trial. (The spec gives ≤ 60 ms. This plan applies it to all
20 trials.)

**Record.** Each latency, median and maximum. Note that the 3-sample median filter adds up to one
sample period (20 ms at 50 Hz) by design.

---

### T3 · Vision frame rate on Pi 5

**Purpose.** The detector runs fast enough for approach warnings (spec §5.3).

**Setup.**

- Helmet fully assembled, lid closed, Active Cooler fitted, at room temperature (20–30 °C).
- Default detector NanoDet-Plus-m 416.
- The camera looks at a busy scene (a street through a window, or a walking video on a monitor).
- Phone app connected to read `status` messages (`fps`, `cpu_temp_c`), or the service log.

**Steps.**

1. Start the helmet. Wait 10 minutes to warm up.
2. Record `fps` and `cpu_temp_c` from 30 consecutive `status` messages (5 minutes).
3. Optional: repeat outdoors in direct sun, and record the result separately.

**Pass.** Average FPS ≥ 8 over the 5-minute window.

A detector-only benchmark on a recording is also available: `python -m owsh.tools.bench --video <file>`.
Record it separately; the pass criterion uses the running helmet.

**Record.** Min / mean / max FPS, CPU temperature, `throttled` and `undervoltage` from `status`.

---

### T4 · Head-height obstacle

**Purpose.** Hanging obstacles are warned about in time (spec §5.1).

**Setup.**

- Indoor hall or quiet outdoor area, level floor, at least 6 m of clear space.
- **Branch mock** hung from a stand: a foam pool noodle or a light cardboard board about 60 cm wide,
  lower edge **1.8 m** above the floor. Adjust to the tester's forward-LiDAR height (±5 cm) and record
  the actual heights.
- Floor tape marks at **1.2 m** and **0.6 m** from the obstacle (measured horizontally to the pod's front).
- A **sighted spotter** walks beside the tester, ready to stop them. Sighted testers may wear the helmet
  with eyes open for early trials; record who wore it.
- Phone app log running (alerts carry `dist_m`), and video from the side.

**Steps.**

1. The tester starts 4 m away, facing the obstacle.
2. The tester walks toward it at normal walking speed in natural head posture.
3. The spotter stops the tester at the first `zone1` continuous buzz, or before contact.
4. From video and log, check when `zone2` began and when `zone1` began relative to the floor marks.
5. Repeat for **20 trials**: 10 at normal speed, 10 at slow speed. Vary the obstacle: at least 5 trials
   with a real leafy branch and 5 with a flat sign board.

**Pass (all 20/20).**

- `zone2` begins **before** the pod passes the 1.2 m mark.
- `zone1` begins **before** the pod passes the 0.6 m mark.
- No contact with the obstacle.

**Record.** Per trial: speed, obstacle type, logged `dist_m` at Z2 and Z1 onset, video check, pass/fail.
Also note, **outside the pass count**, results with a thin rope or wire. These are a known limitation.

---

### T5 · Stairs down

**Purpose.** Downward drops are warned about before the edge (spec §5.2).

**Setup.**

- **5 different staircases** (for example concrete outdoor, tiled indoor, dark carpet, metal, a platform
  or kerb edge), each with a level approach of at least 5 m.
- Each staircase tested in **daylight** and at **night or in darkness** (lights off, or evening outdoors).
- Tape mark at the first step edge.
- **Safety:** the spotter holds the tester's arm on the stair side. The tester walks with the cane as usual.
  Stop at the warning; do not descend in the test.

**Steps.**

1. Start 5 m back on level ground. Walk at normal speed for at least 3 s so the ground distance is learned.
2. Walk toward the first step edge.
3. The spotter stops the tester at the `drop` warning, or at 0.5 m before the edge, whichever is first.
4. From video and log, check whether `drop` began before the leading foot reached the edge mark.
5. Do 2 trials per staircase per lighting condition: 5 × 2 × 2 = **20 trials**.

**Pass.** `drop` warning before the first step edge in **at least 19 of 20** trials.

**Record.** Staircase description, surface colour and material, lighting, distance from edge at warning,
false `drop` or `step_up` alarms during the approach (report them in T7 too).

---

### T6 · Approaching bicycle / person

**Purpose.** Moving objects heading for the user are warned about with enough time (spec §5.3).

**Setup.**

- A closed, empty area (empty car park, sports hall), **no traffic**.
- Tester stands still, facing forward, behind a marked line.
- **Approachers:** an experienced cyclist riding at about 10–12 km/h (≈ 3 m/s), and a person walking briskly
  (≈ 1.5 m/s). Both start 15 m away.
- Approach paths: straight ahead, from about 30° left, and from about 30° right.
- A **turn-off marker 2 m** before the tester. The approacher always turns aside there. Foam barrier in front
  of the tester for extra safety.
- Distance markers every 1 m along each path. Video from the side at ≥ 60 fps, synchronised with the app log.

**Steps.**

1. The approacher moves at a steady speed toward the tester along the path.
2. At the moment of the first `approach_*` alert (P1 or P2), read the approacher's position from the video.
3. TTC at alert = remaining distance to the tester ÷ approacher speed (measured from video between markers).
4. Do **20 trials**: 10 bicycle, 10 person, spread across the three directions.

**Pass.** An APPROACH alert with **TTC ≥ 1.5 s** in **at least 18 of 20** trials.

**Record.** Per trial: approacher type, direction, speed, TTC at alert, alert level, whether the reported
side (`left` / `center` / `right`) was correct (recorded, not part of the pass criterion), lighting.

---

### T7 · False alarm rate, city walk

**Purpose.** Warnings are trustworthy in real streets. Too many false alarms make users ignore warnings.

**Setup.**

- A 30-minute route with ordinary pavements, shop fronts, trees, parked cars, a crossing, and some people.
  Daylight, dry weather (repeat later in other conditions as extra data).
- The tester walks with cane or guide dog as usual. A sighted observer walks alongside.
- Chest or head-mounted video, and the app log of all `alert` messages with `level`.

**Steps.**

1. Walk the route at normal pace for 30 minutes.
2. The observer notes the time of any real hazard.
3. Afterwards, review every **P1** alert (`zone1`, `drop`, `approach` P1) against video. Classify each as
   **true** (a real hazard that matches the alert definition) or **false**.
4. Also count false P2 alerts (recorded, not part of the pass criterion).

**Pass.** P1 false alarms ≤ 2 per 10 minutes on average, meaning **≤ 6 in 30 minutes**.
Also report the worst single 10-minute window.

**Record.** Route description, counts of true and false P1 and P2 alerts by type, likely causes
(dark surface, glass, rain, glare …).

---

### T8 · Fault injection

**Purpose.** Failures are announced; silence never means "safe" (spec P4, §5.7).

> **Hardware care.** Do not unplug the camera ribbon while the Pi is powered. It can damage the camera or
> the Pi. Use the power-off method for the camera below. Dupont wires to a LiDAR can be pulled while running,
> but pull only the named wire, carefully.

**Setup.** Helmet on the bench, log visible with precise timestamps, a stopwatch or 60 fps video.
Before touching hardware you can rehearse in the simulator: keys `l` / `k` unplug the forward / down LiDAR,
`c` covers the camera.

**Steps.**

1. **Forward LiDAR:** while running, pull S1's **5 V** Dupont wire. Note the time. Wait for the FAULT
   pattern and voice. Reconnect; check the recovery message. 5 trials.
2. **Down LiDAR:** same with S2. 5 trials.
3. **Camera (power-off method):** power off, disconnect the camera ribbon at the camera end, power on. From
   the log, measure from the moment the camera thread starts to the camera FAULT. 3 trials.
4. **Camera covered:** while running in a lit room, cover the lens with an opaque cap. Time from covering to
   the FAULT. Check that "Distance sensors still active." is spoken and the forward LiDAR still warns. 3 trials.
5. **IMU (optional):** pull the GY-521 VCC wire while running. 3 trials.
6. Check the FAULT pattern repeats every 10 s while a safety-relevant fault lasts (camera, LiDARs, motors, IMU).
7. **Non-safety component (recorded):** start without the face models present (or with Bluetooth disabled).
   Expect a single spoken announcement, no repeating `fault` pattern.

**Pass (spec §11).**

- Camera unplugged: FAULT within **3 s** (the frame timeout is 2 s).
- Lens covered: FAULT within **4 s**.
- LiDAR unplugged: FAULT within **1 s**.
- In every trial.

**Record.** Each measured time, the voice message heard, and whether recovery was announced.

---

### T9 · SOS

**Purpose.** An emergency can be raised by button or by a fall, and reaches the phone (spec §5.6, §7.3).

**Setup.**

- Phone app connected. Emergency number and a guardian contact configured. **Tell the guardian this is a test.**
- For falls: the helmet (with modules) on a **headform or a padded dummy head**, dropped onto a **thick mattress**.
  Do not ask a person to fall.

**Steps.**

1. **Button:** hold □ B3 for 3 s.
   - Expect `sos_countdown` (all motors, 1 Hz) and the voice countdown message.
   - The app shows the countdown.
   - Wait 10 s. Expect "Sending emergency alert to the phone.", then the app alarm and location and the call and
     SMS buttons.
   - "Emergency alert sent." must be spoken **only after** the app's `ack`. Check in the log that the order is
     `sos` sent → `ack` received → "Emergency alert sent.", and that the helmet stops repeating `sos` after the ack.
   - Optional: block the ack (for example close the app right after the countdown). Expect `sos` repeated every 5 s
     and **no** "Emergency alert sent.".
2. **Cancel:** start again, press any button during the countdown. Expect cancellation on the helmet and in the app.
3. **Fall:** drop the dummy head with the helmet from about 1 m onto the mattress. Leave it still.
   - Expect the countdown to start within about 3 s of coming to rest, reason `fall`.
   - Let the alert be sent. Check the app.
4. **Not a fall:** put the helmet down firmly on a table, nod and shake it hard, sit down heavily while
   wearing it. Expect **no** countdown. Record any false trigger.
5. **No phone:** turn Bluetooth off on the phone. Hold B3 3 s and let it run. Expect "Phone not connected"
   every 10 s, the `sos_countdown` pattern continuing for 60 s, and a fast-blinking LED. Press any button: it stops.

Suggested counts (this plan): button 3/3, cancel 3/3, fall 5/5, not-a-fall 10 events, no-phone 1.

**Pass.** Countdown starts, and the phone receives `sos`, in every button and fall trial.

**Record.** Trial results, time from trigger to countdown, any false fall triggers, SMS content received.

---

### T10 · Battery life

**Purpose.** A day of use is possible with the recommended power bank (spec §4.2).

**Setup.**

- A fully charged **20 000 mAh** USB-C PD power bank, the breakaway cable, room temperature 20–25 °C.
- Helmet fully assembled, camera looking at a moving scene, phone app connected.

**Steps.**

1. Connect the power bank and note the start time.
2. Leave the helmet running. Every hour, press □ B3 short (status) and note the result.
3. Note the time the helmet stops.
4. Check for undervoltage during the run: `vcgencmd get_throttled` (via SSH).

**Pass.** Runs continuously for **≥ 6 hours**.

**Record.** Power bank make and model, run time, temperature, throttling, restarts.

---

### T11 · Impact: modules detach or do not penetrate

**Purpose.** The add-ons do not make an impact worse (spec P1, P2).

> **Important.** This is a **visual design check only.** It is **not** a certification test.
> **Never certification-test a modified helmet for sale without an accredited lab.**
> The helmet used for T11 must be **destroyed and never worn** afterwards.

**Setup.**

- A **separate** helmet of the same model, used only for this test.
- **Dummy modules** with the same shape, straps, saddles and Dual Lock, and similar mass (printed parts filled
  with weights), to avoid destroying electronics.
- A headform or firm foam head that fits the helmet.
- A flat, hard surface. Safety glasses for everyone nearby.

**Steps.**

1. Mount the dummy modules exactly as in the assembly guide.
2. Drop the helmet on the headform from **1 m** onto the surface, landing on:
   - front (front pod),
   - rear-top (main case),
   - right side (button module).
3. After each drop, inspect.

**Pass (visual, every drop).**

- No module or fragment has pushed into the shell or the foam liner.
- No sharp fragment is left pointing toward the head or face.
- Modules either detached or stayed attached without denting the shell locally.
- Straps did not cut into the shell.

**Record.** Photos before and after each drop, what detached, any marks on the shell or liner.

---

### T12 · User trials with blind walkers and an O&M instructor

**Purpose.** Learn whether the helmet is useful, understandable and safe for real users.

**Setup.**

- Participants who are blind or have low vision and are experienced cane or guide dog users.
  Suggested 3–5 people per site.
- A qualified **O&M instructor** present at all times.
- **Informed consent** in an accessible format (braille, large print, audio or screen-reader-friendly file).
  If done through a university or hospital, follow its ethics review process.
- Routes: indoor course with mock obstacles → quiet familiar outdoor route → busier route, in that order.
- Stopping rules agreed in advance. Participants may stop at any time without giving a reason.

**Steps.**

1. **Training (30–60 min):** patterns and buttons, using [05 · User guide](05-user-guide.md) and the simulator.
2. **Pattern recall check:** play each vibration pattern in random order; the participant names it. Record accuracy.
3. **Indoor course** with cane or dog as usual, helmet on.
4. **Outdoor routes,** instructor within arm's reach.
5. **SOS practice:** start and cancel.
6. **Interview:** usefulness of each feature, comfort (weight, heat, pads), trust, annoyance from false alarms,
   what should change.

**Pass.** A qualitative report is produced, and **safety incidents = 0**.

Definition used in this plan:

- **Safety incident:** any injury, fall, or contact with an obstacle that causes pain.
- **Near miss** (recorded, reviewed, not counted as an incident): the instructor had to intervene to prevent contact or a fall.

Any incident stops the trial for that participant and triggers a safety review ([GOVERNANCE.md](../../GOVERNANCE.md)).

**Record.** A [field test report](#7-field-test-report-template) per participant or session (anonymised).

---

### T13 · Safe shutdown (proposed, not yet in spec §11)

**Purpose.** The helmet can be switched off without damaging the memory card, and the shutdown gesture never
triggers an SOS or another action by mistake (spec §7.2).

**Setup.** Helmet running on the bench or worn, log visible. Phone app connected, to see any `sos` message.

**Steps.**

1. Press ○ B1 and □ B3 within about 1 s of each other and hold both for 5 s.
   - Expect "Shutting down.", the `ready` pattern reversed (R → C → L), and power-off about 3 s later (LED off).
   - The app must receive no `sos` message, and the last message must not be repeated.
2. Reconnect power and let it boot. It must start normally ("Helmet ready.", ready pattern).
3. Repeat steps 1–2 for **10 trials**.
4. **Abort:** hold both buttons, release B1 after about 2 s. Expect nothing: no shutdown, no SOS, no repeat.
   Repeat releasing B3 instead. 5 trials each.
5. **Start in the wrong order (recorded, not a pass criterion):** hold B3 first and add B1 after 2 s. Note what
   happens. The user guide tells users to press both within about 1 s.
6. In the simulator you can pre-check with key `z` (`python -m owsh --sim`); power-off is only logged there.

**Pass (this plan).** 10/10 clean shutdowns and reboots; 10/10 aborts with no side effects; zero SOS countdowns
started by the gesture.

**Record.** Trial results, time from press to power-off, any SOS or repeat triggered, boot problems.

---

### T14 · Bluetooth: only the paired phone is accepted (proposed, not yet in spec §11)

**Purpose.** Nearby devices cannot mute the helmet, lower its sensitivity or make it speak (spec §8.3).

**Setup.**

- Helmet with default settings (`ble.security: encrypt`, `ble.bonded_only: true`).
- **Phone A:** paired with the helmet, running the app.
- **Phone B:** never paired, running the app or a generic BLE tool that can write to the Nordic UART RX characteristic.
- Log visible (`journalctl -u owsh -f`).

**Steps.**

1. Boot the helmet and wait **more than 120 s** (pairing window closed).
2. From phone B, connect and send `cfg` with `muted: true`, then `dropoff_sensitivity: low`, then `say`.
   - Expect: pairing is refused or no bonding happens; nothing changes on the helmet; no confirmation is spoken;
     the log shows the messages dropped.
3. From phone A (paired), send `cfg` with `muted: true`.
   - Expect "Voice info muted by phone. Warnings are still spoken." spoken even though mute is being switched on.
4. From phone A, set drop-off sensitivity to low: expect "Drop-off sensitivity set to low by phone."
5. From phone A, set volume to 20: expect "Volume set to 20 percent by phone."
6. From phone A, send 5 `say` messages within 3 s. Expect only one to be spoken.
7. While `zone1` is active (target at 0.4 m), send `say` with `level: 0` from phone A. Expect it **not** to
   interrupt "Stop." (capped at P2).
8. **Pairing window:** restart the helmet; within 120 s pair phone B. Expect "New phone paired: <name>."
   Then remove phone B's pairing (`bluetoothctl remove <address>`).
9. Restore phone A's settings (unmute, sensitivity normal, volume).

**Pass (this plan).** Step 2: no change and no speech from phone B in every attempt. Steps 3–8 behave exactly as
expected.

**Record.** Phone models and OS versions, what the phone B pairing dialog showed, log lines for dropped messages.

---

### T15 · Power and temperature warnings (proposed, not yet in spec §11)

**Purpose.** The user is warned about a failing power supply and overheating (spec §5.7).

**Setup.** Helmet on the bench. Phone app connected to read `status` (`undervoltage`, `throttled`,
`cpu_temp_c`). A weak USB power source (for example a 5 V 1 A charger or a long thin cable). A stopwatch.

**Steps.**

1. **Simulator pre-check:** `python -m owsh --sim`, press `v` (under-voltage) and `t` (overheating, 85 °C).
   Expect the two warnings with the timing below.
2. **Normal supply:** run 10 minutes on the recommended power bank. Expect no power warning and
   `undervoltage: false`.
3. **Under-voltage:** switch to the weak supply and create load (press △ B2 repeatedly, camera looking at a busy
   scene). Start the stopwatch when `status` first shows `undervoltage: true`.
   - Expect "Power is low. Charge the battery soon." after **10 s or more** of continuous under-voltage, not before.
   - Keep it running: the warning must not repeat within 5 minutes.
   - If the Pi resets instead, record it. That is useful data about weak supplies.
4. **Overheating (hardware, optional and supervised):** only if you can do it safely, run in a warm room with the
   lid closed while watching `cpu_temp_c`. Expect "Helmet is overheating." at 80 °C or more, at most once per
   5 minutes, and re-armed only after the CPU cools below 75 °C. **Stop at 85 °C.** Never block the cooler
   deliberately on a helmet someone will wear.

**Pass (this plan).** Under-voltage warning after ≥ 10 s and not repeated within 5 min; overheating behaviour as
specified in the simulator (and on hardware if tested); no warnings on the normal supply.

**Record.** Supply used, time to warning, `status` values, any resets.

## 5. Results table template

Copy into your report. One row per test.

| ID | Date | Firmware commit | Tester(s) | Conditions | Trials / measure | Result | Pass? | Notes / evidence |
|---|---|---|---|---|---|---|---|---|
| T1 | | | | PC + Pi | tests | __ passed / __ | ☐ | |
| T2 | | | | bench | 20 | max __ ms, median __ ms | ☐ | |
| T3 | | | | room __ °C | 5 min | mean __ FPS | ☐ | |
| T4 | | | | branch h = __ m | 20 | __ / 20 | ☐ | |
| T5 | | | | 5 stairs, day + night | 20 | __ / 20 | ☐ | |
| T6 | | | | bicycle 10, person 10 | 20 | __ / 20 | ☐ | |
| T7 | | | | route __ | 30 min | __ false P1 (worst 10 min: __) | ☐ | |
| T8 | | | | bench | LiDAR 10, camera 3 + 3 | LiDAR max __ s, unplug __ s, covered __ s | ☐ | |
| T9 | | | | button, fall, no phone | see T9 | __ | ☐ | |
| T10 | | | | 20 000 mAh, __ °C | 1 | __ h __ min | ☐ | |
| T11 | | | | dummy modules | 3 drops | __ | ☐ | |
| T12 | | | | __ participants | sessions | incidents __, near misses __ | ☐ | |
| T13 (proposed) | | | | bench / worn | 10 + 10 | __ / 10 shutdowns, __ / 10 aborts, SOS __ | ☐ | |
| T14 (proposed) | | | | phone A __, phone B __ | steps 2–8 | __ | ☐ | |
| T15 (proposed) | | | | supply __ | 1 | warning after __ s; repeat __ | ☐ | |

## 6. Per-trial log template

For T4, T5 and T6.

| Trial | Time | Condition (speed / stair / approacher / direction / light) | Key measurement (dist at Z2, Z1 / dist at drop / TTC) | Alert level | Pass? | Notes |
|---|---|---|---|---|---|---|
| 1 | | | | | ☐ | |
| 2 | | | | | ☐ | |
| … | | | | | ☐ | |

## 7. Field test report template

Use this for real-world walks and user trials. You can also submit it on GitHub with the
[field test report form](../../.github/ISSUE_TEMPLATE/field_test_report.yml).
**Remove names, faces and exact home locations.**

```markdown
## Field test report

### Build
- Firmware commit:
- Hardware changes from the reference design:
- Config changes from default.yaml:
- Helmet model / size:

### Session
- Date, country / city (no exact addresses):
- Environment: indoor / quiet street / busy street / station / park / other
- Light: daylight / dusk / night · Weather: dry / light rain / heavy rain / fog / snow · Temperature:
- Duration (min) and approximate distance:

### People
- Wearer: blind / low vision / sighted tester · Cane / guide dog / none
- Years of independent travel experience (optional):
- O&M instructor present: yes / no

### What worked
-

### Missed hazards (the helmet stayed silent when it should have warned)
- What, where, lighting, surface:

### False alarms
- Pattern / message, what was actually there:

### Faults
- Message heard, what caused it, did it recover:

### Comfort and usability
- Weight, heat, pad positions, buttons, voice volume, learning the patterns:

### Safety incidents and near misses
- Incidents (injury, fall, painful contact): none / describe
- Near misses:

### Suggestions
-

### Consent
- [ ] Everyone identifiable in attached media agreed to share it.
```
