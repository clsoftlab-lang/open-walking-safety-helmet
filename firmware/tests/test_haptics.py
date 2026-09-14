import dataclasses
import logging

import pytest

from owsh.events import Level
from owsh.output.haptics import (
    HapticEngine,
    HapticMixer,
    SimHapticBackend,
    intensity_to_duty,
    make_pattern,
)


def sample(pattern, t):
    return pattern.value_at(t)


def test_tick_pattern():
    p = make_pattern("tick")
    assert sample(p, 0.0) == (0, 0.6, 0) and sample(p, 0.039) == (0, 0.6, 0)
    assert sample(p, 0.040) is None


def test_zone_patterns_loop():
    z3 = make_pattern("zone3")
    assert z3.loop and z3.duration_s == pytest.approx(0.5)
    assert sample(z3, 0.03) == (0, 0.4, 0) and sample(z3, 0.1) == (0, 0, 0) and sample(z3, 0.53) == (0, 0.4, 0)
    z2 = make_pattern("zone2")
    assert z2.duration_s == pytest.approx(0.2)  # 5 Hz
    assert sample(z2, 0.05) == (0, 0.7, 0) and sample(z2, 0.15) == (0, 0, 0)
    z1 = make_pattern("zone1")
    assert all(sample(z1, t) == (0, 1.0, 0) for t in (0, 0.5, 12.3))


def test_drop_pattern_exact():
    p = make_pattern("drop")
    assert p.level == Level.P1
    assert sample(p, 0.0) == (1, 1, 1) and sample(p, 0.399) == (1, 1, 1)
    assert sample(p, 0.45) == (0, 0, 0)
    assert sample(p, 0.55) == (1, 1, 1) and sample(p, 0.949) == (1, 1, 1)
    assert sample(p, 1.0) == (0, 0, 0)
    assert sample(p, 1.1) is None


def test_p0_fault_and_sos_patterns_exact():
    f = make_pattern("fault")
    assert f.level == Level.P0 and f.duration_s == pytest.approx(0.3)
    on = [0.0, 0.1, 0.2]
    off = [0.05, 0.15, 0.25]
    assert all(sample(f, t) == (0, 1.0, 0) for t in on)
    assert all(sample(f, t) == (0, 0, 0) for t in off)
    s = make_pattern("sos_countdown")
    assert s.level == Level.P0 and s.duration_s == pytest.approx(10.0)
    for k in range(10):
        assert sample(s, k + 0.1) == (1, 1, 1)
        assert sample(s, k + 0.5) == (0, 0, 0)
    assert sample(s, 10.0) is None
    assert make_pattern("sos_countdown", repeats=60).duration_s == pytest.approx(60.0)


def test_side_patterns_and_intensities():
    assert sample(make_pattern("approach_left", level=Level.P1), 0.1) == (1.0, 0, 0)
    assert sample(make_pattern("approach_right", level=Level.P2), 0.1) == (0, 0, 0.7)
    assert make_pattern("approach_center").duration_s == pytest.approx(3 * 0.23)
    assert sample(make_pattern("person_friend_left"), 0.05) == (0.6, 0, 0)
    assert make_pattern("person_avoid_right").duration_s == pytest.approx(4 * 0.12)
    assert sample(make_pattern("step_up"), 0.05) == (0, 0.8, 0)
    assert make_pattern("step_up").duration_s == pytest.approx(0.6)
    assert make_pattern("count", n=15).name == "count_10"
    ready = make_pattern("ready")
    assert [sample(ready, t) for t in (0.05, 0.15, 0.25)] == [(0.6, 0, 0), (0, 0.6, 0), (0, 0, 0.6)]
    t = make_pattern("turn_left")
    assert t.loop and sample(t, 1.1) == (0.7, 0, 0) and sample(t, 1.5) == (0, 0, 0)
    with pytest.raises(KeyError):
        make_pattern("nope")


def test_mixer_takes_max_per_motor():
    m = HapticMixer()
    m.play(make_pattern("zone2"), 0.0, key="zone")
    m.play(make_pattern("drop"), 0.0)
    lcr, _ = m.render(0.1)  # zone2 off phase (0.08-0.2), drop on
    assert lcr == (1, 1, 1)
    lcr, _ = m.render(1.25)  # drop finished; zone2 at 1.25 % 0.2 = 0.05 -> on
    assert lcr == (0, 0.7, 0)
    assert m.active_names() == ["zone2"]


def test_mixer_key_replaces_and_stop():
    m = HapticMixer()
    m.play(make_pattern("zone3"), 0.0, key="zone")
    m.ensure(make_pattern("zone1"), 0.1, key="zone")
    assert m.active_names() == ["zone1"]
    m.ensure(make_pattern("zone1"), 0.5, key="zone")  # same pattern: not restarted
    assert m.stop("zone") and not m.is_active("zone")
    assert m.render(1.0)[0] == (0, 0, 0)


def test_max_duty_cap_and_scale(cfg):
    assert intensity_to_duty(1.0, 0.75) == 0.75
    assert intensity_to_duty(0.4, 0.75) == 0.4
    assert intensity_to_duty(1.7, 0.75) == 0.75
    assert intensity_to_duty(-1, 0.75) == 0.0
    assert intensity_to_duty(1.0, 0.75, "scale") == 0.75
    assert intensity_to_duty(0.4, 0.75, "scale") == pytest.approx(0.3)
    backend = SimHapticBackend(cfg.haptics)
    assert backend.set_intensities((1.0, 0.6, 0.9)) == (0.75, 0.6, 0.75)
    backend2 = SimHapticBackend(dataclasses.replace(cfg.haptics, max_duty=0.5))
    assert max(backend2.set_intensities((1, 1, 1))) == 0.5


def test_engine_tick_logs_latency(cfg, clock, caplog):
    backend = SimHapticBackend(cfg.haptics)
    eng = HapticEngine(cfg.haptics, backend, clock)
    sample_ts = clock.now()
    clock.advance(0.004)
    eng.ensure("zone1", key="zone", source_ts=sample_ts)
    clock.advance(0.003)
    with caplog.at_level(logging.INFO, logger="owsh.haptics"):
        eng.tick()
    assert backend.duties == (0, 0.75, 0)
    assert eng.last_latency_ms == pytest.approx(7.0, abs=0.01)
    assert "haptic_on motor=C pattern=zone1" in caplog.text
    eng.stop("zone")
    eng.tick()
    assert backend.duties == (0, 0, 0)
