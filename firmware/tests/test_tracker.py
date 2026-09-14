import dataclasses
import math

import pytest

from owsh.events import Direction, Level
from owsh.vision.detector import Detection
from owsh.vision.tracker import (
    ApproachPolicy,
    IoUTracker,
    direction_from_angle,
    horizontal_angle_deg,
    iou,
    time_to_contact,
)

W, H = 1280, 720


def det(label, x1, y1, x2, y2, score=0.9):
    return Detection(label, 0, score, (x1, y1, x2, y2))


def test_iou():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert math.isclose(iou((0, 0, 10, 10), (5, 0, 15, 10)), 50 / 150)


def test_direction_from_angle_and_hfov():
    assert horizontal_angle_deg(W / 2, W, 102) == 0
    assert math.isclose(horizontal_angle_deg(W, W, 102), 51.0, abs_tol=1e-6)
    assert math.isclose(horizontal_angle_deg(0, W, 102), -51.0, abs_tol=1e-6)
    assert direction_from_angle(-15.0) == Direction.CENTER
    assert direction_from_angle(-15.01) == Direction.LEFT
    assert direction_from_angle(15.0) == Direction.CENTER
    assert direction_from_angle(15.01) == Direction.RIGHT


def test_ttc_formula():
    # h doubles over 0.5 s -> s = 2 -> TTC = 0.5 / (2 - 1) = 0.5 s
    assert math.isclose(time_to_contact([(0.0, 100.0), (0.5, 200.0)], 0.5, 0.4, 1.0), 0.5)
    # the newest sample that is >= 0.4 s old is the reference (0.5 s old here)
    hist = [(0.0, 100.0), (0.5, 140.0), (1.0, 200.0)]
    assert math.isclose(time_to_contact(hist, 1.0, 0.4, 1.0), 0.5 / (200.0 / 140.0 - 1.0))
    # not approaching
    assert time_to_contact([(0.0, 100.0), (0.5, 100.0)], 0.5, 0.4, 1.0) == math.inf
    # window too short
    assert time_to_contact([(0.0, 100.0), (0.3, 150.0)], 0.3, 0.4, 1.0) is None


def test_tracker_keeps_ids_and_expires(cfg):
    tr = IoUTracker(cfg.vision.tracker, 102)
    a = tr.update([det("person", 100, 100, 200, 400), det("car", 600, 300, 900, 500)], 0.0, W, H)
    ids = {t.label: t.track_id for t in a}
    b = tr.update([det("person", 105, 100, 205, 402), det("car", 610, 300, 910, 500)], 0.1, W, H)
    assert {t.label: t.track_id for t in b} == ids
    # label change never matches
    c = tr.update([det("dog", 105, 100, 205, 402)], 0.2, W, H)
    assert len({t.track_id for t in c}) == 3
    # tracks older than 0.7 s without detections are dropped
    d = tr.update([], 0.85, W, H)
    assert [t.label for t in d] == ["dog"]
    assert tr.update([], 0.95, W, H) == []


def test_tracker_ttc_on_approaching_person(cfg):
    tc = dataclasses.replace(cfg.vision.tracker, height_smoothing=1.0)
    tr = IoUTracker(tc, 102)
    # height grows as 1/Z with Z = 5 m - 2 m/s * t  -> true TTC(t) = Z/2
    info = None
    for i in range(11):
        t = i * 0.1
        z = 5.0 - 2.0 * t
        h = 400.0 / z
        info = tr.update([det("person", 600, 300, 680, 300 + h)], t, W, H)[0]
    true_ttc = (5.0 - 2.0 * 1.0) / 2.0  # 1.5 s at t = 1.0
    # for constant closing speed the scale-ratio estimate is exact
    assert info.ttc_s == pytest.approx(true_ttc, rel=0.02)
    assert info.direction == Direction.CENTER and info.is_mover


def tinfo(cfg, label="person", ttc=1.0, h=0.25, tid=1):
    from owsh.events import TrackInfo

    return TrackInfo(tid, label, 0.9, (0, 0, 10, 10), h, 0.0, Direction.CENTER, ttc, 1.0,
                     label in cfg.vision.detector.movers)


def test_approach_levels(cfg):
    pol = ApproachPolicy(dataclasses.replace(cfg.vision.approach, confirm_frames=1), cfg.vision.detector.vehicles)
    assert pol.level_for(tinfo(cfg, ttc=1.4, h=0.21)) == Level.P1
    assert pol.level_for(tinfo(cfg, ttc=1.4, h=0.15)) == Level.P2  # not tall enough for P1
    assert pol.level_for(tinfo(cfg, ttc=2.9, h=0.11)) == Level.P2
    assert pol.level_for(tinfo(cfg, ttc=3.5, h=0.5)) is None  # person, > 3.0 s
    assert pol.level_for(tinfo(cfg, "car", ttc=3.5, h=0.12)) == Level.P2  # vehicle < 4.0 s
    assert pol.level_for(tinfo(cfg, ttc=2.0, h=0.09)) is None  # too small
    assert pol.level_for(tinfo(cfg, "bench", ttc=0.5, h=0.5)) is None  # not a mover
    assert pol.level_for(tinfo(cfg, ttc=math.inf)) is None


def test_approach_cooldown_and_escalation(cfg):
    pol = ApproachPolicy(dataclasses.replace(cfg.vision.approach, confirm_frames=1), cfg.vision.detector.vehicles)
    p2 = tinfo(cfg, ttc=2.5, h=0.15)
    p1 = tinfo(cfg, ttc=1.0, h=0.3)
    assert pol.evaluate(p2, 0.0) == Level.P2
    assert pol.evaluate(p2, 1.0) is None  # same level within 5 s
    assert pol.evaluate(p1, 2.0) == Level.P1  # escalation bypasses cooldown
    assert pol.evaluate(p1, 3.0) is None
    assert pol.evaluate(p2, 4.0) is None  # lower level right after P1
    assert pol.evaluate(p1, 7.1) == Level.P1  # cooldown over
    other = tinfo(cfg, ttc=2.5, h=0.15, tid=2)
    assert pol.evaluate(other, 7.2) == Level.P2  # per track


def test_approach_confirm_frames(cfg):
    pol = ApproachPolicy(cfg.vision.approach, cfg.vision.detector.vehicles)
    assert cfg.vision.approach.confirm_frames == 2
    p1 = tinfo(cfg, ttc=1.0, h=0.3)
    assert pol.evaluate(p1, 0.0) is None
    assert pol.evaluate(tinfo(cfg, ttc=math.inf), 0.1) is None  # streak broken
    assert pol.evaluate(p1, 0.2) is None
    assert pol.evaluate(p1, 0.3) == Level.P1
