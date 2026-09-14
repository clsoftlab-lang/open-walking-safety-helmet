import dataclasses

import pytest

from owsh.config import DEFAULT_CONFIG_PATH, Config, ConfigError, config_from_dict, dropoff_ratios, load_config


def test_default_yaml_loads_and_matches_dataclass_defaults():
    loaded = load_config(DEFAULT_CONFIG_PATH)
    assert dataclasses.asdict(loaded) == dataclasses.asdict(Config())


def test_default_yaml_has_no_unknown_keys(caplog):
    import yaml

    data = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    _, warnings = config_from_dict(data)
    assert warnings == []


def test_spec_thresholds(cfg):
    assert (cfg.reflex.zone3_m, cfg.reflex.zone2_m, cfg.reflex.zone1_m, cfg.reflex.hysteresis_m) == (2.0, 1.2, 0.6, 0.1)
    assert cfg.i2c.tfluna_forward_addr == 0x10 and cfg.i2c.tfluna_down_addr == 0x11 and cfg.i2c.mpu6050_addr == 0x68
    assert (cfg.pins.haptic_left, cfg.pins.haptic_center, cfg.pins.haptic_right) == (17, 27, 22)
    assert (cfg.pins.button_b1, cfg.pins.button_b2, cfg.pins.button_b3, cfg.pins.status_led) == (5, 6, 26, 16)
    assert cfg.haptics.max_duty == 0.75
    assert cfg.dropoff.drop_ratio == 1.30 and cfg.dropoff.step_ratio == 0.70 and cfg.dropoff.sustain_s == 0.12
    assert cfg.vision.blocked.dark_mean_max == 12 and cfg.vision.blocked.dark_std_max == 6
    assert cfg.faces.cosine_threshold == 0.363
    assert cfg.audio.max_queue == 3 and cfg.audio.stale_s == 2.0


def test_unknown_key_warns_not_fails():
    cfg, warnings = config_from_dict({"reflex": {"zone9_m": 3}, "bogus": 1})
    assert len(warnings) == 2
    assert cfg.reflex.zone1_m == 0.6


def test_invalid_values_raise():
    with pytest.raises(ConfigError):
        config_from_dict({"reflex": {"zone1_m": 1.5}})  # zone1 > zone2
    with pytest.raises(ConfigError):
        config_from_dict({"haptics": {"max_duty": 1.5}})
    with pytest.raises(ConfigError):
        config_from_dict({"general": {"lang": "xx"}})
    with pytest.raises(ConfigError):
        config_from_dict({"reflex": {"zone1_m": "near"}})
    with pytest.raises(ConfigError):
        config_from_dict({"dropoff": {"no_return_is_drop": "yes"}})


def test_int_accepted_for_float_and_override_applies():
    cfg, _ = config_from_dict({"reflex": {"zone3_m": 3}, "general": {"lang": "ko"}})
    assert cfg.reflex.zone3_m == 3.0 and isinstance(cfg.reflex.zone3_m, float)
    assert cfg.general.lang == "ko"


def test_dropoff_sensitivity_presets(cfg):
    assert dropoff_ratios(cfg.dropoff, "normal") == (1.30, 0.70)
    assert dropoff_ratios(cfg.dropoff, "low") == (1.45, 0.55)
    assert dropoff_ratios(cfg.dropoff, "high") == (1.20, 0.80)
