# Open Walking Safety Helmet

**English** · [한국어](README.ko.md)

> ### *Until the day blind people everywhere can walk like anyone else.*
> 전 세계 시각장애인이 일반인처럼 다닐 수 있는 그날까지.

An open-source helmet that helps blind and low-vision people walk safely.
It feels **head-height obstacles**, finds **stairs and drop-offs**, warns about
**approaching bikes, cars and people**, **reads signs aloud**, recognises **friends' faces**
and sends an **SOS** with your location. It tells you through **vibration on your head** and
**voice**.

Everything is free: firmware, 3D-printable parts, wiring, phone app, documents, **and the
patent.**

**Inventor and project lead:** CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국 박사)
**Patent:** Korean Patent No. 10-2560496, released royalty-free for everyone. See the [Patent Pledge](PATENT_PLEDGE.md).

> [!WARNING]
> **Status: v1.0 reference design, not yet field-validated.** It is an assistive aid, not a
> certified medical device. It **does not replace** a white cane, guide dog or orientation
> and mobility training. Read the [safety guide](docs/en/06-safety.md) before walking with it.

---

## Why a helmet and not glasses?

Sensors can miss things. If a collision happens anyway, **a helmet still protects the head.**
So this project never weakens the helmet:

- Start from a **certified bicycle helmet**. Never 3D-print the shell.
- **Never drill, cut or glue** into the helmet.
- Modules attach with **straps and removable pads** so they break away under impact.
- They sit flat on the shell (curved undersides), stick out at most 35–40 mm (30 mm for small modules) and have rounded edges.

## What it does

| You feel / hear | When |
|---|---|
| Forehead buzz that speeds up, then stays on | Something at **head height** ahead (branch, sign, truck mirror): 2 m → 1.2 m → 0.6 m |
| All three motors, two long buzzes + "Step down ahead" | **Stairs down, curb or platform edge** |
| Left or right side buzzes + "Bicycle approaching from the right" | A person, bike or car **moving towards you** |
| Two gentle buzzes on one side + "Mina is ahead on the left" | An **enrolled friend** is nearby |
| Press ○ | **Reads text** in front of you (signs, labels) |
| Press △ | **Describes the scene**: "2 people ahead, bicycle on the right" |
| Hold □ for 3 s, or fall down | **SOS** countdown, then the phone app shows your location with one-tap call and SMS |
| Three short forehead buzzes every 10 s | **Something is broken.** Don't trust silence. Distance sensors keep working. |

Full haptic language: [User guide](docs/en/05-user-guide.md)

## How it works

```
 Camera (wide) ─► object detection · tracking · time-to-contact ─┐
                  face recognition · text reading (on demand)    │
 LiDAR forward ─► head-height obstacle zones  (works without AI) ─┼─► priority arbiter ─► 3 vibration motors
 LiDAR down    ─► stairs / drop-off / step detector              │                    └► voice (open-ear headset)
 IMU           ─► fall detection                                 │                    └► phone app (BLE): location · SOS
 3 buttons ○△□ ─► read · describe · status / SOS ────────────────┘
 Watchdog: every sensor is monitored, and failures are announced
```

- **Runs offline** on a Raspberry Pi 5, CPU only. No GPU, no cloud.
- **The safety path doesn't depend on AI.** LiDAR warnings keep working if the camera or a neural network fails.
- **Faces never leave the helmet.**

Architecture and every number: [System design specification](docs/en/00-system-design-spec.md)

## Hardware at a glance

Raspberry Pi 5 · Camera Module 3 Wide · 2 × TF-Luna LiDAR · MPU-6050 IMU · 3 coin vibration
motors + ULN2003 · 3 tactile buttons · USB audio + open-ear headset · USB-C power bank in your
pocket · a certified bicycle helmet · 3D-printed PETG/TPU parts.

**No soldering** in the reference build. Every part is printable on a 220 × 220 mm printer.
See the [bill of materials](docs/en/01-bill-of-materials.md) for parts and cost ranges, and the **[buying guide](docs/en/10-buying-guide.md)** for verified purchase links and the most common buying mistakes.

## Repository

| Folder | What | Licence |
|---|---|---|
| [`firmware/`](firmware/) | Python firmware for the helmet (with a PC simulator) | Apache-2.0 |
| [`hardware/`](hardware/) | Parametric OpenSCAD sources, ready-to-print STL, renders, wiring diagram | CERN-OHL-P-2.0 |
| [`app/`](app/) | Phone companion web app (Web Bluetooth): location, SOS, settings | Apache-2.0 |
| [`docs/`](docs/) | Design spec, BOM, wiring, printing, assembly, user guide, safety, tests (English + 한국어) | CC BY 4.0 |
| [`1020210101227.pdf`](1020210101227.pdf) | Original patent publication (Korean) | Public record |

## Get started

**1. Try it on a PC (no hardware needed)**

```bash
cd firmware
pip install -e .[dev]
python -m owsh.tools.download_models
python -m owsh --sim --video path/to/walking_video.mp4
```

The simulator shows detections, the three motor bars and the simulated LiDARs. Keyboard shortcuts are in [firmware/README.md](firmware/README.md).

**2. Build a helmet:**
[Bill of materials](docs/en/01-bill-of-materials.md) → [Buying guide](docs/en/10-buying-guide.md) → [3D printing](docs/en/03-3d-printing-guide.md) → [Wiring](docs/en/02-wiring-guide.md) → [Assembly & setup](docs/en/04-assembly-guide.md) → [Test plan](docs/en/07-test-plan.md)

**3. Phone app:** open [`app/`](app/) on Android Chrome over HTTPS, or use the built-in demo helmet to try it out.

## The whole world is invited

This project only succeeds if it is tested and improved by the people who use it, everywhere.

- **Blind and low-vision walkers, O&M instructors:** field tests and honest feedback ([field test report](.github/ISSUE_TEMPLATE/field_test_report.yml))
- **Makers:** build one, improve the mounts, try cheaper parts
- **Translators:** voice prompts in your language. Safety phrases need review by a native blind speaker ([translation guide](docs/en/09-translation-guide.md))
- **ML engineers:** datasets and detectors for tactile paving, crossings, ramps, elevator buttons
- **Developers:** firmware, native Android/iOS app with automatic SOS, navigation

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Roadmap: [Patent mapping and roadmap](docs/en/08-patent-and-roadmap.md).

## The story

Dr. Lee Il-guk filed this invention in 2021 so that blind people could walk safely, and it was
registered as a Korean patent in 2023. Building the whole system alone once seemed out of
reach. With today's AI tools, including Claude, it has become possible to design it, write
the software and publish everything. So he is giving it to the world for free.
CLSOFTLAB and Dr. Lee Il-guk will keep developing it.

## Licence

- Software: [Apache-2.0](LICENSES/Apache-2.0.txt)
- Hardware: [CERN-OHL-P-2.0](LICENSES/CERN-OHL-P-2.0.txt)
- Documentation: [CC BY 4.0](LICENSES/CC-BY-4.0.txt)
- Patent: [royalty-free pledge](PATENT_PLEDGE.md)

Details in [NOTICE](NOTICE). © 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
