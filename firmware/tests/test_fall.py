from owsh.sensors.imu import FallDetector

DT = 0.01  # 100 Hz


def run(det, segments, t0=0.0):
    """segments: list of (duration_s, magnitude_g). Returns times at which a fall fired."""
    fired = []
    t = t0
    for dur, g in segments:
        for _ in range(int(round(dur / DT))):
            if det.update(t, 0.0, 0.0, g):
                fired.append(round(t, 2))
            t += DT
    return fired


def test_classic_fall(cfg):
    det = FallDetector(cfg.imu)
    fired = run(det, [(1.0, 1.0), (0.15, 0.1), (0.2, 1.2), (0.03, 3.5), (0.5, 1.6), (2.5, 1.0)])
    assert len(fired) == 1
    # still period starts at 1.88 s -> fall 2 s later
    assert abs(fired[0] - 3.88) < 0.02


def test_short_freefall_ignored(cfg):
    det = FallDetector(cfg.imu)
    assert run(det, [(0.06, 0.1), (0.03, 3.5), (3.0, 1.0)]) == []


def test_no_impact_within_1s(cfg):
    det = FallDetector(cfg.imu)
    assert run(det, [(0.2, 0.1), (1.2, 1.0), (0.05, 3.5), (3.0, 1.0)]) == []


def test_impact_followed_by_motion_is_not_fall(cfg):
    det = FallDetector(cfg.imu)
    # jumping and landing, then walking on (|a| oscillates outside 1 +/- 0.15 g)
    walking = [(0.1, 1.4), (0.1, 0.7)] * 40
    assert run(det, [(0.2, 0.1), (0.05, 3.0)] + walking) == []


def test_stillness_must_be_continuous(cfg):
    det = FallDetector(cfg.imu)
    fired = run(det, [(0.2, 0.1), (0.05, 3.0), (1.5, 1.0), (0.05, 1.5), (2.1, 1.0)])
    assert len(fired) == 1


def test_sim_imu_triggers_fall(cfg, clock):
    from owsh.sensors.imu import SimImu

    imu = SimImu(clock.now, seed=1)
    det = FallDetector(cfg.imu)
    for _ in range(100):
        det.update(clock.now(), *imu.read_g())
        clock.advance(DT)
    imu.trigger_fall()
    fired = 0
    for _ in range(400):
        fired += det.update(clock.now(), *imu.read_g())
        clock.advance(DT)
    assert fired == 1
