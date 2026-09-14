# 01 · Bill of Materials

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This page lists every part you need for the reference build, with approximate prices and where
to look for them. The authoritative part list is [§4.1 of the system design specification](00-system-design-spec.md#41-bill-of-materials-reference-build).
If this page and the spec ever disagree, the spec wins. Please open an issue so we can fix it.

> **Ready to order?** Use the [buying guide](10-buying-guide.md): verified purchase links, part numbers and the most common buying mistakes.

A machine-readable version is in [`../bom.csv`](../bom.csv) (now with official, global and Korean purchase-link columns). It includes columns for part, spec,
search keyword, price range and shop categories.

> **About prices.** All prices are **approximate ranges in US dollars, checked in September 2026**.
> They do not include shipping, import duty or VAT. Prices change often, especially for Raspberry Pi
> boards and memory. Compare at least two shops before you buy.

## Contents

- [Before you buy](#before-you-buy)
- [Reference build](#reference-build)
- [Optional parts](#optional-parts)
- [Printed parts and filament](#printed-parts-and-filament)
- [Total cost](#total-cost)
- [Budget variant](#budget-variant)
- [Where to buy](#where-to-buy)
- [Tools you need](#tools-you-need)

## Before you buy

- **The helmet must be new and certified.** Look for EN 1078 (Europe), CPSC 1203 (USA),
  AS/NZS 2063 (Australia/New Zealand), KC (Korea) or your country's equivalent. Choose a rounded
  shell with vents and no visor. Fit it to the person who will wear it. Never use a helmet that has
  already been in a crash.
- **Buy the TF-Luna with a 6-pin lead.** It uses a 6-pin 1.25 mm (GH) connector. Pin 5 selects I2C
  mode, so a 4-pin lead is not enough.
- **Buy coin motors with connectors or long leads.** The reference build uses no soldering.
- **Button modules must work at 3.3 V and be active-low.** Bare tactile switches are the simplest
  choice. See the [wiring guide](02-wiring-guide.md#step-6--buttons-b1b3).
- **Avoid unknown microSD cards.** A failing card is one of the most common causes of a helmet that
  stops working.

## Reference build

Refs match the spec, the wiring guide and the firmware.

| Ref | Part | Qty | Key spec | Search keyword | Unit price (USD, approx.) |
|---|---|---|---|---|---|
| H1 | Certified bicycle/multisport helmet with vents | 1 | EN 1078 / CPSC / AS/NZS / KC; vents ≥ 20 × 8 mm | `certified bicycle helmet EN 1078 vents` | 30–80 |
| U1 | Raspberry Pi 5, 4 GB (8 GB recommended) | 1 | 4 GB low end, 8 GB high end | `Raspberry Pi 5 8GB` | 60–120 |
| U2 | Raspberry Pi Active Cooler (official) | 1 | Required on Pi 5 | `Raspberry Pi 5 Active Cooler` | 5–8 |
| U3 | microSD 32 GB A2 | 1 | Known brand (or NVMe via M.2 HAT) | `microSD 32GB A2` | 8–15 |
| C1 | Raspberry Pi Camera Module 3 **Wide** | 1 | IMX708, 120° diagonal / 102° horizontal | `Raspberry Pi Camera Module 3 Wide` | 35–45 |
| C2 | Pi 5 camera cable 22-pin → 15-pin, 300 mm | 1 | FPC | `Raspberry Pi 5 camera cable 300mm` | 2–5 |
| S1 | Benewake **TF-Luna** LiDAR, forward | 1 | 0.2–8 m, 2° FOV, I2C mode | `Benewake TF-Luna LiDAR` | 18–35 |
| S2 | Benewake **TF-Luna** LiDAR, down-looking | 1 | Same, address changed to 0x11 | `Benewake TF-Luna LiDAR` | 18–35 |
| S3 | MPU-6050 (GY-521) IMU | 1 | I2C 0x68, fall detection | `GY-521 MPU-6050` | 2–5 |
| M1–M3 | Coin ERM vibration motor 1027, 3 V, with leads | 3 | 10 × 2.7 mm; left / centre / right | `1027 coin vibration motor 3V` | 0.5–2 each |
| D1 | ULN2003 driver board (from 28BYJ-48 kit) | 1 | Drives the 3 motors; sits in the aux pod | `ULN2003 driver board 28BYJ-48` | 1–3 |
| B1–B3 | 12 × 12 mm tactile switches (or 3-pin button modules, **3.3 V, active-low**) | 3 | Momentary | `12x12mm tactile switch` | 0.3–1.5 each |
| L1 | 3 mm LED + 330 Ω resistor (or LED module) | 1 | Status for sighted helpers | `3mm LED module` | 0.2–1 |
| A1 | USB audio adapter with a real mic input | 1 | Pi 5 has no 3.5 mm jack; sits in the aux pod. Must match the headset plug (4-pole TRRS combo jack, or split jacks + TRRS splitter) — see the [buying guide](10-buying-guide.md) | `USB audio adapter headphone mic` | 5–15 |
| A2 | Open-ear / bone-conduction wired headset with mic | 1 | Must not block the ears | `wired bone conduction headphones mic` | 15–60 |
| P1 | USB-C PD power bank, ≥ 5 V 3 A, 10 000–20 000 mAh | 1 | Pocket or waist bag | `USB-C PD power bank 20000mAh` | 20–45 |
| P2 | USB-C cable 1.5 m + magnetic breakaway USB-C adapter (3 A) | 1 set | Prevents neck snagging | `magnetic USB-C breakaway adapter 3A` | 8–20 |
| W1 | Dupont F-F 20 cm (40-pack), a few M-F 20–30 cm, **6-pin** 1.25 mm leads for TF-Luna | 1 set | Pin 5 is needed for I2C mode | `Dupont jumper wire female female 20cm` | 4–10 |
| W2 | 20 mm hook-and-loop straps (200 mm) + 3M Dual Lock / VHB pads | 1 set | 8–10 straps; Dual Lock for both faces of 3 saddles | `3M Dual Lock reclosable fastener` | 10–25 |
| W3 | Dupont 1-to-N female splitter cables for shared SDA, SCL, 5 V, 3.3 V and GND lines | 1 set | Or a 2 × 8 female header splitter. Not a Qwiic/STEMMA hub (3.3 V only, JST-SH plugs) | `Dupont splitter 1 to 4 female` | 1–5 |
| W4 | USB-A male → female extension cable, 10–15 cm | 1 | Pi 5 USB 2.0 port → audio adapter in the aux pod | `USB A male female extension 15cm` | 2–5 |
| F1 | M2.5 × 6 screws + 5 mm standoffs (Pi); M2 × 5 screws (camera, TF-Luna) | 1 set | The printed parts also use M2.5 × 8 pan head (lids) and M2 × 8 (pod cover), see [`hardware/README.md`](../../hardware/README.md) | `M2.5 standoff screw kit` | 5–10 |

## Optional parts

| Ref | Part | Qty | Why | Unit price (USD, approx.) |
|---|---|---|---|---|
| G1 | u-blox NEO-M8N GPS module (UART) | 0–1 | Location without a phone | 10–30 |
| R1 | TPU 95A filament for the rain gutter and rear nozzle | — | Passive rain management. About 95 g of TPU, more than the 60 g mass budget. | 2–4 (share) |

## Printed parts and filament

The printable parts (front pod, main case, aux pod, saddles, button housing, haptic pads, anchors,
clips, rain gutter) are listed in [03 · 3D printing guide](03-3d-printing-guide.md). Rigid parts are
PETG or ASA. Saddles, haptic pads and the rain gutter are TPU 95A. Strap anchors are PETG.
**Do not use PLA.** It softens in summer sun and in hot cars.

Filament is not a line in the spec BOM, so this guide adds an estimate (line PR1 in `bom.csv`):

- PETG or ASA: about **200 g** including supports (printed parts about 170 g, from the masses in
  [`hardware/README.md`](../../hardware/README.md)).
- TPU 95A: about **60 g** (three saddles about 41 g, three haptic pads about 9 g).
- Share of filament cost: about **USD 6–12**.

## Total cost

Totals are calculated from [`../bom.csv`](../bom.csv) (quantity × unit price).

- **Reference build (H1 to F1, plus the filament estimate): about USD 250–560.**
- Optional GPS and rain gutter filament: add about USD 12–34.
- Not included: shipping, tax, a 3D printer, tools, and a smartphone.

Where most of the money goes:

- Raspberry Pi 5 with cooler: USD 65–128
- Two TF-Luna LiDARs: USD 36–70
- Helmet: USD 30–80
- Headset: USD 15–60

If you do not own a printer, a local makerspace, library or online print service can print the
parts. Ask for PETG and TPU, not PLA.

## Budget variant

A cheaper build with a Raspberry Pi 4 and ST VL53L1X distance sensors would save about USD 40–100
(estimated total about USD 215–460).

> **The VL53L1X is NOT supported by firmware v1.0.** There is no VL53L1X driver yet; a future
> driver is on the [roadmap](08-patent-and-roadmap.md#610-vl53l1x-driver-for-a-budget-build).
> Until a driver exists and passes the [test plan](07-test-plan.md), a helmet with VL53L1X sensors
> has **no working head-height or drop-off warnings**. Do not use it as a walking aid.

### What changes

| Replaces | Budget part | Unit price (USD, approx.) |
|---|---|---|
| U1 Pi 5 | U1-B Raspberry Pi 4 Model B 4 GB | 55–75 |
| U2 Active Cooler | U2-B Pi 4 heatsink + 30 mm fan | 3–8 |
| C2 22→15-pin cable | C2-B 15→15-pin camera cable 300 mm | 1–4 |
| S1, S2 TF-Luna | S1-B, S2-B VL53L1X modules (**not supported yet**) | 5–15 each |
| A1 USB audio | A1-B use the Pi 4's 3.5 mm jack | 0 |

### Trade-offs

- **No firmware support.** See the warning above.
- **Much shorter outdoor range.** In the dark a VL53L1X reaches about 4 m. In bright sunlight
  its long-distance mode may reach well under 1 m. The down-looking sensor must see the ground about
  2.3 m away (spec §5.2). In daylight it would often get no return, which counts as a DROP. Expect many
  false drop alarms outdoors. The forward zones need 2.0 m and would also shrink.
- **Wider beam.** The VL53L1X field of view is about 27°, compared with 2° for the TF-Luna. It
  reacts to things beside the path, such as walls and poles.
- **Addresses are not stored.** Both VL53L1X sensors start at 0x29. Each needs its own XSHUT GPIO
  line so firmware can set a new address at every boot. The pin map in spec §4.2 has no lines for this.
- **Slower vision.** The Pi 4 runs the detector at a lower frame rate than the Pi 5. Test T3
  (≥ 8 FPS) is not expected to pass. Approach warnings come later.
- **Case fit.** The Pi 4 has the same mounting holes as the Pi 5, but its ports are in different
  places. Check the openings in `main_case_base` before printing, or adapt the model.
- **Sensor cradles.** VL53L1X modules do not fit the TF-Luna bays in the front pod.

**A supported cheaper option: keep both TF-Luna sensors and use a Raspberry Pi 4.** This keeps the
reflex path (spec P5) that firmware v1.0 supports, saves about USD 10–60, and only costs vision speed.

## Where to buy

Search keywords in the tables work on most shops. Shop names below are examples, not endorsements.

### Worldwide

- **Raspberry Pi boards, cooler, camera, cables:** Raspberry Pi Approved Resellers for your
  country (listed on raspberrypi.com), DigiKey, Mouser, Pimoroni.
- **TF-Luna, MPU-6050, ULN2003, motors, buttons, Dupont wires, splitters:** AliExpress (Benewake has an
  official store), DigiKey, Mouser, local electronics shops.
- **Helmet, power bank, headset, straps, USB extension:** local bike and sports shops, electronics stores,
  online retailers.

### Korea

- **Electronics:** 디바이스마트 (DeviceMart), 엘레파츠 (Eleparts), 아이씨뱅큐 (ICBanQ).
- **Helmet:** bicycle shops and sports stores. Check the KC mark.
- **Straps and fasteners:** large online malls, hardware stores.

## Tools you need

No soldering iron is needed.

- Small Phillips screwdrivers (PH0, PH1)
- Calipers, to check dimensions before printing (spec §4.4)
- A straight ruler, to measure the helmet shell radius ([03 · 3D printing guide](03-3d-printing-guide.md#2-measure-your-helmet-first))
- A phone inclinometer app, to measure the shell slope and sensor angles
- Flush cutters and a craft knife, for removing print supports
- A multimeter (recommended, for checking 5 V and continuity)
- A computer with a microSD card reader
- Labels or coloured tape for marking cables and the down-looking LiDAR

Next: [02 · Wiring guide](02-wiring-guide.md)
