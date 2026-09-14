> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

# 10 · Buying guide (verified purchase links)

This guide helps first-time builders **buy the right parts the first time**. Part specifications are in
[01 · Bill of materials](01-bill-of-materials.md). Builders in Korea: see the Korean guide with local shop carts,
[10 · 구매가이드](../ko/10-구매가이드.md).

> [!IMPORTANT]
> - **Prices and stock were checked on 2026-09-15.** They change. Check again before ordering.
> - **✅ verified** = we opened the product page and confirmed the exact title and key spec / part number.
> - **🔍 search** = no single listing can be recommended; the link opens a search. Check the **"must have"** column.
> - Official manufacturer pages are the most stable links. If a shop link breaks, search the **part number**
>   (SC1224, SC1129, SC1148, TF-Luna …).
> - The project has no affiliate or sponsorship relationship with any seller.

## The 7 most common mistakes

1. **Camera:** buy **Camera Module 3 Wide** (Raspberry Pi part **SC1224**), not the standard (75°), NoIR or NoIR Wide
   variants. Shops often list all four on one page.
2. **Camera cable:** buy the **Pi 5 camera cable, 22-pin 0.5 mm to 15-pin 1 mm, 300 mm** (Raspberry Pi calls it
   "Standard–Mini", part **SC1129**). The Wide camera may ship with only a 15-to-15 pin (Pi 4) cable, and short
   cables won't reach. Display cables look similar and do not work.
3. **LiDAR:** the title must say **TF-Luna**. TFmini-S, TFmini Plus and TF02 are different, larger sensors.
4. **No Qwiic/STEMMA QT hub** for W3. Those hubs carry 3.3 V only with 1 mm JST-SH plugs, but the TF-Luna needs 5 V.
   Use Dupont female 1-to-N splitters.
5. **Power bank:** the output table must list **USB-C 5 V ⎓ 3 A**. Many "PD 20 W" banks give 3 A only at 9 V or
   higher, and the helmet will then warn about low power.
6. **Headset and audio adapter must match.** Most headsets have one **4-pole (TRRS) plug**. Buy an adapter with a
   4-pole combo jack, or split jacks plus a TRRS→2×TRS splitter. Adapters that only list "line in" may be too weak
   for a headset mic.
7. **ULN2003:** buy the **driver board**, not the bare "ULN2003AP" chip.

## Core parts

| Ref | Part | Official page | Verified seller listings (price, stock on 2026-09-15) | Must have |
|---|---|---|---|---|
| U1 | Raspberry Pi 5 (8 GB recommended, 4 GB works) | [raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-5/) ✅ | [DigiKey 8GB SC1432](https://www.digikey.com/en/products/detail/raspberry-pi/SC1112/21658257) $175, in stock ✅ · [DigiKey 4GB SC1431](https://www.digikey.com/en/products/detail/raspberry-pi/SC1111/21658261) $110, backorder ✅ · [The Pi Hut](https://thepihut.com/products/raspberry-pi-5) £105.60 / £168 ✅ · [Adafruit 8GB](https://www.adafruit.com/product/5813) $200 ✅ | Check the RAM size on the listing (old part numbers SC1111/SC1112 now redirect to SC1431/SC1432) |
| U2 | Raspberry Pi Active Cooler | [raspberrypi.com](https://www.raspberrypi.com/products/active-cooler/) ✅ | [DigiKey SC1148](https://www.digikey.com/en/products/detail/raspberry-pi/SC1148/21658255) $5 ✅ · [The Pi Hut](https://thepihut.com/products/active-cooler-for-raspberry-pi-5) £4.80 ✅ · [Adafruit](https://www.adafruit.com/product/5815) $13.50 ✅ | Pi 5 only; Pi 4 heatsinks don't fit |
| U3 | microSD 32 GB A2 | [Raspberry Pi SD cards](https://www.raspberrypi.com/products/sd-cards/) ✅ | 🔍 [AliExpress search](https://www.aliexpress.com/w/wholesale-microsd-32gb-a2.html) | **A2** marking; buy a known brand from its official store |
| C1 | Camera Module 3 **Wide** | [raspberrypi.com](https://www.raspberrypi.com/products/camera-module-3/) ✅ | [DigiKey SC1224](https://www.digikey.com/en/products/detail/raspberry-pi/SC0874/17278644) $35 ✅ · [The Pi Hut (select "Wide-angle")](https://thepihut.com/products/raspberry-pi-camera-module-3) £33.60 ✅ · [Adafruit 5658](https://www.adafruit.com/product/5658) $38.50 ✅ | "Wide", 120°, **not NoIR** |
| C2 | Pi 5 camera cable 300 mm | [raspberrypi.com](https://www.raspberrypi.com/products/camera-cable/) ✅ | [DigiKey SC1129](https://www.digikey.com/en/products/detail/raspberry-pi/SC1129/21658260) $2 ✅ · [The Pi Hut](https://thepihut.com/products/camera-adapter-cable-for-raspberry-pi-5) £1.90 ✅ · [Adafruit 5819](https://www.adafruit.com/product/5819) $3.16 ✅ · [SparkFun PRT-26025](https://www.sparkfun.com/raspberry-pi-5-camera-cable-300mm.html) $6 ✅ | 22-pin 0.5 mm ↔ 15-pin 1 mm, **300 mm**, "CAMERA" printed |
| S1, S2 | Benewake TF-Luna LiDAR ×2 | [benewake.com](https://en.benewake.com/TFLuna/index.html) ✅ · [manual PDF](https://en.benewake.com/uploadfiles/2024/04/20240426135946148.pdf) ✅ | [DFRobot SEN0340](https://www.dfrobot.com/product-1995.html) $24.90, cable included ✅ · [Seeed 101990656](https://www.seeedstudio.com/TF-Luna-LiDAR-Module-Short-Range-Distance-Sensor-p-4561.html) $28.90 ✅ · [The Pi Hut (Waveshare)](https://thepihut.com/products/tf-luna-lidar-ranging-sensor) £24, sold out ✅ | Title says **TF-Luna**; 6-pin cable included or ordered separately |
| S3 | MPU-6050 IMU | — (chip is obsolete) | 🔍 [AliExpress GY-521](https://www.aliexpress.com/w/wholesale-gy-521-mpu6050.html) · genuine alternative: [Adafruit 3886](https://www.adafruit.com/product/3886) $12.95 ✅ (different board shape) | I2C address 0x68 |
| M1–M3 | Coin vibration motor 10 × 2.7 mm, 3 V ×3 | — | [Adafruit 1201 "Vibrating Mini Motor Disc"](https://www.adafruit.com/product/1201) $1.95 ✅ · 🔍 [AliExpress 1027](https://www.aliexpress.com/w/wholesale-1027-coin-vibration-motor-3v.html) | 10 mm diameter, 3 V, with leads |
| D1 | ULN2003 driver board | — | 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-uln2003-driver-board-28byj-48.html) | Board with pin headers (from 28BYJ-48 kits), not the bare chip |
| B1–B3 | 12 × 12 mm tactile switch ×3 | — | [SparkFun COM-09190](https://www.sparkfun.com/momentary-pushbutton-switch-12mm-square.html) $0.75 ✅ · [Adafruit 1119 (10-pack)](https://www.adafruit.com/product/1119) $2.50 ✅ · 🔍 [AliExpress 12×12×7.3](https://www.aliexpress.com/w/wholesale-12x12x7.3mm-tactile-switch.html) | Through-hole. Height varies (6 / 7.3 / 8 mm): the printed parts assume 7.3 mm — if different, adjust `sw_body_h` in `button_module.scad` and `stem_d` / `stem_shape` in `button_caps.scad` |
| A1 | USB audio adapter | — | [Adafruit 1475](https://www.adafruit.com/product/1475) $4.95 ✅ · [The Pi Hut](https://thepihut.com/products/usb-audio-adapter-works-with-raspberry-pi) £4.30 ✅ (both list the input as "line in" — may be weak for a mic) · 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-usb-audio-adapter-headphone-microphone.html) | Real **mic** input; jack type matches the headset |
| A2 | Wired open-ear / bone-conduction headset with mic | — | 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-wired-bone-conduction-headphones-microphone.html) | **Wired 3.5 mm**, mic, leaves ears open |
| P1 | USB-C PD power bank 10 000–20 000 mAh | — | 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-usb-c-pd-power-bank-20000mah.html) | Output table lists **5 V ⎓ 3 A** on USB-C; safety certification for your country |
| P2 | Magnetic breakaway USB-C | — | [Adafruit 5521 (120 W data + power, right angle)](https://www.adafruit.com/product/5521) $14.95 ✅ | Rated ≥ 3 A **and** data-capable; avoid charge-only tips. Adafruit 5524 tip does not fit 5521 |
| W1 | Dupont F-F jumpers + 6-pin 1.25 mm cable | — | [Adafruit 266 (40 × 150 mm)](https://www.adafruit.com/product/266) $3.95 ✅ · 🔍 [AliExpress GH1.25 6-pin to Dupont](https://www.aliexpress.com/w/wholesale-gh1.25-6pin-to-dupont-cable.html) | 20 cm or longer helps reach the front pod |
| W2 | 3M Dual Lock + 20 mm hook-and-loop straps | [3M Dual Lock SJ3560](https://www.3m.com/3M/en_US/p/d/b40072057/) ✅ | Buy **small retail packs** (DigiKey only sells industrial rolls, e.g. SJ3560 150 ft $1,409 — don't) | Genuine 3M; straps 20 mm wide |
| W3 | Dupont female 1-to-N splitters | — | 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-dupont-splitter-female.html) | Female ends; **not** a Qwiic hub |
| W4 | USB-A male→female extension 10–30 cm | — | 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-usb-a-male-female-extension-15cm.html) | USB 2.0, slim plugs |
| F1 | M2.5 standoffs/screws + M2 screws | — | [Adafruit 3299 M2.5 nylon kit](https://www.adafruit.com/product/3299) $16.95 ✅ (6 mm standoffs, no M2) | Also buy M2 × 5 and M2 × 8 screws |

Optional: **G1 u-blox NEO-M8N GPS** — [u-blox NEO-M8 series](https://www.u-blox.com/en/product/neo-m8-series) ✅ (marked NRND; NEO-M8M-0 recommended). Marketplace modules are often clones: 🔍 [AliExpress](https://www.aliexpress.com/w/wholesale-neo-m8n-gps-module.html).

Also needed: a **certified bicycle helmet** from a local shop (EN 1078 / CPSC 1203 / AS/NZS 2063 / KC, new, with vents)
and **PETG (or ASA) + TPU 95A** filament.

## Where to buy Raspberry Pi parts in your country

Use the official reseller finder: **https://www.raspberrypi.com/resellers/** (about 150 approved resellers in 60+ countries).
Every product page on raspberrypi.com also has a **Buy now** button that lists resellers near you.

## Approximate cost (USD, excluding shipping, taxes and printer)

| Build | Range |
|---|---:|
| Reference (Pi 5 8 GB) | **about $440–660** |
| Pi 5 4 GB | **about $370–590** |

## Unpacking checklist

- [ ] Raspberry Pi 5 with the RAM size you ordered; Active Cooler **SC1148**
- [ ] Camera box says **Camera Module 3 Wide**, not NoIR
- [ ] Camera cable: narrow 22-pin end + wide 15-pin end, "CAMERA" printed, ~300 mm
- [ ] LiDAR label **TF-Luna**, 6-pin connector, cable present
- [ ] ULN2003 is a **board**, not a chip
- [ ] Tactile switch height measured (for button caps)
- [ ] Power bank label shows **5 V ⎓ 3 A**
- [ ] Headset plug fits the audio adapter (with splitter if needed)

Found a broken link or a better local source? Open an [issue](https://github.com/clsoftlab-lang/open-walking-safety-helmet/issues) — it saves the next builder from the same mistake.
