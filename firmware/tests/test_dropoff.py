import dataclasses
import math

from owsh.sensors.reflex import DropoffDetector

DT = 0.02  # 50 Hz


def feed(det, values, t0=0.0):
    """values: list of distances; returns list of (t, result) for non-None results."""
    out = []
    t = t0
    for v in values:
        r = det.update(t, v)
        if r is not None:
            out.append((round(t, 3), r))
        t += DT
    return out, t


def test_initial_d0_from_geometry(cfg):
    det = DropoffDetector(cfg.dropoff)
    assert math.isclose(det.d0, 1.7 / math.sin(math.radians(50)), rel_tol=1e-6)


def test_learns_level_ground(cfg):
    det = DropoffDetector(cfg.dropoff)
    res, _ = feed(det, [2.5] * 200)  # 4 s of stable 2.5 m (ratio 1.13, inside the band)
    assert res == []
    assert det.calibrated and math.isclose(det.d0, 2.5, abs_tol=1e-6)


def test_no_learning_when_variance_high(cfg):
    det = DropoffDetector(cfg.dropoff)
    d0 = det.d0
    values = [2.1 + (0.3 if i % 2 else -0.1) for i in range(200)]
    feed(det, values)
    assert not det.calibrated and det.d0 == d0


def test_d0_clamped(cfg):
    c = dataclasses.replace(cfg.dropoff, sensor_height_m=5.0)
    assert DropoffDetector(c).d0 == 3.5
    c = dataclasses.replace(cfg.dropoff, sensor_height_m=0.5)
    assert DropoffDetector(c).d0 == 1.2


def test_drop_requires_120ms(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    base_t = 200 * DT
    d0 = det.d0
    # 100 ms of long readings: no alert
    res, t = feed(det, [d0 * 1.4] * 5 + [d0] * 10, base_t)
    assert res == []
    # sustained: alert once 120 ms reached
    res, t = feed(det, [d0 * 1.4] * 20, t)
    assert len(res) == 1
    first_t, r = res[0]
    assert r.kind == "drop" and not r.big
    assert math.isclose(first_t - t + 20 * DT, 0.12, abs_tol=1e-6)


def test_big_drop_and_no_return(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    res, t = feed(det, [None] * 10, 4.0)
    assert len(res) == 1 and res[0][1].kind == "drop" and res[0][1].big and res[0][1].dist_m is None
    det2 = DropoffDetector(cfg.dropoff)
    feed(det2, [2.2] * 200)
    res, _ = feed(det2, [2.2 * 1.8] * 10, 4.0)
    assert res[0][1].big


def test_no_return_not_drop_when_disabled(cfg):
    det = DropoffDetector(dataclasses.replace(cfg.dropoff, no_return_is_drop=False))
    feed(det, [2.2] * 200)
    res, _ = feed(det, [None] * 50, 4.0)
    assert res == []


def test_step_up_detection(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    res, _ = feed(det, [2.2 * 0.6] * 10, 4.0)
    assert len(res) == 1 and res[0][1].kind == "step_up"


def test_cooldown_per_type(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    res, t = feed(det, [3.2] * 100, 4.0)  # 2 s sustained drop -> one alert (cooldown 3 s)
    assert len(res) == 1
    res2, t = feed(det, [1.2] * 10, t)  # step up is a different type: not blocked
    assert len(res2) == 1 and res2[0][1].kind == "step_up"
    res3, t = feed(det, [3.2] * 100, t)  # drop again, 3 s after the first -> second alert
    assert len(res3) == 1
    assert res3[0][0] - res[0][0] >= 3.0 - 1e-9


def test_long_distance_never_learned_by_default(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    d0 = det.d0
    res, _ = feed(det, [3.3] * 1000, 4.0)  # standing still at a platform edge for 20 s
    assert math.isclose(det.d0, d0)
    assert len(res) >= 6  # keeps warning every 3 s


def test_shorter_distance_relearned_after_stable_period(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    feed(det, [1.3] * 800, 4.0)  # 16 s stable (e.g. sitting down)
    assert math.isclose(det.d0, 1.3, abs_tol=1e-6)


def test_sensitivity_change(cfg):
    det = DropoffDetector(cfg.dropoff)
    feed(det, [2.2] * 200)
    det.set_sensitivity("low")
    res, _ = feed(det, [2.2 * 1.4] * 20, 4.0)
    assert res == []  # 1.4 < 1.45
    det.set_sensitivity("high")
    res, _ = feed(det, [2.2 * 1.25] * 20, 5.0)
    assert len(res) == 1
