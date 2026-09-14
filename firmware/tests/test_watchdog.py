import dataclasses

import numpy as np

from owsh.bus import EventBus
from owsh.events import FaultChanged
from owsh.vision.preprocess import Dehazer, frame_stats
from owsh.watchdog import CameraBlockedDetector, Watchdog


def collect(bus):
    got = []
    bus.subscribe(FaultChanged, lambda e: got.append((e.component, e.active)))
    return got


def test_heartbeat_timeout_and_recovery(clock):
    bus = EventBus()
    got = collect(bus)
    wd = Watchdog(bus, clock)
    wd.register("lidar_forward", 0.5)
    wd.beat("lidar_forward")
    clock.advance(0.4)
    wd.check()
    assert got == []
    clock.advance(0.2)
    wd.check()
    assert got == [("lidar_forward", True)]
    wd.check()
    assert got == [("lidar_forward", True)]  # no repeats from the watchdog itself
    wd.beat("lidar_forward")
    assert got[-1] == ("lidar_forward", False)
    assert wd.active_faults() == []


def test_never_started_component_faults_after_grace(clock):
    bus = EventBus()
    got = collect(bus)
    wd = Watchdog(bus, clock)
    wd.register("camera", 2.0, startup_grace_s=8.0)
    clock.advance(9.9)
    wd.check()
    assert got == []
    clock.advance(0.2)
    wd.check()
    assert got == [("camera", True)]


def test_explicit_faults(clock):
    bus = EventBus()
    got = collect(bus)
    wd = Watchdog(bus, clock)
    wd.set_fault("audio", True, "no espeak")
    wd.set_fault("audio", True, "no espeak")
    wd.set_fault("audio", False)
    assert got == [("audio", True), ("audio", False)]


def test_camera_blocked_dark_3s(cfg):
    det = CameraBlockedDetector(cfg.vision.blocked)
    t = 0.0
    assert det.update(t, 3.0, 1.0, 0.5) is None
    for _ in range(14):  # 5 Hz
        t += 0.2
        r = det.update(t, 3.0, 1.0, 0.5)
        assert r is None, t
    t += 0.2  # 3.0 s
    assert det.update(t, 3.0, 1.0, 0.5) is True and det.reason == "dark"
    # recovery needs 1 s of good frames
    t += 0.2
    assert det.update(t, 120.0, 50.0, 300.0) is None
    t += 0.6
    assert det.update(t, 3.0, 1.0, 0.5) is None  # dark again resets clear timer
    for _ in range(6):
        t += 0.2
        r = det.update(t, 120.0, 50.0, 300.0)
    assert r is False and not det.blocked


def test_dark_but_textured_is_not_blocked(cfg):
    det = CameraBlockedDetector(cfg.vision.blocked)
    for i in range(40):
        assert det.update(i * 0.2, 8.0, 9.0, 40.0) is None  # night street: dark but std >= 6


def test_camera_blocked_blur_5s(cfg):
    det = CameraBlockedDetector(cfg.vision.blocked)
    results = [det.update(i * 0.2, 90.0, 20.0, 2.0) for i in range(26)]
    assert results.index(True) == 25  # t = 5.0 s
    assert det.reason == "blur"


def test_frame_stats_black_and_textured():
    black = np.zeros((720, 1280, 3), np.uint8)
    mean, std, lap = frame_stats(black)
    assert mean == 0 and std == 0 and lap == 0
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8)
    mean, std, lap = frame_stats(noise)
    assert mean > 100 and std > 15 and lap > 1000


def test_dehaze_modes(cfg):
    img = np.full((100, 100, 3), 40, np.uint8)
    img[40:60] = 60
    assert Dehazer(dataclasses.replace(cfg.vision, dehaze="off")).should_apply(10, 5) is False
    assert Dehazer(dataclasses.replace(cfg.vision, dehaze="on")).should_apply(200, 80) is True
    d = Dehazer(cfg.vision)
    assert d.should_apply(50, 60) and d.should_apply(120, 20) and not d.should_apply(120, 60)
    out = d.apply(img, 45, 8)
    assert out.shape == img.shape and d.active


def test_black_frame_with_small_bright_icon_is_blocked(cfg):
    """Regression: a Windows privacy shutter delivers black frames with a small white
    "camera off" icon (std-dev > 6). The dark-pixel fraction rule must still catch it."""
    import cv2

    from owsh.vision.preprocess import frame_stats_ex

    frame = np.zeros((720, 1280, 3), np.uint8)
    cv2.rectangle(frame, (595, 325), (661, 371), (255, 255, 255), 3)
    cv2.line(frame, (598, 371), (645, 325), (255, 255, 255), 4)
    mean, std, lap, dark_frac = frame_stats_ex(frame)
    assert mean < 12 and std >= 6  # the literal spec rule alone would miss it
    det = CameraBlockedDetector(cfg.vision.blocked)
    fired = [det.update(i * 0.2, mean, std, lap, dark_frac) for i in range(16)]
    assert fired[15] is True
    # a dark night scene with visible lit areas is not "blocked"
    night = np.full((720, 1280, 3), 6, np.uint8)
    night[300:500, 200:1100] = 60
    assert frame_stats_ex(night)[3] < cfg.vision.blocked.dark_pixel_frac
