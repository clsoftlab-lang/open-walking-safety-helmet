<!-- SPDX-License-Identifier: CERN-OHL-P-2.0 -->
<!-- Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국) -->

# OWSH v1.0 — Raspberry Pi 5 pin map (BCM numbering)

This table is copied from the authoritative spec, `docs/en/00-system-design-spec.md` §4.2.
If the two ever differ, **the spec wins**: change the spec first, then this file, the SVG and the firmware.
Diagram: [`wiring_diagram.svg`](wiring_diagram.svg).

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

## Device-side connections (how the diagram wires each part)

The header pins below are the ones drawn in `wiring_diagram.svg`. Any pin of the same power/GND
group from the table above may be used instead. Shared SDA, SCL, 5 V, 3.3 V and GND lines are split with
the W3 Dupont splitter / small I2C hub (spec §4.1); TF-Luna needs the **6-pin** 1.25 mm lead (W1) because pin 5 is used.

| Device | Device pin | → Pi header pin | Wire colour |
|---|---|---|---|
| S1 TF-Luna FORWARD (0x10) | 1 +5V | 5 V rail (pin 2 / 4) | red |
| | 2 RXD/SDA | pin 3 (GPIO2 SDA) | blue |
| | 3 TXD/SCL | pin 5 (GPIO3 SCL) | yellow |
| | 4 GND | GND rail | black |
| | 5 configuration | GND rail (= I2C mode) | black |
| | 6 multiplexing output | not connected | — |
| S2 TF-Luna DOWN (0x11) | same as S1 | same as S1 | same |
| S3 MPU-6050 / GY-521 (0x68) | VCC | 3.3 V rail (pin 1 / 17) | orange |
| | GND | GND rail | black |
| | SCL / SDA | pin 5 / pin 3 | yellow / blue |
| | AD0 | open or GND (address 0x68) | — |
| D1 ULN2003 board | IN1 / IN2 / IN3 | pin 11 (GPIO17) / 13 (GPIO27) / 15 (GPIO22) | green |
| | + / − | 5 V rail / GND rail | red / black |
| M1 / M2 / M3 ERM 1027 | motor − | OUT1 / OUT2 / OUT3 | green |
| | motor + | ULN2003 board "+" (5 V) | red |
| B1 ○ / B2 △ / B3 □ | switch side A | pin 29 (GPIO5) / 31 (GPIO6) / 37 (GPIO26) | green |
| | switch side B | GND rail | black |
| 3-pin button module (alternative) | VCC / OUT / GND | **3.3 V only** (pin 1/17, never 5 V) / GPIO as above / GND; module must be active-low (else set `buttons.active_high: true`) | orange / green / black |
| L1 LED | anode via 330 Ω | pin 36 (GPIO16) | green |
| | cathode | GND rail | black |
| C1 Camera Module 3 Wide | 15-pin FPC | CAM/DISP 0 via C2 (22→15-pin, 300 mm) | FPC |
| A1 USB audio adapter | USB-A | a USB 2.0 port | — |
| P1 power bank | USB-C PD 5 V 3 A | Pi 5 USB-C via P2 magnetic breakaway | — |
| G1 GPS (optional) | TX / RX | pin 10 (GPIO15 RX) / pin 8 (GPIO14 TX) | purple |
