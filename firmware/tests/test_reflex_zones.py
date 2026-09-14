from owsh.sensors.reflex import MedianFilter, ZoneTracker, valid_distance


def run(zt, distances, t0=0.0, dt=0.02):
    out = []
    for i, d in enumerate(distances):
        out.append(zt.update(d, t0 + i * dt))
    return out


def test_valid_distance_rules():
    assert valid_distance(1.5, 100, 100) == 1.5
    assert valid_distance(1.5, 99, 100) is None
    assert valid_distance(0.0, 5000, 100) is None
    assert valid_distance(None, 5000, 100) is None


def test_median_filter_rejects_single_spike_and_dropout():
    m = MedianFilter(3)
    assert m.add(2.0) == 2.0
    assert m.add(0.3) == 1.15  # median of 2 values is their mean
    assert m.add(2.0) == 2.0
    assert m.add(None) == 2.0
    assert m.add(2.0) == 2.0
    assert m.add(None) is None  # two of the last three samples have no return
    assert m.add(None) is None


def test_zone_entry_thresholds(cfg):
    zt = ZoneTracker(cfg.reflex)
    assert zt.update(2.5) == 0
    assert zt.update(2.0) == 3  # 2.0 >= d > 1.2
    assert zt.update(1.21) == 3
    assert zt.update(1.2) == 2
    assert zt.update(0.61) == 2
    assert zt.update(0.6) == 1
    assert zt.update(0.3) == 1


def test_zone_hysteresis_leaving(cfg):
    zt = ZoneTracker(cfg.reflex)
    zt.update(0.5)
    assert zt.zone == 1
    assert zt.update(0.65) == 1  # needs > 0.7
    assert zt.update(0.70) == 1
    assert zt.update(0.71) == 2
    assert zt.update(1.25) == 2  # needs > 1.3
    assert zt.update(1.31) == 3
    assert zt.update(2.05) == 3  # needs > 2.1
    assert zt.update(2.11) == 0
    assert zt.update(2.05) == 0  # re-entry at 2.0
    assert zt.update(2.0) == 3


def test_zone_jump_out_multiple_levels(cfg):
    zt = ZoneTracker(cfg.reflex)
    zt.update(0.4)
    assert zt.update(1.5) == 3
    zt.update(0.4)
    assert zt.update(5.0) == 0


def test_no_return_clears_but_holds_z1_briefly(cfg):
    zt = ZoneTracker(cfg.reflex)
    zt.update(1.0, 0.0)
    assert zt.update(None, 0.02) == 0  # Z2 -> clear immediately on no return
    zt.update(0.3, 1.0)
    assert zt.update(None, 1.02) == 1  # below min range: hold Z1
    assert zt.update(None, 1.4) == 1
    assert zt.update(None, 1.53) == 0  # after 0.5 s
