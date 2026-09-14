# 02 · Wiring Guide

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This guide connects all electronics to the Raspberry Pi 5 **without soldering**. It uses Dupont
jumper wires, the TF-Luna's GH1.25 cable and a small splitter.

- Wiring diagram: [`hardware/wiring/wiring_diagram.svg`](../../hardware/wiring/wiring_diagram.svg) and the
  device-side table in [`hardware/wiring/pinout.md`](../../hardware/wiring/pinout.md)
- Authoritative pin map: [spec §4.2](00-system-design-spec.md#42-raspberry-pi-5-pin-map-bcm-numbering--authoritative)
- Parts and refs (S1, D1, B1 …): [01 · Bill of materials](01-bill-of-materials.md)

> **Wire on the bench first.** Lay everything out on a table, wire it, and pass all checks in this
> guide. Only then move the parts into the printed cases ([04 · Assembly guide](04-assembly-guide.md)).

## Contents

1. [Safety rules for wiring](#1-safety-rules-for-wiring)
2. [Pin map (authoritative)](#2-pin-map-authoritative)
3. [Finding pins on the header](#3-finding-pins-on-the-header)
4. [Splitting shared lines without soldering](#4-splitting-shared-lines-without-soldering)
5. [Step-by-step wiring](#5-step-by-step-wiring)
6. [TF-Luna: I2C mode and address change](#6-tf-luna-i2c-mode-and-address-change)
7. [Checks](#7-checks)
8. [Common mistakes](#8-common-mistakes)

## 1. Safety rules for wiring

- **Unplug the power** before connecting or moving any wire. Remove the USB-C cable from the Pi.
- **Never put 5 V on a GPIO pin.** The Pi's GPIO pins are 3.3 V only. A 5 V signal can destroy the Pi.
- **Never connect 5 V or 3.3 V directly to GND.** Check twice before powering on.
- Handle the camera ribbon cable gently. Do not fold it sharply.
- Label every cable end as you go (for example "FWD SDA", "M1 L").

## 2. Pin map (authoritative)

This table is identical to spec §4.2. BCM numbering.

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

> **Button modules: 3.3 V only.** If you use 3-pin button modules instead of bare switches, power them
> from pin 1 or 17. **Never from 5 V**: a module powered from 5 V puts 5 V on a GPIO pin and damages the Pi.

## 3. Finding pins on the header

- The 40-pin header has two rows. **Odd pins (1, 3, 5 …) are on the inner row.** Even pins (2, 4, 6 …)
  are on the row along the board edge.
- **Pins 1 and 2 are at the end farthest from the USB ports.** Pins 39 and 40 are next to the USB ports.
- On the Pi, run `pinout` in a terminal to print a diagram of the header.
- A printed GPIO reference card that slips over the pins helps a lot.

Pins used in this build (✔ = used, ○ = optional GPS or spare GND):

```
            inner row  outer row (board edge)
 3.3 V  ✔   1  ●  ●  2   ✔  5 V
 SDA    ✔   3  ●  ●  4   ✔  5 V
 SCL    ✔   5  ●  ●  6   ✔  GND
            7  ●  ●  8   ○  GPS RX←Pi TX (GPIO14)
 GND    ✔   9  ●  ●  10  ○  GPS TX→Pi RX (GPIO15)
 LEFT   ✔  11  ●  ●  12
 CENTER ✔  13  ●  ●  14  ✔  GND
 RIGHT  ✔  15  ●  ●  16
 3.3 V     17  ●  ●  18
           19  ●  ●  20  ✔  GND
           21  ●  ●  22
           23  ●  ●  24
 GND    ○  25  ●  ●  26
           27  ●  ●  28
 B1 ○   ✔  29  ●  ●  30  ✔  GND
 B2 △   ✔  31  ●  ●  32
           33  ●  ●  34  ✔  GND
           35  ●  ●  36  ✔  STATUS LED (GPIO16)
 B3 □   ✔  37  ●  ●  38
 GND    ✔  39  ●  ●  40
                 (USB ports this end)
```

## 4. Splitting shared lines without soldering

Some header pins must feed more than one device:

| Shared line | From header pin | Goes to |
|---|---|---|
| SDA | 3 | S1 pin 2, S2 pin 2, S3 SDA |
| SCL | 5 | S1 pin 3, S2 pin 3, S3 SCL |
| 5 V (sensors) | 2 | S1 pin 1, S2 pin 1 |
| 5 V (motors) | 4 | D1 "+", M1 +, M2 +, M3 + |
| GND (LiDARs) | 6 | S1 pin 4, S1 pin 5, S2 pin 4, S2 pin 5 |

Use part **W3** (spec §4.1), one of these:

- **Mini breadboard (170 tie-points).** Each half-column of 5 holes is one connected strip. Use one
  strip per shared line. Plug the wire from the Pi into the strip, then plug each device wire into
  the same strip. Label the strips: SDA, SCL, 5V-S, 5V-M, GND.
- **Dupont 1-to-N splitters, or a 2 × 8 female header splitter.** Smaller and easier to fit inside the
  cases. Wrap each splitter in heat-shrink tube or tape so it cannot touch other pins.
- **A small I2C hub** (for example a Qwiic/STEMMA hub) for SDA and SCL, with Dupont adapters.

For the final install on the helmet, splitters usually fit better than a breadboard. A mini breadboard
is handy for the bench build.

## 5. Step-by-step wiring

Each step lists every wire. Tick them off as you go.

### Step 1 · Prepare the splitter

1. Mark five strips (or five splitters): **SDA**, **SCL**, **5V-S** (sensors), **5V-M** (motors), **GND**.
2. Pi pin 3 → SDA strip.
3. Pi pin 5 → SCL strip.
4. Pi pin 2 → 5V-S strip.
5. Pi pin 4 → 5V-M strip.
6. Pi pin 6 → GND strip.

Ground pins used in this guide: pin 6 (GND strip), 9 (IMU), 14 (ULN2003), 20 (LED), 30 (B1),
34 (B2), 39 (B3). Pin 25 stays free as a spare.

### Step 2 · MPU-6050 IMU (S3, GY-521)

| GY-521 pin | Connect to |
|---|---|
| VCC | Pi pin 1 (3.3 V) |
| GND | Pi pin 9 (GND) |
| SCL | SCL strip |
| SDA | SDA strip |
| XDA, XCL, AD0, INT | leave unconnected |

AD0 unconnected keeps the address at 0x68.

### Step 3 · Forward TF-Luna (S1) — connect later for the address step

TF-Luna connector pins, counted from pin 1 as printed in the Benewake datasheet:

| TF-Luna pin | Name | Connect to |
|---|---|---|
| 1 | +5 V | 5V-S strip |
| 2 | SDA (RXD) | SDA strip |
| 3 | SCL (TXD) | SCL strip |
| 4 | GND | GND strip |
| 5 | Configuration | **GND strip.** This selects I2C mode. |
| 6 | Multiplexing output | leave unconnected |

> **Do not trust the wire colours.** Cable colours differ between batches. Count the pins on the
> connector using the pin-1 mark in the datasheet.

**Do not connect S1 yet.** First change the address of S2 ([section 6](#6-tf-luna-i2c-mode-and-address-change)).

### Step 4 · Down-looking TF-Luna (S2)

Wired exactly like S1:

| TF-Luna pin | Connect to |
|---|---|
| 1 +5 V | 5V-S strip |
| 2 SDA | SDA strip |
| 3 SCL | SCL strip |
| 4 GND | GND strip |
| 5 Configuration | GND strip |
| 6 | leave unconnected |

Put a label on S2: **DOWN 0x11**.

### Step 5 · ULN2003 driver (D1) and vibration motors (M1–M3)

On the helmet the ULN2003 sits in the **aux pod** at the back of the head, not in the main case.
Use Dupont wires long enough (about 20–30 cm) to reach from the Pi header to the aux pod.

The ULN2003 board has input pins IN1–IN4, two power pins "+" and "−", an ON/OFF jumper, and a
white 5-pin motor socket.

| ULN2003 pin | Connect to |
|---|---|
| IN1 | Pi pin 11 (GPIO17, LEFT) |
| IN2 | Pi pin 13 (GPIO27, CENTER) |
| IN3 | Pi pin 15 (GPIO22, RIGHT) |
| IN4 | leave unconnected |
| "+" | 5V-M strip |
| "−" | Pi pin 14 (GND) |
| ON/OFF jumper | **must be fitted** |

Motors. Each motor has two leads. The ULN2003 switches the negative side.

| Motor | + lead | − lead |
|---|---|---|
| M1 left temple | 5V-M strip | ULN2003 OUT1 |
| M2 forehead centre | 5V-M strip | ULN2003 OUT2 |
| M3 right temple | 5V-M strip | ULN2003 OUT3 |

**Reaching OUT1–OUT3 without soldering:**

1. The outputs are in the white 5-pin socket. Board layouts differ, so find them with a multimeter.
   On the ULN2003 chip, **pin 16 is OUT1, pin 15 is OUT2, pin 14 is OUT3** (pin 1 is next to the notch
   or dot). Check continuity from each chip pin to the socket holes and mark them.
2. Push the male end of an M-F Dupont wire into each output hole. It should hold firmly.
3. Connect the motor's − lead to the female end. If your motors have bare leads, use motors with a
   2-pin connector, crimp Dupont ends onto the leads (crimping is not soldering), or use small
   lever-type wire connectors.
4. A coin ERM motor vibrates in either polarity. What matters is that it sits **between 5 V and
   an OUT pin**, never between 5 V and GND.

The firmware caps motor duty at 75 % (`haptics.max_duty`), because the driver gives about 4 V to
3 V motors. Do not raise it.

### Step 6 · Buttons (B1–B3)

**Bare 12 × 12 mm tactile switches (recommended).** A switch has four legs in two connected pairs.
Use two **diagonally opposite** legs. That pair always switches, whichever way the switch is turned.

| Button | Shape (cap) | One leg | Diagonal leg |
|---|---|---|---|
| B1 front | ○ circle | Pi pin 29 (GPIO5) | Pi pin 30 (GND) |
| B2 middle | △ triangle | Pi pin 31 (GPIO6) | Pi pin 34 (GND) |
| B3 rear | □ square | Pi pin 37 (GPIO26) | Pi pin 39 (GND) |

The firmware turns on the internal pull-up. Idle reads high, pressed reads low (active-low).

**3-pin button modules.** VCC → **3.3 V only** (pin 1 or 17, via splitter), **never 5 V**. GND → GND.
OUT → GPIO as above.

- Use modules that output **low when pressed** (active-low).
- An active-high module (high when pressed) reads as **permanently pressed** unless configured. That can
  look like B3 held down and start an SOS countdown. Spec §4.2 defines the setting
  `buttons.active_high: true` for such modules. Check that your firmware version's
  `firmware/config/default.yaml` lists it before relying on it; otherwise use active-low modules or bare
  switches.
- Check every button with [check 7.4](#74-buttons).

### Step 7 · Status LED (L1)

1. Pi pin 36 (GPIO16) → one end of the 330 Ω resistor.
2. Other end of the resistor → LED **long leg** (anode).
3. LED **short leg** (cathode) → Pi pin 20 (GND).

An LED module with a built-in resistor connects directly: S → pin 36, − → GND.
The LED sits under the light-pipe hole in `main_case_lid`. Use Dupont wires long enough to reach it.

### Step 8 · Camera (C1)

1. Power off.
2. On the Pi 5, gently lift the latch of the **CAM/DISP 0** connector.
3. Insert the 22-pin end of the cable straight and fully. Follow the official Raspberry Pi camera
   documentation for which side the contacts face.
4. Close the latch. Pull very lightly: the cable must not move.
5. Connect the 15-pin end to the camera module the same way.

A reversed cable usually just means the camera is not detected. Power off and turn it around.

### Step 9 · Audio (A1, A2, W4)

1. Plug the **10–15 cm USB-A extension (W4)** into a **USB 2.0 port** (black) of the Pi. Keep the blue
   USB 3 ports free. This reduces 2.4 GHz noise near Bluetooth.
2. Plug the USB audio adapter into the extension. On the helmet, the adapter sits in the aux pod.
3. Plug the headset into the adapter: headphone plug into the headphone jack, mic plug into the mic jack.

### Step 10 · Optional GPS (G1)

| GPS pin | Connect to |
|---|---|
| TX | Pi pin 10 (GPIO15, RX) |
| RX | Pi pin 8 (GPIO14, TX) |
| VCC | 3.3 V or 5 V as printed on your module |
| GND | Pi pin 25 (spare GND) |

Enable the serial port: `sudo raspi-config` → Interface Options → Serial Port →
login shell **No**, serial hardware **Yes**.

### Step 11 · Power

Leave the power bank disconnected until [check 7.1](#71-before-power-on). The Pi is powered through
its USB-C socket from the power bank, through the magnetic breakaway adapter (P2).

## 6. TF-Luna: I2C mode and address change

Both TF-Luna sensors leave the factory with I2C address **0x10**. Two devices on one bus cannot share
an address. So you change the down-looking unit to **0x11**, once. The sensor remembers it.

You need a working Raspberry Pi OS with the firmware installed
([04 · Assembly guide, part B](04-assembly-guide.md#part-b--software-setup)). The commands below run from
the `firmware` folder, which contains the virtual environment `.venv` made by the setup script.

1. **Power off.** Connect **only S2** (down-looking) as in step 4. S1 stays disconnected.
   Pin 5 must be on GND, otherwise the sensor stays in UART mode and does not appear on I2C.
2. Power on. Stop the helmet service so nothing else uses the bus:
   ```bash
   sudo systemctl stop owsh
   ```
3. Check that the sensor is visible at 0x10:
   ```bash
   i2cdetect -y 1
   ```
   You should see `10` (and `68` if the IMU is connected).
4. Change the address:
   ```bash
   .venv/bin/python -m owsh.tools.tfluna_addr --from 0x10 --to 0x11
   ```
   Add `--dry-run` first if you want to see the register writes without touching the bus.
5. **Power off completely** for 5 seconds, then power on again.
6. Run `i2cdetect -y 1` again. You should now see `11` instead of `10`.
7. Label S2 **DOWN 0x11** if you have not already done so.
8. Power off. Connect S1 (forward) as in step 3. Power on and continue with [check 7.2](#72-i2c-bus).

If you mix up the sensors later, it is easy to tell them apart: the one at 0x11 is DOWN.

## 7. Checks

### 7.1 Before power on

- [ ] No bare metal of a splitter or wire end touches another pin.
- [ ] With a multimeter on continuity: 5 V pin 2 to GND pin 6 does **not** beep.
- [ ] 3.3 V pin 1 to GND does **not** beep.
- [ ] Both TF-Luna pin 5 wires go to the GND strip.
- [ ] ULN2003 ON/OFF jumper is fitted.
- [ ] Button module VCC (if used) goes to 3.3 V, not 5 V.

### 7.2 I2C bus

If `i2cdetect` is missing, install it: `sudo apt install -y i2c-tools`.

```bash
i2cdetect -y 1
```

Expected output, with exactly these three addresses:

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: 10 11 -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

- `10` = TF-Luna FWD (S1)
- `11` = TF-Luna DOWN (S2)
- `68` = MPU-6050 (S3)

What other results mean:

| You see | Likely cause |
|---|---|
| Only `10`, no `11` | S2's address was not changed, or S2 is not connected. Both sensors may be answering at 0x10. |
| Nothing at 10 or 11 | TF-Luna pin 5 not on GND (UART mode), no 5 V, or SDA/SCL swapped |
| `69` instead of `68` | GY-521 AD0 is connected to VCC. Disconnect it. |
| Every address shows a number | SDA or SCL shorted to GND or 3.3 V |
| `Error: Could not open file /dev/i2c-1` | I2C not enabled. Run the setup script, or `sudo raspi-config nonint do_i2c 0` and reboot. |
| Addresses appear and disappear | Loose Dupont wire, or long wires. See [common mistakes](#8-common-mistakes). |

### 7.3 Camera

```bash
rpicam-hello --list-cameras
```

You should see one camera with sensor `imx708_wide`.

### 7.4 Buttons

With the helmet service stopped, set the pull-ups and read the pins:

```bash
pinctrl set 5,6,26 ip pu
pinctrl get 5,6,26
```

- Not pressed: each line ends with `hi`.
- Hold B1 and run `pinctrl get 5` again: it must show `lo`. Repeat for B2 (6) and B3 (26).
- If a pin shows `lo` when **not** pressed, the switch is wired to the wrong legs or shorted. Fix this
  before first boot.
- If a module shows `lo` when idle and `hi` when pressed, it is **active-high**. Replace it with an
  active-low module or a bare switch, or configure `buttons.active_high: true` if your firmware supports it.
  Otherwise the firmware sees the button as permanently pressed, and B3 could start an SOS countdown.

### 7.5 Motors and LED

Start the service (`sudo systemctl start owsh`) or reboot. At boot the **ready** pattern runs:
**left → centre → right**, 100 ms each.

- Hold M1, M2 and M3 between your fingers. They must buzz in that order.
- If the order is wrong, swap the motor − wires on OUT1–OUT3. Do not change the pin map.
- The status LED should light while the helmet is running.

### 7.6 Audio

```bash
aplay -l
```

The USB audio adapter should be listed. After boot you should hear the start-up voice message in the headset.

## 8. Common mistakes

1. **TF-Luna pin 5 not grounded.** The sensor stays in UART mode and is invisible on I2C.
2. **Both TF-Lunas connected during the address change.** The tool may change the wrong one, or
   both. Always connect only S2 for that step.
3. **Trusting wire colours** on the TF-Luna cable. Count pins.
4. **Button module on 5 V.** Puts 5 V on a GPIO and damages the Pi. Use 3.3 V only.
5. **Active-high button module.** Reads as "permanently pressed" unless configured. Check with `pinctrl get`.
6. **Motor between 5 V and GND** instead of 5 V and OUT. The motor runs all the time and the Pi
   cannot control it.
7. **ULN2003 ON/OFF jumper missing.** Motors never run.
8. **Missing common ground.** Every module's GND must go to a Pi GND pin.
9. **Using the wrong numbering.** The pin map uses BCM GPIO numbers *and* physical header pins.
   GPIO17 is header pin 11, not pin 17.
10. **GY-521 AD0 tied high.** The IMU moves to 0x69 and firmware cannot find it.
11. **Long, loose I2C wires on the helmet.** The bus from the rear case to the front pod is 30–40 cm.
    Twist SDA together with a GND wire, and SCL with another GND wire. Push every Dupont connector fully
    home and wrap connector pairs with tape. If `i2cdetect` is still unstable, try
    `i2c_arm_baudrate=100000` in `/boot/firmware/config.txt` as a diagnostic, and report it in a
    [field test report](../../.github/ISSUE_TEMPLATE/field_test_report.yml). The spec value is 400 kHz.
12. **Audio adapter (or its W4 extension) in a blue USB 3 port.** It works, but can add 2.4 GHz noise near Bluetooth.
13. **Camera cable not fully inserted.** Camera not listed. Reseat both ends with the power off.

Next: [03 · 3D printing guide](03-3d-printing-guide.md)
