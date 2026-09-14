# Contributing

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

Thank you for helping. This project exists so that blind people everywhere can walk like anyone else, and it only
gets there with people from many countries, backgrounds and abilities.

**Blind and low-vision contributors are especially welcome,** as testers, reviewers, developers, writers and
maintainers. If any part of this process is not accessible to you, tell us and we will fix the process.

한국어 안내: 이슈와 풀 리퀘스트는 영어가 기본이지만 **한국어도 환영합니다.** 영어가 어려우면 한국어로 쓰셔도
됩니다. 메인테이너가 필요하면 번역해서 함께 적어 두겠습니다.

## Contents

1. [Ground rules](#1-ground-rules)
2. [Ways to contribute](#2-ways-to-contribute)
3. [Issues](#3-issues)
4. [Pull requests](#4-pull-requests)
5. [Developer Certificate of Origin (DCO) sign-off](#5-developer-certificate-of-origin-dco-sign-off)
6. [Safety review for alert logic](#6-safety-review-for-alert-logic)
7. [Firmware](#7-firmware)
8. [Hardware](#8-hardware)
9. [Phone app](#9-phone-app)
10. [Translations](#10-translations)
11. [Datasets](#11-datasets)
12. [Field tests](#12-field-tests)
13. [Documentation](#13-documentation)
14. [Licences of contributions](#14-licences-of-contributions)

## 1. Ground rules

- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- **The spec comes first.** [`docs/en/00-system-design-spec.md`](docs/en/00-system-design-spec.md) is the single source
  of truth. If your change affects pins, dimensions, thresholds, the haptic language, buttons, SOS or the protocol,
  change the spec in the same pull request (or first), then the implementation.
- **Never weaken helmet protection** (spec P1, P2). Pull requests that drill, cut, glue into or replace the certified
  helmet will not be accepted.
- **Permissive licences only** in the default build: Apache-2.0, MIT, BSD (spec P9). No AGPL or GPL-linked libraries,
  no models with non-commercial or unclear licences.
- **Offline first** (spec P6). Hazard warnings must never depend on the internet or the phone.
- **Security problems are reported privately.** See [SECURITY.md](SECURITY.md). Do not open a public issue.

## 2. Ways to contribute

| You are | You could |
|---|---|
| Blind or low-vision walker | Test a helmet, report what works and what does not, review voice phrases in your language |
| O&M instructor | Run user trials ([07 · Test plan](docs/en/07-test-plan.md) T12), review the user guide and haptic language |
| Maker | Build one, improve mounts and printed parts, try cheaper or more available parts |
| Firmware developer | Fix bugs, add tests, improve performance on the Pi, work on roadmap items |
| App developer | Improve the web app, accessibility, or start a native Android or iOS app |
| ML engineer | Datasets and detectors for tactile paving, crossings, ramps, elevator buttons |
| Translator | Voice and app strings, and documentation |
| Writer, designer | Clearer guides, diagrams, accessible formats (braille-ready, large print, audio) |

Roadmap and open questions: [08 · Patent mapping and roadmap](docs/en/08-patent-and-roadmap.md).

## 3. Issues

- Write issues in **English** so people worldwide can follow. **Korean is welcome** too; please add a short English
  summary if you can, or a maintainer will.
- Choose a form:
  - [Bug report](.github/ISSUE_TEMPLATE/bug_report.yml)
  - [Feature request](.github/ISSUE_TEMPLATE/feature_request.yml)
  - [Field test report](.github/ISSUE_TEMPLATE/field_test_report.yml)
  - [Translation](.github/ISSUE_TEMPLATE/translation.yml)
- **Mark safety-related problems clearly**, for example a missed drop-off, a false "all clear", a module that did not
  break away, or a FAULT that was not announced. These are triaged first.
- **Remove personal information**: names, faces, exact home addresses, phone numbers.
- Search existing issues first.

## 4. Pull requests

1. Open or find an issue first for anything bigger than a typo, so work is not duplicated.
2. Fork the repository and create a branch, for example `fix/dropoff-cooldown` or `docs/es-user-guide`.
3. Keep the pull request focused on one change.
4. Update the spec, tests and documentation that your change affects. **User-facing guides exist in English and
   Korean.** If you cannot update the Korean version, say so in the pull request, and a maintainer will help.
5. Run the checks locally (see the sections below).
6. **Sign off every commit** (DCO, next section).
7. Fill in the [pull request checklist](.github/PULL_REQUEST_TEMPLATE.md), including **safety impact**.
8. Be patient and kind in review. Reviewers are volunteers too.

Commit messages: a short summary line (imperative, ≤ 72 characters), a blank line, then why the change is needed.

Continuous integration runs firmware tests on Python 3.11 and 3.12, the app tests on Node 22, and an OpenSCAD render smoke test
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## 5. Developer Certificate of Origin (DCO) sign-off

We use the [Developer Certificate of Origin 1.1](https://developercertificate.org/). By signing off, you certify that you
wrote the contribution or otherwise have the right to submit it under the project's licences.

Add a sign-off line to every commit:

```bash
git commit -s -m "Fix drop-off cooldown after re-learning"
```

This adds:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use your real name or a consistent, identifiable pseudonym, and an email address you can be contacted at.
To sign off commits you already made: `git rebase --signoff main` (then force-push your branch).

## 6. Safety review for alert logic

Some changes can make someone walk into danger. They need a **safety review** before merge, as defined in
[GOVERNANCE.md](GOVERNANCE.md).

A safety review is required for any change to:

- Hazard logic: `firmware/owsh/arbiter.py`, `firmware/owsh/sensors/reflex.py`, `firmware/owsh/sensors/imu.py`,
  `firmware/owsh/vision/tracker.py`, `firmware/owsh/watchdog.py`, `firmware/owsh/sensors/power.py`
- Thresholds and defaults in `firmware/config/default.yaml` that affect warnings, drop-off, fall detection or faults
- The haptic language (spec §6), haptic engine or mixer (`firmware/owsh/output/haptics.py`)
- Speech priority, mute or queue rules (`firmware/owsh/output/audio.py`)
- Buttons, safe shutdown and SOS behaviour (`firmware/owsh/input/buttons.py`), and the SOS screen in the app
- The BLE protocol and its security (spec §8, §8.3: encryption, bonding, pairing window, spoken confirmations, `say`
  limits) in `firmware/owsh/link/`, the pairing agent service, and anything that lets the phone change settings
- **P0–P2 voice phrases** in any language
- Mechanical mounting, protrusion, breakaway behaviour, or the power cable

What the pull request must include:

- The spec change, if behaviour changes.
- Tests that cover the change (`firmware/tests/`).
- Evidence: which [test plan](docs/en/07-test-plan.md) procedures you ran (for example T2, T4, T5, T8) and the results,
  or a clear statement that hardware testing is still needed.
- A plain-language description of what a user will notice.

## 7. Firmware

Python ≥ 3.11. You do not need hardware to start: the simulator runs on any PC.

```bash
pip install -e "firmware[dev]"
cd firmware
python -m pytest -q
python -m owsh --sim            # add --video path/to/walk.mp4 to use a video instead of a webcam
```

See [`firmware/README.md`](firmware/README.md) for the simulator keys, including fault injection, safe shutdown
and power warnings.

- Follow the layout in spec §9. One thread per subsystem; communicate through the event bus.
- Pure logic (arbiter, reflex, protocol, mixer) must be testable without hardware. Add tests for every fix.
- The LiDAR reflex path must keep working without the camera or neural networks (P5).
- Every subsystem must publish heartbeats; failures must produce FAULT (P4).
- Keep dependencies small and permissively licensed. Hardware libraries go in extras (`pi`, `ocr`, `ble`).

## 8. Hardware

- OpenSCAD sources in `hardware/openscad/`, one file per printable part, shared code in `hardware/openscad/lib/`.
- Dimensions are parameters. Measure real parts with calipers and document what you measured.
- **Commit the re-rendered STL** in `hardware/stl/` together with the `.scad` change, so non-CAD users can print it.
  Update a PNG preview in `hardware/renders/` if the shape changes visibly.
- Check that the part still renders headless: `openscad -o /tmp/x.stl hardware/openscad/<part>.scad`, or re-export
  everything with `hardware/scripts/render_all.sh` (Windows: `render_all.ps1`).
- Keep heights above the shell within spec P2 (front pod ≤ 35 mm, main case ≤ 40 mm, all other modules ≤ 30 mm),
  curved undersides on a uniform 3 mm saddle with no gaps > 5 mm, outer fillets ≥ 3 mm, strap slots 21 × 3.2 mm, and
  the part printable on a 220 × 220 × 250 mm printer. Update the measured numbers in `hardware/README.md`.
- Wiring changes: update `hardware/wiring/`, the spec pin map (§4.2), and the [wiring guide](docs/en/02-wiring-guide.md) together.
- Include photos of printed and fitted parts in the pull request.

## 9. Phone app

- The web app lives in `app/` and uses Web Bluetooth.
- Run the tests with Node 22: `cd app && node --test tests/*.test.mjs`.
- **Accessibility is a requirement, not a feature.** Test every change with TalkBack (Android) or VoiceOver (iOS),
  and with large text. The SOS screen must be usable by a stressed bystander who has never seen the app.
- Never hard-code an emergency number. It is a per-country setting.
- The protocol implementation must match spec §8.

## 10. Translations

See the [translation guide](docs/en/09-translation-guide.md). In short:

- Voice: `firmware/owsh/i18n/<lang>.json`. App: `app/i18n/<lang>.json`.
- Keep keys and `{placeholders}`; translate values.
- A language is **verified** only after review by a native speaker who is blind, or an O&M instructor.
- Open a [translation issue](.github/ISSUE_TEMPLATE/translation.yml) first.

## 11. Datasets

We need images for accessible-facility detection, elevator panels, and rain and fog (roadmap v1.2, v1.3).

- Read the dataset call in [08 · Patent mapping and roadmap](docs/en/08-patent-and-roadmap.md#63-v13--accessible-facility-detector--call-for-dataset-contributors-worldwide).
- **Blur faces and licence plates before uploading.** Only photograph people who agreed.
- Contribute under **CC BY 4.0** or **CC0**, and only images you have the right to share.
- Do not commit large datasets to this repository. Open a feature request describing the data, and a maintainer will
  agree where to host it.

## 12. Field tests

Field tests are the most valuable contribution of all.

- Follow [06 · Safety](docs/en/06-safety.md) and [07 · Test plan](docs/en/07-test-plan.md).
- Always walk with the cane or guide dog, and with an O&M instructor or sighted companion for early tests.
- Submit results with the [field test report form](.github/ISSUE_TEMPLATE/field_test_report.yml). Failures and
  missed hazards are as important as successes.
- Remove personal information and get consent for any photos or video.

## 13. Documentation

- Guides live in `docs/en/` and `docs/ko/`. Keep them in sync; link between them with relative links.
- Short sentences, concrete steps, honest limitations. No marketing language.
- Write for screen readers: real headings, lists, meaningful link text, alt text for images. If a table carries
  critical information, also give it as a list.
- Keep the licence line at the top of each page.

## 14. Licences of contributions

By contributing, you agree that your contribution is licensed under the licence of the part you change
(see [NOTICE](NOTICE)):

- Software (`firmware/`, `app/`, scripts, CI): Apache-2.0
- Hardware (`hardware/`): CERN-OHL-P-2.0
- Documentation (`docs/`, README files, images): CC BY 4.0

The patent is covered by the [patent pledge](PATENT_PLEDGE.md).
