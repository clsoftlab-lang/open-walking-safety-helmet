## What does this change?

<!-- A short, plain-language description. Link the issue: "Closes #123". 한국어로 작성하셔도 됩니다. -->

## Why?

<!-- The problem it solves, and for whom. -->

## Area

- [ ] Firmware
- [ ] Hardware (OpenSCAD / STL / wiring)
- [ ] Phone app
- [ ] BLE protocol
- [ ] Documentation (English / Korean)
- [ ] Translation (voice / app)
- [ ] CI / tooling

## Safety impact

<!-- See CONTRIBUTING.md §6 and GOVERNANCE.md §4. When in doubt, choose "Yes". -->

- [ ] **No safety impact.** This cannot change whether, when or how a user is warned, or how the helmet protects the head.
- [ ] **Safety-critical.** It touches alert logic, thresholds, the haptic language, speech priority or mute, buttons,
      safe shutdown or SOS, the BLE protocol or its security, power warnings, P0–P2 voice phrases, fault reporting,
      mounting, module height or the power cable.

If safety-critical:

- What could go wrong for a user walking with the helmet?
- What will the user notice?
- Hardware test evidence (test plan IDs and results, or "not yet tested on hardware" and why):

## Checklist

- [ ] **Spec updated** (`docs/en/00-system-design-spec.md` and `docs/ko/00-시스템설계서.md`), or no behaviour, pin,
      dimension, threshold, pattern, button, SOS or protocol change.
- [ ] **Tests** added or updated, and passing locally:
      `cd firmware && python -m pytest -q` · `cd app && node --test tests/*.test.mjs` · OpenSCAD renders for changed parts.
- [ ] **Test plan** procedures run where relevant (T1–T12), results included above.
- [ ] **STL re-rendered** and committed for changed `.scad` files (hardware only).
- [ ] **Documentation** updated in English, and Korean updated or help requested.
- [ ] **Accessibility** checked for app or doc changes (screen reader, headings, alt text, no colour-only information).
- [ ] **Licences:** new dependencies or models are Apache-2.0, MIT or BSD only.
- [ ] **Privacy:** no face data, location or personal information leaves the helmet or appears in logs, fixtures or media
      without consent.
- [ ] **Helmet integrity:** nothing drills, cuts, glues into or replaces the certified helmet.
- [ ] **All commits are signed off** (`git commit -s`, DCO).
