# OWSH firmware

Firmware for the **Open Walking Safety Helmet**. It warns blind and low-vision walkers about
head-height obstacles, drop-offs and approaching objects. It can also read text, recognise enrolled
faces and send an SOS through a phone.

> **The helmet assists and never replaces the white cane or guide dog.**
> The authoritative design is [`../docs/en/00-system-design-spec.md`](../docs/en/00-system-design-spec.md).
> This firmware implements spec v1.0.

Licence: Apache-2.0 · Author: CLSOFTLAB, Dr. Lee Il-guk

---

## Quick start on a PC (simulator)

Requires Python ≥ 3.11 and a webcam or a video file.

```bash
cd firmware
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m owsh.tools.download_models              # NanoDet, YuNet, SFace -> models/
python -m owsh --sim                              # webcam 0 + dashboard window
python -m owsh --sim --video path/to/walk.mp4     # a video instead of the webcam
python -m owsh --sim --lang ko                    # Korean voice
```

In `--sim` mode the LiDARs and the IMU are simulated and controlled from the dashboard. The
motors are drawn as bars and the buttons are keys. Speech uses `pyttsx3`, or `--tts print` to
print the text instead.

Headless runs are useful for CI or for checking detection on a recording:

```bash
curl -L -o samples/vtest.avi https://github.com/opencv/opencv/raw/4.x/samples/data/vtest.avi
python -m owsh --sim --video samples/vtest.avi --no-window --frames 300 --tts print \
       --save-frames samples/out --save-every 100
python -m owsh.tools.bench --video samples/vtest.avi       # detector FPS
```

### Keyboard map (dashboard window)

| Key | Action |
|---|---|
| `1` / `2` / `3` | short press B1 ○ / B2 △ / B3 □ |
| `Shift+1..3` or `q` / `w` / `e` | long press (B3 long = hold 3 s = SOS countdown) |
| `a` / `s` / `d` | double press |
| trackbars `forward cm`, `down cm` | simulated LiDAR distances (0 = no return) |
| `f` | simulate a fall |
| `l` / `k` | unplug / replug forward / down LiDAR (fault injection) |
| `c` | cover / uncover the camera (black frames → `camera_blocked`) |
| `z` | hold B1 + B3 for 5 s → safe shutdown (in simulation the power-off is only logged) |
| `v` / `t` | toggle simulated Pi under-voltage / overheating (85 °C) |
| `Esc` or `x` | quit |

What the buttons do (spec §7.2):

| Button | Short (< 0.8 s) | Long (≥ 1.5 s) | Double (< 0.4 s gap) |
|---|---|---|---|
| B1 ○ | read text (OCR) | repeat last message | — |
| B2 △ | describe scene | where am I (phone location) | who is here (faces) |
| B3 □ | status report | hold 3 s: SOS countdown | toggle voice mute (P3–P4) |

Every press vibrates `tick`. Any button cancels a running SOS countdown.

**Safe shutdown: hold B1 ○ and B3 □ together for 5 seconds.** The helmet says "Shutting down",
vibrates the start-up pattern in reverse (right → centre → left) and powers off 3 s later. As soon
as both buttons are down, their normal long presses are blocked, so this can never start an SOS.
Press both within about 1 s of each other (B1 alone held 1.5 s would already repeat the last
message). Letting go of either button before 5 s cancels the shutdown without doing anything else.

### Power warnings (Raspberry Pi)

Every 5 s the firmware reads the Pi's `get_throttled` flags and the CPU temperature:

- under-voltage for 10 s or longer → "Power is low. Charge the battery soon." (P2), repeated at
  most every 5 minutes while it lasts;
- CPU at 80 °C or hotter → "Helmet is overheating." (P2), repeated at most every 5 minutes, re-armed
  once the CPU cools below 75 °C.

The phone's `status` message carries `undervoltage` and `throttled` (current state, omitted when
unknown).

## On the Raspberry Pi 5

Use Raspberry Pi OS Bookworm 64-bit with the hardware wired per spec §4.2.

```bash
git clone <this repository> && cd <repo>/firmware
bash scripts/setup_pi.sh            # apt packages, I2C, venv, pip install -e .[pi,ble], models, systemd
sudo reboot
i2cdetect -y 1                      # expect 0x10 (TF-Luna) and 0x68 (MPU-6050)
.venv/bin/python -m owsh.tools.tfluna_addr --from 0x10 --to 0x11   # once, only the DOWN sensor connected
sudo systemctl start owsh && journalctl -u owsh -f
```

The service restarts automatically (`Restart=always`, `RestartSec=2`). Optional parts degrade
gracefully. A missing LiDAR, IMU, camera, GPIO, audio backend or Bluetooth stack produces a
spoken and vibrated **FAULT**, never a crash. Silence must never mean "safe".

### Pairing the phone (Bluetooth security)

The helmet only takes commands from a **paired (bonded) phone**, and the link is encrypted.
Otherwise anyone nearby could mute it or lower the drop-off sensitivity.

1. Switch the helmet on. While no phone is paired yet, pairing is always open. Once a phone is
   paired, pairing is open only for the first **2 minutes after each start**, so to add or replace
   a phone, restart the helmet (or hold B1 + B3 for 5 s and switch it on again).
2. In the phone app tap "Connect" and choose `OWSH-XXXX`.
3. When the app first sends a command, Android shows its normal system dialog, **"Pair with
   OWSH-XXXX?"**, with *Pair* and *Cancel* buttons. There is no PIN, because the helmet has no
   screen or keypad. Tap *Pair*. The phone stores the pairing, so later connections are automatic.
   iOS shows a similar "Bluetooth Pairing Request" alert. A screen reader reads the dialog aloud.
4. The helmet announces **"New phone paired: <phone name>."** If you hear this and did not pair
   a phone yourself, remove the pairing (see below) and restart the helmet.

On the Pi, `scripts/setup_pi.sh` installs `bluez-tools` and runs `bt-agent` with the
NoInputNoOutput capability (`owsh-bt-agent.service`). This agent accepts the Just Works pairing,
and the firmware decides when BlueZ is pairable. To remove all pairings, run
`bluetoothctl devices Paired`, then `bluetoothctl remove <address>`.

Settings the phone sends that reduce safety are always announced on the helmet: "Voice info
muted by phone", "Drop-off sensitivity set to low by phone", and "Volume set to N percent by
phone" (below 30 %). The phone's "say" messages are capped at P2 and limited to one every 3 s.
Configuration keys: `ble.security` (`encrypt`), `ble.bonded_only` (`true`),
`ble.pairing_window_s` (120), `ble.say_min_interval_s` (3), `ble.confirm_volume_below` (30).

Other tools:

```bash
python -m owsh.tools.enroll_face --name "Mina" --tag friend --camera 0   # or --images a.jpg b.jpg
python -m owsh.tools.enroll_face --list
pip install -e ".[ocr]"                                                   # optional text reading
```

Face photos stay in `data/faces/` on the helmet. Only names are ever sent to the phone.

## Architecture

```
reflex thread 50 Hz  TF-Luna fwd/down ─► zones (§5.1) / drop-off (§5.2) ─┐
imu thread 100 Hz    MPU-6050 ─► fall detector (§5.6) ───────────────────┤
vision thread        camera ─► blocked check ─► CLAHE ─► NanoDet ─► IoU  │
                     tracker ─► TTC ─► approach policy (§5.3) ───────────┤  EventBus (sync)
faces thread ≤ 2 Hz  YuNet + SFace (§5.4) ───────────────────────────────┤      │
buttons              gesture state machine (§7.2) ───────────────────────┤      ▼
ble thread           NUS GATT server (§8) ◄──────────────────────────────┴─ Arbiter + SOS + Controller
watchdog 10 Hz       heartbeats ─► FAULT events; drives arbiter/SOS timers      │        │
                                                              haptics mixer 10 ms   speech queue
```

| Module | Role |
|---|---|
| `owsh/config.py`, `config/default.yaml` | every threshold from the spec, validated |
| `owsh/events.py`, `owsh/bus.py` | event types, `Level` P0–P4, synchronous thread-safe bus |
| `owsh/arbiter.py` | hazard → haptic pattern, speech and phone alert; cooldowns; SOS state machine |
| `owsh/sensors/reflex.py` | median filter, zones with hysteresis, auto-calibrated drop-off detector |
| `owsh/sensors/tfluna.py`, `imu.py` | I2C drivers (smbus2), simulators, fall detector |
| `owsh/sensors/power.py` | under-voltage / throttling / temperature warnings, safe power-off |
| `owsh/vision/*` | camera sources, CLAHE, NanoDet decoding, tracker + TTC, describe, faces, OCR |
| `owsh/output/haptics.py` | spec §6.2 patterns, max-per-motor mixer, `max_duty` cap in the backend |
| `owsh/output/audio.py` | preemptive speech queue; piper / espeak-ng / pyttsx3 / print |
| `owsh/input/buttons.py` | debounced short / long / double state machine; gpiozero or keyboard |
| `owsh/link/protocol.py`, `ble.py` | pure JSON framing and chunking; `bless` NUS server or no-op link |
| `owsh/watchdog.py` | heartbeats, explicit faults, camera-blocked detector |
| `owsh/sim/dashboard.py` | desktop debug window |

Design rules the code follows:

- The **reflex path** (LiDAR → arbiter → motors) imports no vision code. It keeps working when the
  camera or the neural networks fail (P5).
- All timing uses an injectable monotonic clock, so the state machines are unit-tested with fake time.
- Logs are single lines with wall time and `mono=` monotonic time. `reflex zone=… sample_ts=…` and
  `haptic_on … latency_ms=…` measure the LiDAR → motor latency (spec T2, target ≤ 60 ms).

## Tests

```bash
python -m pytest -q
python -m compileall owsh
```

The tests cover config and spec values, i18n key and placeholder parity (en/ko), zones and hysteresis,
drop-off calibration, drop and step detection, tracker and TTC, the approach policy, haptic
patterns, the mixer and `max_duty`, the speech-queue rules, the button state machine, the fall
detector, protocol chunking round-trips, the watchdog and camera-blocked detection, the arbiter and
SOS flows, and a sim integration test (reflex latency, SOS, fault injection, dashboard). Detector
tests on `vtest.avi` run when the model and sample are present.

## Languages

Phrases live in `owsh/i18n/<lang>.json`. `en` and `ko` are maintained by the core team. A new
language must contain exactly the same keys and `{placeholders}`, which the tests check. A language
counts as verified only after review by a blind native speaker or an O&M instructor. Unverified
languages play a notice at boot.
