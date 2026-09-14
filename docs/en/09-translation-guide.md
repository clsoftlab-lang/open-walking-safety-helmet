# 09 · Translation Guide

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

The helmet speaks to people in the middle of a street. A translation here is safety equipment.
A warning that is slow to say, easy to mishear or ambiguous can hurt someone. This guide explains how
to add a language carefully, and how it becomes **verified**.

## Contents

1. [What can be translated](#1-what-can-be-translated)
2. [The "verified" rule](#2-the-verified-rule)
3. [Adding a voice language (helmet)](#3-adding-a-voice-language-helmet)
4. [Adding an app language](#4-adding-an-app-language)
5. [Writing good safety phrases](#5-writing-good-safety-phrases)
6. [Glossary of safety terms](#6-glossary-of-safety-terms)
7. [Review checklist for verification](#7-review-checklist-for-verification)
8. [Translating the documentation](#8-translating-the-documentation)
9. [Language status](#9-language-status)

## 1. What can be translated

| What | File | Used for |
|---|---|---|
| Helmet voice messages | `firmware/owsh/i18n/<lang>.json` | Everything the helmet says (spec §7.1) |
| Phone app interface | `app/i18n/<lang>.json` | Buttons, labels, screen reader text, SOS screen, SMS text |
| Sign danger keywords | `ocr.danger_keywords.<lang>` in `firmware/config/default.yaml` | OCR adds "Warning sign:" when a sign contains these words (spec §5.5) |
| Documentation | `docs/<lang>/` | Guides like this one |

`<lang>` is a language code, for example `es`, `fr`, `pt`, `ar`, `hi`, `zh-CN`, `ja`, `sw`.
Use a region suffix only when the difference matters for safety or clarity (for example `pt-BR`, `zh-TW`).

Reference files: [`firmware/owsh/i18n/en.json`](../../firmware/owsh/i18n/en.json),
[`firmware/owsh/i18n/ko.json`](../../firmware/owsh/i18n/ko.json), and the app files in [`app/i18n/`](../../app/i18n/).

## 2. The "verified" rule

From the spec's global project rules:

- `en` and `ko` are maintained by the core team.
- Any other language is welcome, but it is marked **verified** only after review by **a native speaker who is
  blind, or an O&M instructor** who is a native speaker.
- **Unverified languages still ship,** with a first-boot notice telling the user the language has not been
  verified yet.

Why this rule? Sighted translators often write phrases that read well but sound unclear when heard once, in
traffic, through a bone-conduction headset. People who rely on speech every day, and people who teach
independent travel, catch those problems.

How verification happens:

1. The translator opens a pull request with the language files.
2. A reviewer who meets the rule reviews the **voice phrases** with the checklist in
   [section 7](#7-review-checklist-for-verification), ideally by listening to them through the helmet or the simulator.
3. The reviewer comments on the pull request: which role they have (blind native speaker or O&M instructor),
   that they listened to the phrases, and what they changed. They may stay anonymous publicly; maintainers may
   confirm privately.
4. A maintainer adds the language code to `VERIFIED_LANGS` in `firmware/owsh/i18n/__init__.py` (this switches off
   the first-boot notice) and updates the [language status table](#9-language-status).
5. Any later change to a safety phrase (level P0–P2) needs a new review for that phrase.

## 3. Adding a voice language (helmet)

1. **Open an issue** with the [translation form](../../.github/ISSUE_TEMPLATE/translation.yml), so others know
   you are working on it.
2. **Copy** `firmware/owsh/i18n/en.json` to `firmware/owsh/i18n/<lang>.json`.
3. **Translate only the values.** Keep every key exactly as it is.
4. **Keep `{placeholders}` unchanged**, for example `{name}`, `{what}` or `{count}`. You may move them within the sentence.
5. **Keep every key.** The firmware tests check that each language file has exactly the same keys and
   `{placeholders}` as `en.json`. If you cannot translate a phrase yet, leave the English text as the value and list
   it in the pull request. (At run time a missing phrase falls back to English, so it never silences a warning, but
   the tests will still fail.)
6. **Check the speech engine.** The default engine on the Pi is `espeak-ng`. Check your language exists:
   ```bash
   espeak-ng --voices | grep -i <lang>
   espeak-ng -v <lang> "your translated warning"
   ```
   If `espeak-ng` pronounces it badly, note it in the pull request. A `piper` voice may be better (spec §7.1).
7. **Add danger keywords** for sign reading under `ocr.danger_keywords` in `firmware/config/default.yaml`, as a new
   `<lang>:` list (for example the words for "danger", "caution", "wet floor", "construction"). Text reading in a new
   script may also need a recognition model for that script (`ocr.rec_model_path`) and an entry in `ocr.languages`.
8. **Listen in the simulator** on a PC, with your language selected:
   ```bash
   python -m owsh --sim --lang <lang>
   ```
   Press the simulated buttons and move the LiDAR sliders so each warning is spoken.
9. **Validate the JSON** and run the tests (they check key and placeholder parity):
   ```bash
   python -m json.tool firmware/owsh/i18n/<lang>.json > /dev/null
   cd firmware && python -m pytest -q
   ```
10. **Open a pull request.** Say whether a reviewer who meets the verified rule is available.

Format rules:

- UTF-8, no byte-order mark, 2-space indentation, no trailing commas.
- Keep the same key order as `en.json` so diffs are easy to review.
- Numbers and units: the firmware inserts numbers. Write units the way they are spoken
  ("metres", not "m"). Metric is the default; imperial is selectable for voice.
- Plurals: object names have two keys, `.one` and `.many` (for example `class.person.one` and
  `class.person.many` with `{count}`). If your language needs more forms, choose a phrasing that works for any
  number, and mention it in the pull request.

Example entries from `en.json`:

```json
{
  "obstacle.stop": "Stop.",
  "obstacle.ahead": "Obstacle ahead.",
  "approach.p2.right": "{what} approaching from the right.",
  "class.person.many": "{count} people",
  "face.friend.left": "{name} is ahead on the left."
}
```

## 4. Adding an app language

1. Copy `app/i18n/en.json` to `app/i18n/<lang>.json`.
2. Translate values; keep every key and `{placeholder}` (the app tests check this too).
3. Add the language code to `SUPPORTED_LANGUAGES` in `app/js/i18n.js`.
4. **Screen reader text matters as much as visible text.** Labels for buttons and status must make sense when read alone.
5. **The SOS screen and the SMS text are safety text.** The SMS goes to guardians and may be read by emergency
   services. Keep it short and clear: who needs help, that it is an emergency, and the map link.
6. **Emergency numbers are never translated into the text.** They are a per-country setting. Do not write
   "call 112" or "call 911" into a string.
7. For right-to-left languages (for example `ar`), check that the layout is mirrored and the screen reader reads in the right order.
8. Run the app tests with Node 22 (`cd app && node --test tests/*.test.mjs`), then open the app on a phone with the screen reader on (TalkBack or VoiceOver) and
   go through every screen.

## 5. Writing good safety phrases

Priority P0–P2 messages (spec §6.1) are the most important. When writing them:

- **Short.** A warning must finish before the hazard arrives. Aim for one to three words. "Stop" must be as short
  as your language allows.
- **Action first** when the phrase asks for action. Use a direct imperative. Avoid polite forms that add syllables
  or sound optional, unless the direct form is offensive in your culture.
- **Hard to mishear.** "Step up" and "Step down" must sound clearly different, not just by one short syllable.
  If they are too similar, change the wording (for example "Step down" versus "Kerb up").
- **Left and right** are always from the wearer's point of view.
- **One word, one meaning.** Use the same word for the same thing everywhere. Do not switch between synonyms.
- **No jokes, no idioms, no regional slang** in warnings.
- **Test in noise.** Listen to the phrase with street noise playing, through an open-ear headset, at a normal volume.
- **Keep the message ids' meaning.** Do not merge two messages into one, or change what a message warns about.

## 6. Glossary of safety terms

Translate these consistently, in both the helmet and the app. The Korean column shows the reference translation
used by the core team.

| Term (English) | Meaning and notes | Korean reference |
|---|---|---|
| Stop | Stop walking now. Shortest possible form. Spoken for Z1 obstacles. | 멈추세요 |
| Obstacle ahead | Something at head height 0.6–1.2 m ahead. | 앞에 장애물 |
| Step down ahead | A step, kerb or stairs going down. | 앞에 내려가는 턱 |
| Drop ahead | A deeper drop: platform edge, stairs, hole. | 앞에 추락 위험 |
| Step up ahead | A step up or a low obstacle. Must sound clearly different from "step down". | 앞에 올라가는 턱 |
| approaching | Moving toward the wearer. Used with an object and a side. | 접근 |
| left / right | From the wearer's point of view. | 왼쪽 / 오른쪽 |
| ahead | In front of the wearer. | 앞 |
| person, bicycle, car, motorcycle, bus, truck, dog | Detector classes that can approach. Use everyday words. | 사람, 자전거, 자동차, 오토바이, 버스, 트럭, 개 |
| Warning sign: | Prefix before reading a sign with danger words. | 경고 표지: |
| Emergency alert | The SOS function. Must not be confused with a normal notification. | 긴급 신고 |
| Emergency alert in 10 seconds. Press any button to cancel. | SOS countdown. | 10초 뒤 긴급 신고를 보냅니다. 취소하려면 아무 버튼이나 누르세요. |
| Sending emergency alert to the phone. | The helmet is still trying to reach the phone. Must not sound like "sent". | 휴대폰으로 긴급 신고를 보내는 중입니다. |
| Emergency alert sent | Spoken only after the phone confirmed it received the alert. | 긴급 신고를 보냈습니다 |
| cancel / cancelled | Stop the SOS countdown. | 취소 / 긴급 신고를 취소했습니다 |
| Phone not connected | The helmet cannot reach the phone. | 휴대폰이 연결되지 않았습니다 |
| fault | A part of the helmet stopped working. Do not soften it to "problem" or "issue" if that sounds minor. | 고장 |
| Camera is covered or too dark | Camera blocked fault. | 카메라가 가려졌거나 너무 어둡습니다 |
| Distance sensors still active | LiDAR warnings still work. | 거리 센서는 계속 작동합니다 |
| recovered | A failed part works again. | 복구됨 |
| muted / unmuted | Low-priority speech off / on. Warnings and answers to button presses are still spoken. | 음성 안내를 끕니다 / 음성 안내를 켭니다 |
| Shutting down. | Safe shutdown started (B1 + B3 held 5 s). | 전원을 끕니다. |
| Power is low. Charge the battery soon. | Under-voltage warning. The helmet may stop soon. | 전원이 부족합니다. 곧 배터리를 충전하세요. |
| Helmet is overheating. | CPU too hot; warnings from the camera may be slower. | 헬멧이 과열되었습니다. |
| Voice info muted by phone. Warnings are still spoken. | Safety-reducing change made from the phone; always spoken. | 휴대폰에서 음성 안내를 껐습니다. 위험 경고는 계속 말합니다. |
| Drop-off sensitivity set to low by phone. | Safety-reducing change made from the phone; always spoken. | 휴대폰에서 낙차 감지 민감도를 낮춤으로 바꿨습니다. |
| Volume set to {volume} percent by phone. | Volume below 30 % set from the phone; always spoken. | 휴대폰에서 음량을 {volume}퍼센트로 바꿨습니다. |
| New phone paired: {name}. | A phone was paired. If the user did not do it, it is a security warning. | 새 휴대폰이 등록되었습니다: {name}. |
| friend | An enrolled person the wearer wants to know about. | 지인 |
| person to avoid | An enrolled person the wearer wants a warning about. Neutral wording, not insulting. | 피하고 싶은 사람 |
| Text reading is not installed | OCR not available. | 문자 읽기 기능이 설치되어 있지 않습니다 |
| Where am I | Location request. | 여기가 어디예요 / 현재 위치 |
| metre(s) | Distance unit, spoken form. | 미터 |
| Call emergency number | App button. The number itself comes from settings. | 긴급 전화 걸기 |
| Send SMS to guardians | App button. | 보호자에게 문자 보내기 |
| guardian | A trusted contact who receives SOS messages. | 보호자 |

## 7. Review checklist for verification

The reviewer (a native speaker who is blind, or an O&M instructor) checks each P0–P2 phrase:

- [ ] I listened to it through the helmet or the simulator, not only read it.
- [ ] I understood it the first time, with street noise in the background.
- [ ] It is short enough to act on while walking.
- [ ] It tells me what to do or what is there, without ambiguity.
- [ ] "Step up" and "step down" (or equivalents) cannot be confused.
- [ ] Left and right are from my point of view.
- [ ] The same thing is called the same way in every message.
- [ ] The tone is right: urgent where needed, never alarming for information messages.
- [ ] The speech engine pronounces it correctly.
- [ ] The first-boot message clearly says the helmet assists and does not replace the cane or guide dog.

For the app:

- [ ] Every screen works with the screen reader.
- [ ] The SOS screen and SMS text are clear to a stranger reading them.

## 8. Translating the documentation

- Documentation translations are welcome under `docs/<lang>/`. Start with the user guide and safety pages, because
  they matter most to users.
- Keep the licence line at the top of each page, translated.
- Keep every number, pin, command and file name unchanged.
- Write natural text for your readers, not a word-by-word translation.
- Add your language to [`docs/README.md`](../README.md).

## 9. Language status

| Code | Language | Voice (helmet) | App | Status |
|---|---|---|---|---|
| `en` | English | core team | core team | Maintained by the core team; listed in `VERIFIED_LANGS`. Further review by blind native speakers is welcome. |
| `ko` | 한국어 (Korean) | core team | core team | Maintained by the core team; listed in `VERIFIED_LANGS`. Further review by blind native speakers is welcome. |
| other | — | — | — | Not yet available. [Open a translation issue.](../../.github/ISSUE_TEMPLATE/translation.yml) |

When a language is verified, the maintainer adds the reviewer role and date here.
