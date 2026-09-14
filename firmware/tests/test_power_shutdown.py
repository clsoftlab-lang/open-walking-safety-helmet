import types

import pytest

from owsh.bus import EventBus
from owsh.clock import FakeClock
from owsh.events import ButtonGesture
from owsh.input.buttons import ButtonInput, ChordDetector
from owsh.output.haptics import make_pattern
from owsh.sensors.power import (
    THROTTLED_NOW,
    UNDERVOLTAGE_NOW,
    PowerControl,
    PowerMonitor,
    PowerWorker,
    parse_throttled,
)


# ------------------------------------------------------------------------- shutdown chord
def test_chord_detector_pure():
    c = ChordDetector(5.0)
    assert c.update(0.0, True, False, 0.0, 0.0) == []
    assert c.update(1.0, True, True, 0.0, 1.0) == ["chord_start"]
    assert c.update(5.9, True, True, 0.0, 1.0) == []
    assert c.update(6.0, True, True, 0.0, 1.0) == ["shutdown"]
    assert c.update(9.0, True, True, 0.0, 1.0) == []  # once
    assert c.update(9.1, False, True, 0.0, 1.0) == []
    assert c.update(10.0, True, True, 10.0, 1.0) == ["chord_start"]  # new chord


def make_input(cfg):
    bus = EventBus()
    got = []
    bus.subscribe(ButtonGesture, lambda e: got.append((round(e.ts, 2), e.button, e.gesture)))
    return ButtonInput(cfg.buttons, bus, FakeClock()), got


def poll_range(bi, start, end, step=0.02):
    t = start
    while t <= end + 1e-9:
        bi.poll(t)
        t += step


def gestures(got):
    return [(b, g) for _, b, g in got]


def test_b1_b3_hold_5s_shutdown_without_sos(cfg):
    bi, got = make_input(cfg)
    bi.edge("b3", True, 0.0)
    poll_range(bi, 0.0, 1.0)
    bi.edge("b1", True, 1.0)
    poll_range(bi, 1.0, 7.0)
    names = gestures(got)
    assert ("b3", "long") not in names and ("b1", "long") not in names
    assert names.count(("b1+b3", "shutdown")) == 1
    t_shutdown = [t for t, b, g in got if g == "shutdown"][0]
    assert t_shutdown == pytest.approx(6.0, abs=0.05)
    bi.edge("b1", False, 7.1)
    bi.edge("b3", False, 7.1)
    poll_range(bi, 7.1, 8.0)
    assert [g for _, _, g in got if g not in ("press",)] == ["shutdown"]  # no short/double either


def test_b1_joining_just_before_sos_threshold_suppresses_sos(cfg):
    bi, got = make_input(cfg)
    bi.edge("b3", True, 0.0)
    poll_range(bi, 0.0, 2.96)
    bi.edge("b1", True, 2.99)  # B3 would reach 3.0 s in the same polling step
    poll_range(bi, 3.0, 4.5)
    assert ("b3", "long") not in gestures(got)


def test_chord_released_early_does_nothing_and_b3_alone_still_sos(cfg):
    bi, got = make_input(cfg)
    bi.edge("b1", True, 0.0)
    bi.edge("b3", True, 0.2)
    poll_range(bi, 0.0, 3.0)
    bi.edge("b1", False, 3.0)
    poll_range(bi, 3.0, 6.0)  # B3 still held, but its press cycle was swallowed
    assert gestures(got) == [("b1", "press"), ("b3", "press")]
    bi.edge("b3", False, 6.0)
    poll_range(bi, 6.0, 6.5)
    bi.edge("b3", True, 7.0)
    poll_range(bi, 7.0, 10.2)
    assert ("b3", "long") in gestures(got)  # normal SOS hold works again


def test_ready_reverse_pattern():
    p = make_pattern("ready_reverse")
    assert [p.value_at(t) for t in (0.05, 0.15, 0.25)] == [(0, 0, 0.6), (0, 0.6, 0), (0.6, 0, 0)]


def test_power_control(cfg):
    assert PowerControl(sim=True, runner=lambda *a, **k: 1 / 0).poweroff()
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=1 if cmd[0] == "systemctl" else 0, stderr="denied")

    assert PowerControl(sim=False, runner=runner).poweroff()
    assert calls == [["systemctl", "poweroff"], ["sudo", "-n", "systemctl", "poweroff"]]


# ------------------------------------------------------------------------------- power
def test_parse_throttled():
    assert parse_throttled("throttled=0x50005\n") == 0x50005
    assert parse_throttled("0x0") == 0
    assert parse_throttled("50005") == 0x50005
    assert parse_throttled("error") is None and parse_throttled(None) is None


def test_undervoltage_sustained_10s_and_repeat_5min(cfg):
    m = PowerMonitor(cfg.power)
    uv = UNDERVOLTAGE_NOW | THROTTLED_NOW
    assert m.update(0.0, uv, 50) == []
    assert m.undervoltage and m.throttled
    assert m.update(5.0, uv, 50) == []
    assert m.update(10.0, uv, 50) == ["undervoltage"]
    assert all(m.update(t, uv, 50) == [] for t in range(15, 310, 5))
    assert m.update(310.0, uv, 50) == ["undervoltage"]
    # flapping supply: a new episode does not re-warn before 5 min since the last warning
    assert m.update(315.0, 0, 50) == [] and not m.undervoltage
    assert all(m.update(t, uv, 50) == [] for t in range(320, 610, 5))
    assert m.update(610.0, uv, 50) == ["undervoltage"]


def test_short_undervoltage_blip_ignored(cfg):
    m = PowerMonitor(cfg.power)
    assert m.update(0.0, UNDERVOLTAGE_NOW, 50) == []
    assert m.update(5.0, UNDERVOLTAGE_NOW, 50) == []
    assert m.update(10.0, 0, 50) == []
    assert m.update(15.0, UNDERVOLTAGE_NOW, 50) == []


def test_overheat_with_rearm(cfg):
    m = PowerMonitor(cfg.power)
    assert m.update(0.0, 0, 79.9) == []
    assert m.update(5.0, 0, 80.0) == ["overheat"]
    assert m.update(10.0, 0, 82.0) == []
    assert m.update(15.0, 0, 77.0) == []  # still above the 75 degC clear level
    assert m.update(20.0, 0, 81.0) == []
    assert m.update(25.0, 0, 74.0) == []  # re-armed
    assert m.update(30.0, 0, 80.5) == ["overheat"]
    assert m.update(330.0, 0, 85.0) == ["overheat"]  # 5 min repeat


def test_power_worker_unknown_platform(cfg, clock):
    statuses, warnings = [], []
    w = PowerWorker(cfg.power, clock, statuses.append, warnings.append, bits_reader=lambda: None,
                    temp_reader=lambda: None)
    assert w.step() == []
    assert statuses[0].undervoltage is None and warnings == []
