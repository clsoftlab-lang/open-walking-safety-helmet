<!--
SPDX-License-Identifier: Apache-2.0
Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국)
-->

# OWSH phone companion app (PWA)

Phone app for the **Open Walking Safety Helmet**. It is built for people who use a screen reader
(TalkBack on Android, VoiceOver on iOS). It is plain HTML, CSS and JavaScript modules: no build
step, no frameworks, no CDNs. After the first visit it works offline.

The helmet assists a white cane or guide dog. It never replaces them.

Protocol, SOS flow and all behaviour follow `docs/en/00-system-design-spec.md` (§7.3 SOS, §8 BLE).

## What it does

| Feature | Details |
|---|---|
| Connect | Web Bluetooth, Nordic UART Service, devices named `OWSH-…`. Reconnects automatically with exponential backoff (1 s → 30 s) while the app is open. |
| Demo helmet | "Try demo helmet" simulates `hello`, `status`, `alert`, `speech`, `sos`, `need_location`, and replies to `loc`, `ack`, `say`, `cfg`, `ping`. All demo traffic goes through the real encoder, 20 byte chunking and line decoder. |
| Live screen | Connection state, helmet status (problems in plain words, low power, slowing down to cool, camera frame rate, temperature, voice muted; low power is announced once when it starts), and a log of the latest 50 `alert`/`speech` messages. New messages are announced with `aria-live`: assertive for level 0–1, polite for 2–4. A warning appears if no status arrives for 25 s. |
| Location | When connected and turned on in Settings, sends `loc` every 10 s and immediately on `need_location`. Never sends a fix older than 60 s. |
| Street address | Off by default. When on, uses OpenStreetMap Nominatim at most once per 30 s, caches results, adds `addr` to `loc`. |
| SOS | `countdown` → full-screen alert (cancel with any helmet button). `sent` → `ack`, WebAudio siren with pauses (so the screen reader stays audible), vibration, location, big **Call emergency number** (`tel:`) and **Send SMS to guardians** (`sms:` with an OpenStreetMap link) buttons, **I'm OK**. |
| Settings | Language (system / English / 한국어), emergency number with country presets (editable), 3 guardian numbers, helmet mute / volume / drop-off sensitivity (`cfg`), location sharing, address lookup, keep screen on. Stored only on the phone (`localStorage`, with a memory fallback). |

## Pairing (encrypted Bluetooth)

The helmet only accepts phones that are **paired (bonded)** with it, over an encrypted link.

- Pairing is "Just Works": the first time you connect, the phone's operating system shows a pairing
  request. Accept it. No code is needed.
- A new phone can pair only while **no phone is paired** with the helmet, or during the **first
  120 seconds after the helmet starts**. At other times an unpaired phone is refused.
- **If connection is refused, restart the helmet and connect within 2 minutes.**
- If you removed the helmet from your phone's Bluetooth settings, the helmet still remembers the old
  pairing: restart the helmet and connect within 2 minutes to pair again.

When a Bluetooth operation fails because the link is not authenticated ("not paired",
"insufficient authentication", "not authorized"), the app shows this advice on the connect and
helmet screens instead of a generic error. The connect screen shows a short version of this help.

## Run it locally

Web Bluetooth and service workers need a secure context: `https://…` or `http://localhost`.

```sh
cd app
python -m http.server 8123
# or: npx --yes http-server . -p 8123 -c-1
```

Open <http://localhost:8123>. To test with a real helmet from a phone, serve over HTTPS (for
example GitHub Pages) because a phone cannot reach your computer as `localhost`.

## Tests

Node 20 or newer, no dependencies:

```sh
cd app
node --test tests/
```

- `tests/protocol.test.mjs`: encode, chunking to MTU − 3, streaming decode with Korean text split in
  the middle of a character, unknown types ignored, malformed and over-long lines, builders, backoff.
- `tests/i18n.test.mjs`: `en.json` and `ko.json` have the same keys and placeholders; every key used
  in the HTML and JavaScript exists.
- `tests/sos.test.mjs`: `tel:`/`sms:` links, SMS text with map link, Nominatim rate limit, settings.

## Host on GitHub Pages

Publish the `app/` folder (for example with a Pages workflow that uploads `app/`, or by copying it
to a `gh-pages` branch). All paths are relative, so it works under `https://<user>.github.io/<repo>/`.
When you change any file, bump `CACHE_VERSION` in `sw.js` so installed apps update.

## Files

```
index.html            screens, SOS dialog, live regions
styles.css            high-contrast light/dark themes, 48 px targets, reduced motion
manifest.webmanifest  install metadata
sw.js                 offline cache (cache-first, same-origin only)
js/protocol.js        pure protocol: constants, encode, chunk, LineDecoder, message builders
js/ble.js             Web Bluetooth transport, reconnect with backoff, support detection
js/sim.js             demo helmet
js/app.js             screens, rendering, wiring
js/sos.js             SOS screen, alarm tone, tel/sms links
js/location.js        geolocation sharing, Nominatim reverse geocoder
js/settings.js        settings storage, country emergency presets
js/i18n.js            translations loader
i18n/en.json, ko.json strings (keep keys identical)
icons/                app icon and maskable icon (SVG)
tests/                node --test
```

## Platform limits (please read)

- **iPhone and iPad:** Safari and every other iOS browser have no Web Bluetooth. Use the free
  third-party **Bluefy** browser to connect a real helmet. The demo helmet works everywhere.
- **Firefox and desktop Safari** do not support Web Bluetooth. Use Chrome or Edge on Android,
  Windows, macOS or ChromeOS.
- **Screen off / app in background:** phones pause web pages. Bluetooth notifications, location
  sharing and the SOS alarm can stop until the app is visible again. The app can keep the screen on
  while connected (Screen Wake Lock, on by default). A native app is needed for reliable background
  operation (roadmap).
- **No automatic calls or SMS:** a web app cannot place a call or send an SMS by itself. The user
  or a bystander must confirm in the phone's dialer or messages app (spec §7.3).
- **Alarm sound** needs the browser to allow audio. The app unlocks audio when you tap Connect or
  Try demo helmet; if audio is still blocked, the SOS screen shows a **Sound alarm** button.
- **Vibration** is not available on iOS.
- **MTU:** Web Bluetooth does not expose the negotiated MTU, so writes use 20 byte chunks.
- **Emergency number presets** are a starting point. Always check the number where you live.
- **Device chooser filter:** the chooser filters on the `OWSH-` name prefix; the Nordic UART Service
  is required after connecting (a 128-bit UUID and the name do not fit in one advertisement packet).

## Privacy

- Settings, guardian numbers and the message log stay on the phone.
- Location goes only from the phone to the helmet, and only when sharing is turned on.
- Address lookup is off by default. When on, coordinates are sent to the OpenStreetMap Foundation's
  Nominatim service (at most 1 request per 30 s; the browser identifies the app by its Referer
  origin, as browsers cannot set a User-Agent). Address data © OpenStreetMap contributors, ODbL.
- During SOS the phone reads its location to show it and to put it in the SMS text, even if sharing
  is off. Nothing is sent until the user taps Call or SMS and confirms.

## Accessibility checklist

- Semantic landmarks, headings, lists, `fieldset`/`legend`, labelled controls.
- Focus moves to the new screen's heading on every screen change and to the SOS heading.
- Minimum 48 × 48 px targets; tested without horizontal scrolling at 320 px width.
- High-contrast light and dark themes; information is never shown by colour alone
  (text + symbols for levels and connection state).
- `prefers-reduced-motion` and forced-colors supported; the `lang` attribute follows the language.
- New translations: add `i18n/<lang>.json` with the same keys and add the language to
  `SUPPORTED_LANGUAGES` in `js/i18n.js`. Safety phrases must be reviewed by a native speaker who is
  blind or an O&M instructor before the language is marked verified (see the spec).

## License

Apache-2.0. Copyright 2026 CLSOFTLAB (씨엘소프트랩), Dr. Lee Il-guk (이일국).
Patent KR 10-2560496 released free by CLSOFTLAB, Dr. Lee Il-guk. See the repository root for
`LICENSE`, `NOTICE` and `PATENT_PLEDGE.md`.
