# Security Policy

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

In this project, a security bug can become a safety bug: someone who can silence warnings or make the helmet say false
things could put a blind person in danger. Please report vulnerabilities **privately**.

한국어 안내: 보안 취약점은 공개 이슈로 올리지 말고, 아래 GitHub Security Advisories로 비공개 제보해 주십시오.
한국어로 작성하셔도 됩니다.

## How to report

1. Go to this repository on GitHub.
2. Open the **Security** tab.
3. Choose **Report a vulnerability**. This opens a private advisory that only you and the maintainers can see.
   (GitHub documentation: [Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).)

**Do not** open a public issue, pull request or discussion for a vulnerability.

Please include:

- What is affected (firmware, app, protocol, setup script, hardware).
- Firmware commit or release, and hardware used.
- Steps to reproduce, or a proof of concept.
- What an attacker could do, and what it would mean for a user walking with the helmet.
- Whether you believe it is being exploited.

You may write in English or Korean.

## What to expect

- We aim to acknowledge your report within **7 days**.
- We will keep you informed while we investigate and fix it.
- We coordinate disclosure with you. Our target is a fix or mitigation within **90 days**, sooner for issues that affect
  user safety.
- We credit reporters in the advisory unless you prefer to stay anonymous.
- We will not take legal action against good-faith research that follows this policy, avoids harm to users and
  privacy, and does not test against helmets that people are using.

## Scope

In scope:

- **BLE link, protocol and security** (spec §8, §8.3): for example getting a non-bonded device's messages accepted,
  pairing outside the pairing window, bypassing the spoken confirmations for mute / low drop-off sensitivity / low
  volume, getting past the `say` priority cap or rate limit, or suppressing SOS acknowledgements.
- Firmware: crashes or hangs that can be triggered remotely, ways to stop FAULT reporting, unsafe handling of files
  or models.
- Phone app: injection into the speech log, leaking location, guardian numbers or SOS data.
- Face data: any way to extract photos or embeddings from a helmet over the air.
- `firmware/scripts/setup_pi.sh`, the `owsh` and `owsh-bt-agent` systemd services, and the sudoers rule that lets the
  safe-shutdown gesture run `systemctl poweroff`: privilege or supply-chain issues, unsafe downloads.
- CI workflows in `.github/workflows/`.

Out of scope:

- Physical access attacks on a helmet you own (for example reading the microSD card). Please still tell us through a
  normal issue if you have ideas to reduce the risk.
- Denial of service by radio jamming.
- Vulnerabilities in third-party dependencies without a demonstrated impact on this project. Please report those
  upstream, and let us know if we should update.

## Known limitations

- The BLE link is encrypted and only bonded phones are accepted (`ble.security: encrypt`, `ble.bonded_only: true`).
  Pairing uses **Just Works**, because the helmet has no display or keypad. Just Works does not protect against a
  man-in-the-middle **during** pairing. Pairing is open while no phone is bonded, and afterwards only for 120 s after
  each boot; every new pairing is announced by voice.
- `ble.security: authenticated` exists but needs a passkey agent; it is not the default.
- A lost or stolen bonded phone keeps its access until its pairing is removed.
- See the [safety guide](docs/en/06-safety.md#8-bluetooth-security) for user-facing advice. Proposals for stronger
  pairing that stays accessible to blind users are welcome.

## Supported versions

Security fixes are made for the latest release and the `main` branch. Please update to the latest release before
reporting, if you can.
