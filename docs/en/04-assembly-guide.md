# 04 · Assembly Guide

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This guide takes you from a box of parts to a tested helmet. Plan for one or two days, not counting printing.

Read [06 · Safety](06-safety.md) before you start. The two most important rules:

1. **Never drill, cut, glue into or melt the helmet shell or its foam liner.** Everything attaches with
   straps through the vents and removable pads.
2. **The helmet assists. It never replaces the white cane, a guide dog or O&M training.**

## Contents

- [Part A — Preparation](#part-a--preparation)
- [Part B — Software setup](#part-b--software-setup)
- [Part C — Bench wiring and first checks](#part-c--bench-wiring-and-first-checks)
- [Part D — Building the modules](#part-d--building-the-modules)
- [Part E — Mounting on the helmet without drilling](#part-e--mounting-on-the-helmet-without-drilling)
- [Part F — Pairing the phone](#part-f--pairing-the-phone)
- [Part G — First boot test checklist](#part-g--first-boot-test-checklist)
- [Part H — Calibration](#part-h--calibration)
- [Part I — Before the first real walk](#part-i--before-the-first-real-walk)
- [Switching off and looking after the memory card](#switching-off-and-looking-after-the-memory-card)

---

## Part A — Preparation

- [ ] All parts from [01 · Bill of materials](01-bill-of-materials.md), including the W3 splitter and W4 USB extension.
- [ ] All printed parts from [03 · 3D printing guide](03-3d-printing-guide.md), cleaned and test-fitted, with the
      curved parts rendered for **your** helmet's measured radii.
- [ ] A computer with a microSD card reader and [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
- [ ] Wi-Fi for setup (only needed to install software; the helmet works offline afterwards).
- [ ] An Android phone with Chrome (or an iPhone with the Bluefy browser) for the phone app.
- [ ] A kitchen scale. **Weigh the empty helmet now** and write the value down.
- [ ] Mild soap, water and a cloth to clean the helmet shell.

## Part B — Software setup

### B1. Flash Raspberry Pi OS Bookworm 64-bit

1. Insert the microSD card into your computer and open Raspberry Pi Imager.
2. **Device:** Raspberry Pi 5.
3. **Operating system:** *Raspberry Pi OS (64-bit)* based on **Debian 12 "Bookworm"**.
   If Imager's default is a newer release, open *Raspberry Pi OS (other)* and choose the Bookworm
   64-bit (Legacy) image. Firmware v1.0 is built and tested for Bookworm.
4. **Storage:** your microSD card.
5. **Edit settings** (OS customisation):
   - Hostname, for example `owsh-01`.
   - User name and a strong password. Write them down for the owner.
   - Wi-Fi network and country.
   - Time zone and keyboard layout.
   - Services: enable **SSH** (password or key).
6. Write the card, then put it in the Pi.

### B2. First start and update

1. Connect the Pi to a normal USB-C power supply (5 V 3 A or the official 27 W supply) for setup.
2. Wait 1–2 minutes, then connect from your computer: `ssh <user>@owsh-01.local`.
3. Update the system:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo reboot
   ```

### B3. Install the firmware

1. Get the project and go to the `firmware` folder:
   ```bash
   sudo apt install -y git
   git clone <repository-url> owsh
   cd owsh/firmware
   ```
   Use the repository URL shown on the project's GitHub page.
2. Run the setup script **as your normal user** (not with `sudo`; it asks for your password when needed):
   ```bash
   bash scripts/setup_pi.sh          # add --ocr to also install text reading
   ```
   The script:
   - installs system packages (camera, GPIO, `espeak-ng`, `i2c-tools`, `bluez`, `bluez-tools`);
   - turns on I2C at 400 kHz and the camera in `config.txt`;
   - creates the virtual environment `firmware/.venv` and installs the firmware;
   - downloads the AI models and runs the self-tests;
   - installs and enables two services: **`owsh`** (the helmet firmware) and **`owsh-bt-agent`** (the
     Bluetooth pairing agent);
   - allows the helmet's safe-shutdown gesture to power off the Pi.
3. Reboot: `sudo reboot`.
4. Check the services:
   ```bash
   systemctl status owsh owsh-bt-agent
   journalctl -u owsh -f
   ```
   Without sensors connected you will see FAULT messages. That is expected and correct (spec P4):
   a missing sensor must never look like "all clear".

In this guide, firmware tools run from the `firmware` folder with the virtual environment's Python:
`.venv/bin/python -m owsh.tools.<tool>`.

**Text reading (OCR)** is optional (spec §5.5). If you did not use `--ocr`, pressing ○ says
"Text reading is not installed". To add it later: `.venv/bin/pip install -e ".[ocr]"`, then
`sudo systemctl restart owsh`.

**Try the simulator first (optional).** On any PC with a webcam you can run
`python -m owsh --sim` to learn the haptic patterns and buttons before the hardware is ready
(see [`firmware/README.md`](../../firmware/README.md)).

## Part C — Bench wiring and first checks

1. Power off. Wire everything on the table following [02 · Wiring guide](02-wiring-guide.md).
2. Change the down-looking TF-Luna's address to 0x11 ([wiring guide section 6](02-wiring-guide.md#6-tf-luna-i2c-mode-and-address-change)).
3. Pass all checks in [wiring guide section 7](02-wiring-guide.md#7-checks):
   `i2cdetect -y 1` shows `10`, `11`, `68`; the camera is listed; buttons read `hi`/`lo`; motors buzz
   left → centre → right at boot.

**Do not continue until the bench build passes every check.** Faults are far easier to find on a
table than inside a closed case on a helmet.

## Part D — Building the modules

Power off before each step. Screw sizes are listed in [`hardware/README.md`](../../hardware/README.md).
For self-tapping holes, drive each screw in once, back it out, then assemble.

### D1. Front sensor pod (`front_pod_base`, `front_pod_cover`)

1. Mount the **Camera Module 3 Wide** in the camera bay with 4 × M2 × 5 screws. The lens looks
   through the window, 10° down. Do not overtighten: the board can crack.
2. Connect the 15-pin end of the camera cable before closing anything.
3. Place **S1 (forward TF-Luna)** in the forward bay, lens facing forward (2 × M2 × 5).
4. Place **S2 (down TF-Luna, labelled 0x11)** in the 50° facet, lens facing down and forward (2 × M2 × 5).
5. **Do not cover the lenses.** Check from the front: both TF-Luna apertures and the camera lens are
   completely clear, and the rain visor does not hang into their view.
6. Route the camera ribbon and the two TF-Luna cables out through the cable exits in the rear wall.
7. Close `front_pod_cover` (4 × M2 × 8).
8. Clean the lenses with a microfibre cloth.

### D2. Main case (`main_case_base`, `main_case_lid`)

The main case holds only the **Pi 5 with Active Cooler, the MPU-6050 and the status LED**.

1. Fit the **Active Cooler** to the Pi 5 (follow the instructions in its box).
2. Mount the Pi on the standoffs with 4 × M2.5 × 6 screws. The USB-C power socket, the USB-A ports and the
   cooler exhaust must line up with their openings.
3. Slide the **MPU-6050** into its slot. Mount it firmly. Its orientation does not matter for fall detection
   (it uses total acceleration), but a loose IMU rattles and can look like an impact.
4. Press the 3 mm status LED into the lid from inside.
5. Connect the camera ribbon's 22-pin end to **CAM/DISP 0**.
6. Connect the Dupont wires as in the bench build. Keep the splitters wrapped. The wires to the ULN2003
   (IN1–IN3, 5 V, GND) leave the case toward the aux pod.
7. Plug the **W4 USB-A extension** into a black USB 2.0 port. Its socket end leaves through the rear opening.
8. Close the lid (4 × M2.5 × 8). No wire may be pinched. The cooler fan must spin freely; it has only about
   1.2 mm clearance to the lid.

### D3. Aux pod (`aux_pod_base`, `aux_pod_lid`)

The aux pod on the back of the head holds the **ULN2003 driver** and the **USB audio adapter**.

1. Put the ULN2003 board in its cradle. Connect IN1/IN2/IN3 (GPIO17/27/22), "+" (5 V) and "−" (GND) from the
   main case wires.
2. Connect the three motor leads to the ULN2003 as in the wiring guide. The motor leads leave through the
   **lower notch** toward the comfort pads.
3. Plug the USB audio adapter onto the W4 extension and slide it onto its rails. The headset jacks face the
   jack opening.
4. Close the lid (4 × M2.5 × 8).

### D4. Button module (`button_module`, `button_caps`)

1. Insert the three 12 mm switches.
2. Press on the caps in this order, from **front to back**: **○ circle, 1 dot (B1)**, **△ triangle, 2 dots (B2)**,
   **□ square, 3 dots (B3)**.
3. Connect the wires: B1 → GPIO5 (pin 29), B2 → GPIO6 (pin 31), B3 → GPIO26 (pin 37), each with its GND.
   Button modules, if used, get **3.3 V only**.
4. Check again by touch with your eyes closed: circle front, triangle middle, square rear.

### D5. Haptic pads (`haptic_pad` × 3)

1. Slide one coin motor into each TPU pad from the side. The skin membrane faces the head.
2. Stick a piece of the **hook** side of hook-and-loop into the recess.
3. Label the pads: **L** (M1), **C** (M2), **R** (M3).

## Part E — Mounting on the helmet without drilling

> **Rules for every step:**
> - No drilling, cutting, gluing into, heating or melting the shell or the foam liner.
> - Only straps through existing vents, removable Dual Lock pads on the **outer** shell surface,
>   and hook-and-loop on the **comfort padding**. Never replace straps with screws, zip ties or glue.
> - Height above the shell: front pod ≤ **35 mm**, main case ≤ **40 mm**, every other module ≤ **30 mm**.
>   All outside edges rounded. No stilts or gaps larger than 5 mm under a module.

### Where each module goes

| Module | Position |
|---|---|
| Front sensor pod | Front-top, centred, above the forehead |
| Main case | Top of the head, behind the crown, long side front-to-back |
| Aux pod | Back of the head, below the main case |
| Button module | Right side, above the ear, near the lower rim |
| Haptic pads | Inside, on the comfort pads: left temple, forehead centre, right temple |

### E1. Clean the shell

Wash the mounting areas with mild soap and water, then dry completely. **Do not use solvents** such as
acetone or strong alcohol: many helmet makers warn they can weaken the shell. Dual Lock sticks best above
15 °C and reaches full strength after about 24–72 hours.

### E2. Saddles

Each of the three large modules sits on its own 3 mm TPU saddle from the `saddle_pad` plate (pod, case, aux).

1. Put Dual Lock on **both faces** of each saddle (or hook-and-loop).
2. The saddle **only rests** on the shell and bends to its shape. Never glue it to the shell.

### E3. Front sensor pod

1. Press the pod onto its saddle.
2. Place it on the shell, centred left-to-right above the forehead. Look from the side: the forward LiDAR
   should be roughly horizontal when the helmet sits on a head in normal posture.
3. Thread **two 20 mm straps**: down through a strap tab slot, through a helmet vent, and back up. Close them
   **snug, not tight**.
4. Inside the helmet, each strap must lie **flat** against the liner with no twist or buckle on the head side.
   The comfort padding covers it.
5. Check the gap between the saddle and the shell at the pod's ends. If there is a gap larger than a few mm, the
   pod was rendered for a different radius. Re-measure and reprint.

### E4. Main case

Same method: saddle + Dual Lock + **two straps through vents**, on top of the head behind the crown, long side
front-to-back. The USB-C opening and cooler exhaust must not be blocked by a strap or the shell.

### E5. Aux pod

1. Saddle + Dual Lock + straps through the vents at the back of the head, below the main case.
2. Route the **W4 USB extension** and the ULN2003 wires from the main case's rear opening to the aux pod in a short,
   tidy loop. Hold them with `cable_clip`s. They must not hang free where a hand or branch could catch them.
3. The headset cable leaves the aux pod's jack opening and goes to the headset around the side of the helmet,
   not across the face.

### E6. Button module

1. Fix a `strap_anchor` through a side vent with a short strap.
2. Attach the button module with Dual Lock and its angled strap tabs.
3. Check with the user: they should find ○ at the front without searching, with the right hand.
4. The module must not press on the ear or catch on glasses or a hat.

### E7. Haptic pads

1. Put the **loop** side of hook-and-loop on the helmet's removable comfort pads: **left temple**,
   **forehead centre**, **right temple**. Most comfort pads are already a loop fabric that hook tape grips.
2. Press the pads on. Never glue them to the foam liner.
3. Let the user put the helmet on. Adjust the pad positions until each one is felt clearly and
   separately. Hair, headscarves and caps weaken vibration. Move the pads rather than increasing power.

### E8. Cable routing

1. Run the camera ribbon from the front pod to the main case inside `fpc_cover`, along the shell
   centre line, under the straps. Hold it with `cable_clip`s.
2. Bundle the TF-Luna and button Dupont wires along the same path. Twist each I2C line with a ground wire.
3. Motor leads go from the aux pod's lower notch through a vent to the inside. Route them along the edge of
   the liner, under the comfort padding, so they never touch the skin.
4. Leave small loops of slack at each module. A pulled cable must not pull a connector out.
5. Nothing may hang in front of the face, cross the ears, or pass under the chin strap.

### E9. Breakaway power cable

The power bank rides in a pocket or waist bag. The cable must never be able to catch around the neck.

1. Plug the **magnetic breakaway adapter** into the Pi's USB-C socket (or put it at the point where
   the cable leaves the helmet).
2. Route the 1.5 m cable from the rear of the helmet down the back to the pocket or waist bag.
3. **Pull test:** with the helmet on a table, pull the cable sharply. The magnetic joint must separate
   before the helmet moves. If the helmet slides instead, the adapter holds too hard. Replace it.
4. Never wrap the cable around the neck or through clothing in a way that could tighten.

### E10. Final mechanical checks

- [ ] **Height above the shell** (calipers at the highest point): front pod ≤ 35 mm, main case ≤ 40 mm,
      aux pod, button module and everything else ≤ 30 mm.
- [ ] **No gap larger than 5 mm** between any module's saddle and the shell.
- [ ] **Mass:** weigh the helmet again. Added mass without power bank and without rain gutter is **≤ 380 g**
      (expected about 330 g).
- [ ] **Balance:** the helmet does not tip forward or back on the head when the user nods.
- [ ] **Fit:** the helmet still sits level and the chin strap and fit dial adjust normally.
- [ ] **No drilling, cutting or glue** in the shell or liner. Check this again.
- [ ] **Edges:** run a hand over every module. No sharp corners, points or loose wire ends.
- [ ] **Ventilation:** at least some vents stay open.
- [ ] **Certification label** inside the helmet is still readable.

## Part F — Pairing the phone

The helmet only accepts commands from a **paired (bonded) phone**, over an encrypted link (spec §8.3).
Otherwise anyone nearby could mute it or lower the drop-off sensitivity.

1. Open the phone app over HTTPS in Chrome on Android, or in the Bluefy browser on iPhone
   (see [`app/README.md`](../../app/README.md)).
2. Switch the helmet on. While **no phone is paired yet**, pairing is always open. Once a phone is paired,
   pairing is open only for the **first 2 minutes after each start**.
3. In the app tap **Connect** and choose `OWSH-XXXX`.
4. When the app first sends a command, the phone shows its normal system dialog, for example
   **"Pair with OWSH-XXXX?"**. There is no PIN, because the helmet has no screen or keypad. Tap **Pair**.
   Screen readers read this dialog aloud.
5. The helmet says **"New phone paired: <phone name>."** Later connections are automatic.
6. **To add or replace a phone,** restart the helmet and pair within 2 minutes.
7. **To remove all pairings,** on the Pi run `bluetoothctl devices Paired`, then
   `bluetoothctl remove <address>` for each device.

Tell the user: if the helmet ever says "New phone paired" when they did not pair a phone, someone else paired.
Remove the pairings and restart the helmet.

## Part G — First boot test checklist

Do this indoors, in a safe room, with a sighted helper. Watch the log from a laptop:
`journalctl -u owsh -f`. Tick each item. Voice messages are quoted from the English phrase file
(`firmware/owsh/i18n/en.json`).

### G1. Start-up

- [ ] Connect the power bank. The status LED lights.
- [ ] Within about a minute the headset says "Helmet ready." and "This helmet only assists. Keep using your
      cane or guide dog."
- [ ] **Ready pattern:** a quick sweep **left → forehead → right** (100 ms each).
- [ ] No FAULT pattern (three very quick forehead buzzes) follows. If it does, check the log.

### G2. Buttons (every accepted press gives a short `tick` on the forehead)

- [ ] ○ B1 short (under 0.8 s): tick, then text reading (or "Text reading is not installed.").
- [ ] ○ B1 long (1.5 s or more): tick, the last message is repeated.
- [ ] A press between about 0.8 s and 1.5 s is ignored.
- [ ] △ B2 short: tick, scene description.
- [ ] △ B2 long: tick, "where am I" (needs the phone app connected).
- [ ] △ B2 double: tick, who is here (faces).
- [ ] □ B3 short: tick, status report.
- [ ] □ B3 double: tick, "Voice info muted. Warnings are still spoken." Then press △ B2 short: the scene
      description is **still spoken**, because it answers your own button press. Double-press □ again to unmute.
- [ ] □ B3 hold 3 s: the SOS countdown starts while you are still holding (all three motors pulse once per
      second, voice warns). **Press any button to cancel.** Check it cancels. Do the full SOS test later
      ([07 · Test plan](07-test-plan.md) T9).

### G3. Safe shutdown

- [ ] Press ○ B1 and □ B3 **together** (within about 1 s of each other) and hold both for **5 s**.
- [ ] The helmet says "Shutting down.", the ready pattern runs in reverse (**right → forehead → left**), and the
      Pi powers off about 3 s later. The status LED goes out.
- [ ] No SOS countdown started and the last message was not repeated.
- [ ] Switch on again (unplug and replug the power). Now hold both buttons and **let go of one after about 2 s**:
      nothing happens (the shutdown is cancelled, no SOS).

### G4. Forward LiDAR zones (use your hand or a book)

The forward beam is narrow (2°): about 7 cm wide at 2 m. Hold the target straight ahead of the pod,
at head height. A book or a board is easier to hit than a hand.

- [ ] Target at about **1.8 m**: slow, gentle forehead pulses (`zone3`). No voice.
- [ ] Target at about **1.0 m**: fast pulses (`zone2`) and "Obstacle ahead."
- [ ] Target at about **0.4 m**: continuous strong buzz (`zone1`) and "Stop."
- [ ] Move the target to about **10 cm** (closer than the sensor can measure): the `zone1` buzz continues for
      about half a second, then stops.
- [ ] Move the target away: the buzzing stops.

### G5. Drop-off at a table edge

The down-looking LiDAR compares the ground distance with a learned value. For safety it **never learns a
longer distance by itself**, and it re-learns a **shorter** stable distance only after 10 seconds.

1. A helper holds the helmet level, about **1 m above a table top**, so the down beam hits the table
   about 80 cm ahead of the helmet. A "Step up ahead." warning at the start is expected: the table is closer
   than the default ground distance.
2. Hold still for **at least 12 seconds** so the shorter table distance is learned.
3. Slowly move the helmet forward so the beam spot crosses the table edge and lands on the floor.
- [ ] **Drop pattern:** two long buzzes on all three motors, and "Step down ahead." or "Drop ahead."
- [ ] Wait 3 s (cooldown), move back over the table, then slide a box about 40 cm tall under the beam:
      three short forehead pulses and "Step up ahead."

### G6. Fault by covering the camera

1. In a normally lit room, cover the camera lens completely with an opaque cap or tape.
- [ ] Within **4 seconds**: FAULT pattern (three very quick forehead buzzes), "Camera is covered or too dark.",
      and "Distance sensors still active."
- [ ] While still covered, repeat G4 at 1.0 m: the LiDAR warning still works.
- [ ] The FAULT pattern repeats every 10 seconds.
2. Uncover the lens.
- [ ] Voice says "Camera view recovered." FAULT stops.

### G7. Phone app and settings confirmations

- [ ] The app connects to `OWSH-XXXX` without a new pairing dialog (already paired in part F).
- [ ] The app shows status (uptime, temperature, faults).
- [ ] △ B2 long press: the helmet speaks the location from the phone.
- [ ] The app's log shows what the helmet said.
- [ ] Mute the helmet from the app: the helmet says "Voice info muted by phone. Warnings are still spoken."
      Unmute again.
- [ ] Set drop-off sensitivity to low in the app: "Drop-off sensitivity set to low by phone." Set it back to normal.
- [ ] Set the volume to 20 %: "Volume set to 20 percent by phone." Set it back.

### G8. Power and temperature

- [ ] With the normal power bank, no "Power is low. Charge the battery soon." message appears in 10 minutes of use.
      If it does, the power bank or cable cannot deliver 5 V 3 A. Replace it before walking.
- [ ] Optional check that the warning works: with the helmet running, power it for a minute from a weak USB supply
      (for example a 5 V 1 A charger) while pressing △ B2 a few times. After about 10 s of under-voltage you should
      hear "Power is low. Charge the battery soon." and the app status shows under-voltage. Switch back to the
      proper power bank.
- [ ] After 15 minutes of running with the lids closed, the app shows a CPU temperature below 80 °C in room
      conditions, and "Helmet is overheating." has not been spoken.

If any item fails, fix it before going outside. Common causes are in the
[wiring guide's common mistakes](02-wiring-guide.md#8-common-mistakes).

## Part H — Calibration

Calibrate **with the actual user wearing the helmet**, in their natural walking posture. Many people
walk with the head slightly lowered, and that changes where the sensors look.

### Where settings live

All thresholds are in `firmware/config/default.yaml`. The `owsh` service starts the firmware with that file
(see `/etc/systemd/system/owsh.service`). To keep personal changes safe from updates, copy it (for example
to `config/my.yaml`), change `--config` in the service file to the copy, then run
`sudo systemctl daemon-reload && sudo systemctl restart owsh`. Running `setup_pi.sh` again rewrites the
service file, so repeat this step afterwards.

### H1. Forward LiDAR aim

1. The user stands in normal posture, facing a flat wall, **1.5 m** away (measure from the forehead).
2. Expected: `zone3` slow pulses. At 1.0 m: `zone2`. At 0.5 m: `zone1`.
3. If the zones come early, late or not at all, the beam probably points up or down. At 2 m, a
   tilt of 5° moves the beam spot about 17 cm. Check `mount_pitch_deg` and the pod's seat on its saddle.
4. Zone distances are config values (spec §5.1). Change them only with good reason, and record why.

### H2. Down-looking LiDAR tilt and height

1. With the helmet on the user's head in normal posture, a helper holds a phone inclinometer against
   the down-LiDAR facet of the pod.
2. The spec value is **50° below horizontal**. If you measure a different angle, set
   `dropoff.tilt_deg` to the measured value.
3. Measure the height of the pod above the ground when worn, and set `dropoff.sensor_height_m`
   (default 1.7 m). The firmware starts from this value. Because it **never automatically learns a longer ground
   distance** (spec §5.2 safety rule), a correct starting height matters, especially for tall users.
4. Walk slowly toward a known kerb or the top of a staircase **with a sighted helper holding the user's
   arm**. The drop warning must come before the edge.

### H3. Drop-off sensitivity

- Default: no-return (for example, very dark or wet ground) is treated as a DROP. A missed drop is worse
  than a false alarm.
- If false drop alarms on dark surfaces are too frequent, the phone app can set drop-off sensitivity
  to `low`, or the config can set `dropoff.no_return_is_drop: false`. The helmet always confirms a low setting by
  voice. **Explain the trade-off to the user and their O&M instructor before changing it.**

### H4. Camera view

With the service stopped, take a picture: `rpicam-still -o view.jpg`. A person standing 3 m ahead should
be fully in the picture, and the ground should fill roughly the lower third. If not, check the pod angle.

### H5. Vibration and voice

- Each pad must be felt clearly. If not, move the pad. **Do not raise `haptics.max_duty` above 75 %.**
  The motors are 3 V parts.
- Set voice volume and language in the phone app. Voice must be clear over street noise but must not
  hide traffic sounds.
- Teach the user the patterns with [05 · User guide](05-user-guide.md) and the simulator.

### H6. Phone app, emergency number, guardians

In the app: choose the **country emergency number** (for example 112, 119 or 911), add guardian phone
numbers, and test sending an SMS to a guardian who knows it is a test.

### H7. Enrolling faces (optional)

Only enrol people who have **agreed** to it. Stop the service first (the camera is in use), then, from the
`firmware` folder:

```bash
sudo systemctl stop owsh
.venv/bin/python -m owsh.tools.enroll_face --name "Mina" --tag friend --camera 0
sudo systemctl start owsh
```

Use `--tag avoid` for a person the user wants to be warned about. Photos and face data stay on the
helmet (spec §5.4). To see who is enrolled, use `--list`. To delete a person, use `--remove "Mina"`.

## Part I — Before the first real walk

1. Run the procedures in [07 · Test plan](07-test-plan.md), at least T2, T4, T5, T8, T9, T13 and T14.
2. The first outdoor walks are done **with the white cane or guide dog as usual**, with an O&M instructor
   or a trusted sighted companion walking alongside.
3. Start in familiar, quiet places. Build up slowly.
4. Record what went well and what did not in a [field test report](../../.github/ISSUE_TEMPLATE/field_test_report.yml).

## Switching off and looking after the memory card

- **Switch off with the safe shutdown:** hold ○ B1 and □ B3 together for 5 seconds. Wait until the LED goes out,
  then unplug the power.
- Removing power without a clean shutdown can, rarely, damage the microSD card. Teach the user the safe shutdown.
- Use a good A2 card, and **keep a backup image** of the working card (for example with Raspberry Pi
  Imager or `dd`) so the helmet can be restored in minutes.
- An NVMe drive on an M.2 HAT is more robust than microSD.

Next: [05 · User guide](05-user-guide.md)
