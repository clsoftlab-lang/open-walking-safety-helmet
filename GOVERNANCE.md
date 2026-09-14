# Governance

> Part of the Open Walking Safety Helmet · Licensed CC BY 4.0 · © 2026 CLSOFTLAB, Dr. Lee Il-guk

This document explains who decides what, and how. It is deliberately simple, and it will change as the community grows.

한국어 요약: 프로젝트 책임자는 씨엘소프트랩(CLSOFTLAB) 이일국 박사입니다. 일반적인 변경은 메인테이너 검토로 결정하고,
경보 로직처럼 안전에 영향을 주는 변경은 안전 검토자를 포함한 두 명의 승인과 시험 근거가 있어야 합니다.
시각장애인 사용자와 보행지도사의 의견을 결정에 반드시 반영합니다.

## Contents

1. [Principles](#1-principles)
2. [Roles](#2-roles)
3. [How ordinary decisions are made](#3-how-ordinary-decisions-are-made)
4. [How safety-critical decisions are made](#4-how-safety-critical-decisions-are-made)
5. [Safety incidents](#5-safety-incidents)
6. [Releases](#6-releases)
7. [Becoming a maintainer](#7-becoming-a-maintainer)
8. [Changing this document](#8-changing-this-document)

## 1. Principles

- **The mission decides:** blind and low-vision people walking as freely and safely as anyone else.
- **Safety over features, evidence over opinion.**
- **Nothing about us without us.** Decisions that affect users are made with blind and low-vision people and O&M
  instructors, not only for them.
- **Open by default.** Decisions and their reasons are recorded in public issues and pull requests, except security
  and conduct matters.
- **The spec is the contract.** Changes to behaviour start as changes to the
  [system design specification](docs/en/00-system-design-spec.md).

## 2. Roles

### Project lead

**Dr. Lee Il-guk (이일국), CLSOFTLAB (씨엘소프트랩)** — inventor and patent holder.

- Sets the mission and long-term direction.
- Appoints and removes maintainers and safety reviewers.
- Holds the final decision when consensus cannot be reached.
- Has a **veto on any change that weakens safety**. The lead does not use the veto to override a safety concern
  raised by a safety reviewer; safety concerns are resolved with evidence.
- Owns the patent pledge and the project's trademarks and names.

### Maintainers

Trusted contributors with write access. Each maintainer has one or more areas:

| Area | Covers |
|---|---|
| Firmware | `firmware/` |
| Hardware | `hardware/`, mechanical safety |
| App | `app/`, accessibility of the app |
| Documentation and translation | `docs/`, `i18n` files, language verification process |
| Community | Issues triage, code of conduct, field test coordination |

Maintainers review and merge pull requests in their area, triage issues, and keep the spec and implementations in sync.
The current maintainers are listed in the repository's GitHub team settings and named in each release's notes.
Until more maintainers are appointed, the project lead acts as maintainer for all areas.

### Safety reviewers

People appointed by the project lead to review safety-critical changes. The group should always include:

- at least one person with **orientation and mobility (O&M) expertise**, and
- at least one person who is **blind or has low vision** and walks independently,

in addition to technical reviewers for firmware and hardware. A safety reviewer can also be a maintainer.

### Contributors

Everyone who files an issue, reviews, tests, translates or sends a pull request. Contributors are the project.

## 3. How ordinary decisions are made

For changes that do not affect safety (for example refactoring with no behaviour change, documentation fixes, build
tooling, new optional features that do not touch alerts):

- **Lazy consensus.** A pull request approved by **one maintainer** of the area, with passing CI and no unresolved
  objection, can be merged.
- Larger changes (new dependencies, new modules, architecture changes) stay open for at least **7 days** so others can comment.
- If maintainers disagree, they discuss in the issue. If still unresolved, the project lead decides and records the reason.

## 4. How safety-critical decisions are made

A change is **safety-critical** if it can change whether, when or how a user is warned, or how the helmet protects
the head. The list in [CONTRIBUTING.md §6](CONTRIBUTING.md#6-safety-review-for-alert-logic) defines it. When in doubt,
treat a change as safety-critical.

Requirements before merge:

1. **Spec first.** The change to the [system design specification](docs/en/00-system-design-spec.md) is part of the pull
   request or already merged.
2. **Written rationale.** What problem it solves, what could go wrong, what the user will notice.
3. **Tests.** Automated tests for the logic (`firmware/tests/`), all passing in CI.
4. **Evidence.** Results from the relevant [test plan](docs/en/07-test-plan.md) procedures on real hardware. A change that
   cannot be hardware-tested yet may be merged only behind a disabled-by-default setting, clearly labelled experimental.
5. **Two approvals:** one maintainer of the area **and** one safety reviewer, who are not the author.
6. **User voice.** Changes to the haptic language, P0–P2 voice phrases, buttons or SOS also need agreement from a
   safety reviewer who is blind or has low vision, or an O&M instructor.
7. **Waiting period** of at least **7 days** after the last substantive change, so the community can review. Urgent
   fixes for a dangerous bug may skip the waiting period with the project lead's approval; they are reviewed again afterwards.
8. **Release notes** describe the change in plain language, in English and Korean.

A safety reviewer's objection blocks merge until it is resolved with evidence or the change is withdrawn.
Defaults are conservative: when a trade-off is unclear, the project prefers a false alarm over a missed hazard
(see spec §5.2), while tracking false-alarm rates (T7) so warnings stay trustworthy.

## 5. Safety incidents

When someone reports an injury, a fall, a near miss, or behaviour that could cause one (publicly with a field test
report or bug report, or privately by opening a private GitHub Security Advisory or contacting a maintainer via their
GitHub profile):

1. A maintainer acknowledges the report within a few days and labels it **safety**.
2. Maintainers and safety reviewers investigate, with the reporter's consent for any follow-up.
3. If the cause could affect other users, the project publishes an advisory in English and Korean, even before a fix.
4. The fix follows the safety-critical process. The spec and the [safety guide](docs/en/06-safety.md) are updated
   with what was learned.

Security vulnerabilities follow [SECURITY.md](SECURITY.md).

## 6. Releases

- Versions follow the spec version (v1.0, v1.1 …) for behaviour changes, with patch releases for fixes.
- A release includes firmware, rendered STL files, the app, and English and Korean documentation.
- Before a release: CI passes, the results table from the [test plan](docs/en/07-test-plan.md) is filled in for the
  reference build, and known limitations are listed in the release notes.
- The project lead or a maintainer they delegate publishes releases.

## 7. Becoming a maintainer

- Contributors who have made sustained, high-quality contributions and follow the code of conduct may be nominated by
  any maintainer, or may ask.
- The project lead decides after hearing the existing maintainers.
- Maintainers who are inactive for 12 months may be moved to emeritus status, with thanks. They can return.
- Maintainers who seriously break the code of conduct can be removed by the project lead.

We actively seek maintainers and safety reviewers who are blind or have low vision, and from outside Korea.

## 8. Changing this document

Changes to governance are proposed by pull request, stay open for at least **14 days**, and need the project lead's approval.
