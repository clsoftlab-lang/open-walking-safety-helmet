"""Configuration: dataclasses with spec defaults, YAML loader and validation.

Defaults here MUST equal ``config/default.yaml`` (a test enforces it). Unknown YAML keys are
logged as warnings and ignored (a typo must not stop the helmet from booting); invalid values
raise :class:`ConfigError` so ``__main__`` can fall back to safe defaults and announce it.
"""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_type_hints

log = logging.getLogger("owsh.config")

FIRMWARE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = FIRMWARE_ROOT / "config" / "default.yaml"


class ConfigError(ValueError):
    pass


@dataclass
class GeneralConfig:
    lang: str = "en"
    units: str = "metric"  # metric | imperial (voice only)
    data_dir: str = "data"
    models_dir: str = "models"
    log_level: str = "INFO"


@dataclass
class PinsConfig:  # BCM numbering, spec §4.2
    haptic_left: int = 17
    haptic_center: int = 27
    haptic_right: int = 22
    button_b1: int = 5
    button_b2: int = 6
    button_b3: int = 26
    status_led: int = 16


@dataclass
class I2CConfig:
    bus: int = 1
    tfluna_forward_addr: int = 0x10
    tfluna_down_addr: int = 0x11
    mpu6050_addr: int = 0x68


@dataclass
class ReflexConfig:  # spec §5.1
    rate_hz: float = 50.0
    median_window: int = 3
    min_strength: int = 100
    zone3_m: float = 2.0
    zone2_m: float = 1.2
    zone1_m: float = 0.6
    hysteresis_m: float = 0.1
    z1_no_return_hold_s: float = 0.5
    zone2_voice_cooldown_s: float = 5.0
    zone1_voice_cooldown_s: float = 3.0
    zone3_alert_cooldown_s: float = 5.0


@dataclass
class DropoffConfig:  # spec §5.2
    enabled: bool = True
    tilt_deg: float = 50.0
    sensor_height_m: float = 1.7
    learn_window_s: float = 3.0
    learn_max_std_m: float = 0.05
    d0_min_m: float = 1.2
    d0_max_m: float = 3.5
    drop_ratio: float = 1.30
    step_ratio: float = 0.70
    big_drop_ratio: float = 1.6
    sustain_s: float = 0.12
    cooldown_s: float = 3.0
    no_return_is_drop: bool = True
    sensitivity: str = "normal"  # low | normal | high
    relearn_shorter_after_s: float = 10.0
    allow_relearn_longer: bool = False


@dataclass
class DetectorConfig:  # spec §5.3
    model: str = "object_detection_nanodet_2022nov.onnx"
    input_size: int = 416
    score_threshold: float = 0.35
    nms_threshold: float = 0.6
    num_threads: int = 0
    color_order: str = "rgb"
    classes: list[str] = field(default_factory=lambda: [
        "person", "bicycle", "car", "motorcycle", "bus", "truck", "dog", "horse", "bench",
        "fire hydrant", "stop sign", "parking meter", "traffic light", "chair", "potted plant",
        "suitcase"])
    movers: list[str] = field(default_factory=lambda: [
        "person", "bicycle", "car", "motorcycle", "bus", "truck", "dog", "horse"])
    vehicles: list[str] = field(default_factory=lambda: [
        "bicycle", "car", "motorcycle", "bus", "truck"])


@dataclass
class TrackerConfig:
    iou_threshold: float = 0.3
    max_age_s: float = 0.7
    ttc_window_s: float = 0.4
    ttc_max_window_s: float = 1.0
    height_smoothing: float = 0.5
    center_deg: float = 15.0


@dataclass
class ApproachConfig:
    p1_ttc_s: float = 1.5
    p1_min_height: float = 0.20
    p2_ttc_s: float = 3.0
    p2_vehicle_ttc_s: float = 4.0
    p2_min_height: float = 0.10
    cooldown_s: float = 5.0
    confirm_frames: int = 2


@dataclass
class BlockedConfig:  # spec §5.7
    dark_mean_max: float = 12.0
    dark_std_max: float = 6.0
    dark_hold_s: float = 3.0
    dark_pixel_frac: float = 0.97
    blur_lapvar_max: float = 5.0
    blur_hold_s: float = 5.0
    clear_hold_s: float = 1.0
    check_hz: float = 5.0


@dataclass
class VisionConfig:
    enabled: bool = True
    source: str = "auto"  # auto | picamera2 | opencv | video
    camera_index: int = 0
    video_path: str = ""
    video_loop: bool = True
    width: int = 1280
    height: int = 720
    hfov_deg: float = 102.0
    dehaze: str = "auto"  # auto | on | off
    dehaze_auto_mean_below: float = 70.0
    dehaze_auto_std_below: float = 35.0
    clahe_clip: float = 2.0
    clahe_grid: int = 8
    describe_max_objects: int = 5
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    approach: ApproachConfig = field(default_factory=ApproachConfig)
    blocked: BlockedConfig = field(default_factory=BlockedConfig)


@dataclass
class FacesConfig:  # spec §5.4
    enabled: bool = True
    detector_model: str = "face_detection_yunet_2023mar.onnx"
    recognizer_model: str = "face_recognition_sface_2021dec.onnx"
    rate_hz: float = 2.0
    detect_width: int = 640
    detect_score_min: float = 0.6
    nms_threshold: float = 0.3
    cosine_threshold: float = 0.363
    cooldown_s: float = 60.0


@dataclass
class OcrConfig:  # spec §5.5
    enabled: bool = True
    languages: list[str] = field(default_factory=lambda: ["en", "ko"])
    det_model_path: str = ""
    rec_model_path: str = ""
    rec_keys_path: str = ""
    crop_frac: float = 0.70
    max_chars: int = 200
    min_score: float = 0.5
    danger_keywords: dict[str, list[str]] = field(default_factory=lambda: {
        "en": ["DANGER", "CAUTION", "WARNING", "WET FLOOR", "KEEP OUT", "NO ENTRY"],
        "ko": ["위험", "공사", "주의", "경고", "출입금지", "미끄럼"],
    })


@dataclass
class ImuConfig:  # spec §5.6
    enabled: bool = True
    rate_hz: float = 100.0
    freefall_g: float = 0.35
    freefall_min_s: float = 0.08
    impact_g: float = 2.5
    impact_window_s: float = 1.0
    still_band_g: float = 0.15
    still_s: float = 2.0
    still_timeout_s: float = 6.0


@dataclass
class HapticsConfig:  # spec §6
    tick_ms: float = 10.0
    max_duty: float = 0.75
    duty_mode: str = "cap"  # cap: min(intensity, max_duty) | scale: intensity * max_duty
    pwm_hz: float = 200.0


@dataclass
class AudioConfig:  # spec §7.1
    backend: str = "auto"  # auto | piper | espeak-ng | pyttsx3 | print
    piper_bin: str = "piper"
    piper_model: str = ""
    player: str = "aplay"
    espeak_voices: dict[str, str] = field(default_factory=lambda: {"en": "en-us", "ko": "ko"})
    rate_wpm: int = 170
    volume: int = 80
    max_queue: int = 3
    stale_s: float = 2.0
    cache_dir: str = "cache/tts"


@dataclass
class ButtonsConfig:  # spec §7.2
    short_max_s: float = 0.8
    long_min_s: float = 1.5
    sos_hold_s: float = 3.0
    double_gap_s: float = 0.4
    shutdown_hold_s: float = 5.0  # hold B1 + B3 together -> safe shutdown
    debounce_s: float = 0.03
    poll_hz: float = 50.0


@dataclass
class SosConfig:  # spec §7.3
    countdown_s: float = 10.0
    resend_s: float = 5.0
    no_phone_alarm_s: float = 60.0
    no_phone_voice_every_s: float = 10.0


@dataclass
class WatchdogConfig:  # spec §5.7
    camera_timeout_s: float = 2.0
    lidar_timeout_s: float = 0.5
    imu_timeout_s: float = 1.0
    fault_repeat_s: float = 10.0
    check_hz: float = 10.0


@dataclass
class BleConfig:  # spec §8
    enabled: bool = True
    name_prefix: str = "OWSH"
    chunk_size: int = 20  # MTU 23 - 3; safe for every phone
    chunk_gap_ms: float = 15.0
    status_every_s: float = 10.0
    phone_say_min_level: int = 2  # phone "say" can never preempt P0/P1 safety speech
    say_min_interval_s: float = 3.0  # at most one phone "say" per 3 s
    security: str = "encrypt"  # none | encrypt | authenticated (BlueZ characteristic flags)
    bonded_only: bool = True  # accept phone messages only from bonded (paired) phones
    pairing_window_s: float = 120.0  # pairing open this long after boot once a phone is bonded
    confirm_volume_below: int = 30  # a phone setting volume below this is announced


@dataclass
class PowerConfig:
    enabled: bool = True
    poll_s: float = 5.0
    undervoltage_hold_s: float = 10.0
    undervoltage_repeat_s: float = 300.0
    overheat_c: float = 80.0
    overheat_clear_c: float = 75.0
    overheat_repeat_s: float = 300.0
    shutdown_delay_s: float = 3.0


@dataclass
class LocationConfig:
    fresh_s: float = 60.0
    wait_s: float = 5.0


@dataclass
class SimConfig:
    forward_m: float = 0.0  # 0 = no return (clear path)
    down_m: float = 2.2
    noise_m: float = 0.01


@dataclass
class Config:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    pins: PinsConfig = field(default_factory=PinsConfig)
    i2c: I2CConfig = field(default_factory=I2CConfig)
    reflex: ReflexConfig = field(default_factory=ReflexConfig)
    dropoff: DropoffConfig = field(default_factory=DropoffConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    faces: FacesConfig = field(default_factory=FacesConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    imu: ImuConfig = field(default_factory=ImuConfig)
    haptics: HapticsConfig = field(default_factory=HapticsConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    buttons: ButtonsConfig = field(default_factory=ButtonsConfig)
    sos: SosConfig = field(default_factory=SosConfig)
    watchdog: WatchdogConfig = field(default_factory=WatchdogConfig)
    ble: BleConfig = field(default_factory=BleConfig)
    power: PowerConfig = field(default_factory=PowerConfig)
    location: LocationConfig = field(default_factory=LocationConfig)
    sim: SimConfig = field(default_factory=SimConfig)

    # ----------------------------------------------------------------- helpers
    def resolve_path(self, p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else FIRMWARE_ROOT / path

    @property
    def data_dir(self) -> Path:
        return self.resolve_path(self.general.data_dir)

    @property
    def models_dir(self) -> Path:
        return self.resolve_path(self.general.models_dir)

    def model_path(self, name: str) -> Path:
        path = Path(name)
        return path if path.is_absolute() else self.models_dir / path


# --------------------------------------------------------------------------- loading
def _coerce(value: Any, typ: Any, path: str) -> Any:
    origin = getattr(typ, "__origin__", None)
    if dataclasses.is_dataclass(typ):
        if not isinstance(value, dict):
            raise ConfigError(f"{path}: expected a mapping")
        return value  # merged by caller
    if typ is bool:
        if isinstance(value, bool):
            return value
        raise ConfigError(f"{path}: expected true/false, got {value!r}")
    if typ is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{path}: expected integer, got {value!r}")
        return value
    if typ is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{path}: expected number, got {value!r}")
        return float(value)
    if typ is str:
        if not isinstance(value, str):
            raise ConfigError(f"{path}: expected text, got {value!r}")
        return value
    if origin is list:
        if not isinstance(value, list):
            raise ConfigError(f"{path}: expected a list")
        (item_t,) = typ.__args__
        return [_coerce(v, item_t, f"{path}[{i}]") for i, v in enumerate(value)]
    if origin is dict:
        if not isinstance(value, dict):
            raise ConfigError(f"{path}: expected a mapping")
        _, val_t = typ.__args__
        return {str(k): _coerce(v, val_t, f"{path}.{k}") for k, v in value.items()}
    return value


def _merge(obj: Any, data: dict[str, Any], path: str, warnings: list[str]) -> None:
    hints = get_type_hints(type(obj))
    names = {f.name for f in dataclasses.fields(obj)}
    for key, value in data.items():
        full = f"{path}.{key}" if path else str(key)
        if key not in names:
            warnings.append(f"unknown config key '{full}' ignored")
            continue
        typ = hints[key]
        if dataclasses.is_dataclass(typ):
            if value is None:
                continue
            _coerce(value, typ, full)
            _merge(getattr(obj, key), value, full, warnings)
        else:
            setattr(obj, key, _coerce(value, typ, full))


def config_from_dict(data: dict[str, Any] | None) -> tuple[Config, list[str]]:
    cfg = Config()
    warnings: list[str] = []
    if data:
        if not isinstance(data, dict):
            raise ConfigError("top level of the config must be a mapping")
        _merge(cfg, data, "", warnings)
    validate(cfg)
    return cfg, warnings


def load_config(path: str | Path | None = None) -> Config:
    """Load YAML over built-in defaults. Raises ConfigError for invalid values."""
    import yaml  # noqa: PLC0415

    p = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config {p}: {exc}") from exc
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {p}: {exc}") from exc
    cfg, warnings = config_from_dict(data)
    for w in warnings:
        log.warning("%s (%s)", w, p)
    return cfg


def validate(cfg: Config) -> None:
    errors: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    from .i18n import available_languages  # noqa: PLC0415

    check(cfg.general.lang in available_languages(), f"general.lang '{cfg.general.lang}' has no phrase file")
    check(cfg.general.units in ("metric", "imperial"), "general.units must be metric|imperial")
    r = cfg.reflex
    check(0 < r.zone1_m < r.zone2_m < r.zone3_m <= 8.0, "reflex zones must satisfy 0 < zone1 < zone2 < zone3 <= 8 m")
    check(0 <= r.hysteresis_m < (r.zone2_m - r.zone1_m), "reflex.hysteresis_m must be smaller than zone widths")
    check(r.rate_hz > 0 and r.median_window >= 1, "reflex.rate_hz > 0 and median_window >= 1")
    d = cfg.dropoff
    check(0 < d.step_ratio < 1 < d.drop_ratio <= d.big_drop_ratio, "dropoff ratios: 0 < step < 1 < drop <= big_drop")
    check(0 < d.d0_min_m < d.d0_max_m, "dropoff.d0_min_m < d0_max_m")
    check(5 <= d.tilt_deg <= 90, "dropoff.tilt_deg in 5..90")
    check(d.sensitivity in ("low", "normal", "high"), "dropoff.sensitivity must be low|normal|high")
    check(d.sustain_s >= 0 and d.learn_window_s > 0, "dropoff timing must be positive")
    v = cfg.vision
    check(v.source in ("auto", "picamera2", "opencv", "video"), "vision.source invalid")
    check(v.dehaze in ("auto", "on", "off"), "vision.dehaze must be auto|on|off")
    check(10 <= v.hfov_deg <= 180, "vision.hfov_deg in 10..180")
    check(v.detector.color_order in ("rgb", "bgr"), "vision.detector.color_order must be rgb|bgr")
    check(v.detector.input_size % 32 == 0, "vision.detector.input_size must be a multiple of 32")
    check(0 < v.tracker.ttc_window_s <= v.tracker.ttc_max_window_s, "tracker ttc windows invalid")
    a = v.approach
    check(0 < a.p1_ttc_s <= a.p2_ttc_s <= a.p2_vehicle_ttc_s, "approach TTC thresholds must be ordered")
    check(0 < a.p2_min_height <= a.p1_min_height < 1, "approach height fractions invalid")
    check(a.confirm_frames >= 1, "approach.confirm_frames >= 1")
    h = cfg.haptics
    check(0 < h.max_duty <= 1.0, "haptics.max_duty must be in (0, 1]")
    check(h.duty_mode in ("cap", "scale"), "haptics.duty_mode must be cap|scale")
    check(1 <= h.tick_ms <= 50, "haptics.tick_ms in 1..50")
    au = cfg.audio
    check(au.backend in ("auto", "piper", "espeak-ng", "pyttsx3", "print"), "audio.backend invalid")
    check(au.max_queue >= 1 and 0 <= au.volume <= 100, "audio.max_queue >= 1, volume 0..100")
    b = cfg.buttons
    check(0 < b.short_max_s < b.long_min_s <= b.sos_hold_s, "buttons: short_max < long_min <= sos_hold")
    check(0 < b.double_gap_s and b.debounce_s < b.short_max_s, "buttons timing invalid")
    check(cfg.ble.chunk_size >= 20, "ble.chunk_size must be >= 20")
    check(2 <= cfg.ble.phone_say_min_level <= 4, "ble.phone_say_min_level in 2..4 (never P0/P1)")
    check(cfg.ble.security in ("none", "encrypt", "authenticated"), "ble.security must be none|encrypt|authenticated")
    check(cfg.ble.say_min_interval_s >= 0 and cfg.ble.pairing_window_s >= 0, "ble timing must be >= 0")
    check(b.shutdown_hold_s >= 1.0, "buttons.shutdown_hold_s >= 1")
    pw = cfg.power
    check(pw.poll_s > 0 and pw.undervoltage_hold_s >= 0 and pw.shutdown_delay_s >= 0, "power timing invalid")
    check(pw.overheat_clear_c < pw.overheat_c, "power.overheat_clear_c < overheat_c")
    check(0 < v.blocked.dark_pixel_frac <= 1.0, "vision.blocked.dark_pixel_frac in (0, 1]")
    check(0 < cfg.faces.cosine_threshold < 1, "faces.cosine_threshold in (0, 1)")
    check(0 < cfg.ocr.crop_frac <= 1, "ocr.crop_frac in (0, 1]")
    if errors:
        raise ConfigError("; ".join(errors))


def dropoff_ratios(d: DropoffConfig, sensitivity: str | None = None) -> tuple[float, float]:
    """(drop_ratio, step_ratio) for a sensitivity preset. 'normal' uses the configured values."""
    s = sensitivity or d.sensitivity
    if s == "low":
        return max(d.drop_ratio, 1.45), min(d.step_ratio, 0.55)
    if s == "high":
        return min(d.drop_ratio, 1.20), max(d.step_ratio, 0.80)
    return d.drop_ratio, d.step_ratio
