from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from owsh.clock import FakeClock  # noqa: E402
from owsh.config import Config  # noqa: E402
from owsh.events import Level  # noqa: E402
from owsh.i18n import I18n  # noqa: E402
from owsh.link.ble import FakeLink  # noqa: E402


class FakeHaptics:
    def __init__(self) -> None:
        self.played: list[tuple[str, str | None, dict]] = []
        self.active: dict[str, str] = {}
        self.stopped: list[str] = []

    def play(self, pattern_id, key=None, source_ts=None, **kw):
        self.played.append((pattern_id, key, kw))
        self.active[key or pattern_id] = pattern_id
        return key or pattern_id

    def ensure(self, pattern_id, key, source_ts=None, **kw):
        if self.active.get(key) != pattern_id:
            self.play(pattern_id, key, source_ts, **kw)

    def stop(self, key):
        self.active.pop(key, None)
        self.stopped.append(key)

    def names(self) -> list[str]:
        return [p[0] for p in self.played]


class FakeSpeech:
    def __init__(self) -> None:
        self.muted = False
        self.items: list[tuple[str, Level, bool]] = []

    def say(self, text, level, requested=False, cacheable=False):
        self.items.append((text, Level(level), requested))

    def texts(self) -> list[str]:
        return [t for t, _, _ in self.items]


@pytest.fixture
def cfg() -> Config:
    return Config()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def haptics() -> FakeHaptics:
    return FakeHaptics()


@pytest.fixture
def speech() -> FakeSpeech:
    return FakeSpeech()


@pytest.fixture
def i18n() -> I18n:
    return I18n("en")


@pytest.fixture
def link(cfg, clock) -> FakeLink:
    return FakeLink(cfg.ble, clock, connected=False)
