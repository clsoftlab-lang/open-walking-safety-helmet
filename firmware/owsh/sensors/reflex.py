"""Reflex path logic (spec §5.1, §5.2). Pure classes with injected timestamps.

This module never imports anything from the vision stack: the LiDAR -> haptics reflex must work
when the camera or the neural networks are broken (design principle P5).
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import deque
from dataclasses import dataclass

from ..config import DropoffConfig, ReflexConfig, dropoff_ratios

log = logging.getLogger("owsh.reflex")

NO_RETURN = math.inf  # internal representation of "no return" in the median filter


def valid_distance(dist_m: float | None, strength: int, min_strength: int) -> float | None:
    """Spec §5.1: strength < min_strength or distance = 0 counts as no return (None)."""
    if dist_m is None or dist_m <= 0 or strength < min_strength:
        return None
    return dist_m


class MedianFilter:
    """Median of the last N samples; no-return samples count as +infinity."""

    def __init__(self, window: int = 3) -> None:
        self.buf: deque[float] = deque(maxlen=max(1, window))

    def add(self, dist_m: float | None) -> float | None:
        self.buf.append(NO_RETURN if dist_m is None else float(dist_m))
        m = statistics.median(self.buf)
        return None if math.isinf(m) else m

    def reset(self) -> None:
        self.buf.clear()


class ZoneTracker:
    """Forward LiDAR zones with hysteresis.

    Zone numbers: 0 clear, 3 notice (<= 2.0 m), 2 warning (<= 1.2 m), 1 imminent (<= 0.6 m).
    Entering a more severe zone happens at the threshold; leaving it towards a less severe zone
    requires ``d > threshold + hysteresis``.
    """

    def __init__(self, cfg: ReflexConfig) -> None:
        self.cfg = cfg
        self.zone = 0
        self._no_return_since: float | None = None

    def _raw_zone(self, d: float | None, margin: float = 0.0) -> int:
        c = self.cfg
        if d is None:
            return 0
        if d <= c.zone1_m + margin:
            return 1
        if d <= c.zone2_m + margin:
            return 2
        if d <= c.zone3_m + margin:
            return 3
        return 0

    @staticmethod
    def _severity(zone: int) -> int:
        return 0 if zone == 0 else 4 - zone  # clear 0 < Z3 1 < Z2 2 < Z1 3

    def update(self, d: float | None, t: float | None = None) -> int:
        """Feed a filtered distance (None = no return). Returns the new zone."""
        raw = self._raw_zone(d)
        if d is not None:
            self._no_return_since = None
        if self._severity(raw) >= self._severity(self.zone):
            self.zone = raw
            return self.zone
        if d is None:
            # TF-Luna returns nothing below its 0.2 m minimum range: when an imminent obstacle
            # suddenly "disappears", hold Z1 briefly instead of going silent at once.
            if self.zone == 1 and t is not None:
                if self._no_return_since is None:
                    self._no_return_since = t
                if t - self._no_return_since < self.cfg.z1_no_return_hold_s:
                    return self.zone
            self.zone = 0
            return self.zone
        # Getting less severe: the distance must clear the current zone's outer threshold + hysteresis.
        held = self._raw_zone(d, margin=self.cfg.hysteresis_m)
        if self._severity(held) < self._severity(self.zone):
            self.zone = held
        return self.zone


@dataclass
class DropoffResult:
    kind: str  # "drop" | "step_up"
    dist_m: float | None
    d0_m: float
    big: bool


class DropoffDetector:
    """Down-looking LiDAR: auto-calibrated drop-off / step detector (spec §5.2).

    * d0 starts at ``sensor_height / sin(tilt)`` and is re-learned continuously as the median of
      the last ``learn_window_s`` of samples when their std-dev is low (level ground), clamped to
      ``d0_min_m..d0_max_m``.
    * Samples that are themselves hazards (outside the step/drop band) are NOT learned, except a
      stable *shorter* distance for ``relearn_shorter_after_s`` (e.g. the user sat down). A longer
      distance is never learned automatically unless ``allow_relearn_longer`` - otherwise standing
      still at a platform edge would teach the helmet that the track bed is "ground".
    * DROP: d > d0 * drop_ratio or no return (if ``no_return_is_drop``), sustained >= 120 ms.
    * STEP UP: d < d0 * step_ratio sustained >= 120 ms. Cooldown 3 s per type.
    """

    def __init__(self, cfg: DropoffConfig) -> None:
        self.cfg = cfg
        self.sensitivity = cfg.sensitivity
        self.d0 = self._clamp(cfg.sensor_height_m / math.sin(math.radians(cfg.tilt_deg)))
        self.calibrated = False
        self._window: deque[tuple[float, float]] = deque()
        self._cond_kind: str | None = None
        self._cond_since = 0.0
        self._last_alert: dict[str, float] = {}
        self._outside_since: float | None = None

    def _clamp(self, d: float) -> float:
        return min(self.cfg.d0_max_m, max(self.cfg.d0_min_m, d))

    def set_sensitivity(self, sensitivity: str) -> None:
        if sensitivity in ("low", "normal", "high"):
            self.sensitivity = sensitivity

    @property
    def ratios(self) -> tuple[float, float]:
        return dropoff_ratios(self.cfg, self.sensitivity)

    def classify(self, d: float | None) -> str | None:
        drop_r, step_r = self.ratios
        if d is None:
            return "drop" if self.cfg.no_return_is_drop else None
        if d > self.d0 * drop_r:
            return "drop"
        if d < self.d0 * step_r:
            return "step_up"
        return None

    def _learn(self, t: float, d: float | None) -> None:
        c = self.cfg
        if d is None:
            self._window.clear()
            self._outside_since = None
            return
        self._window.append((t, d))
        while self._window and t - self._window[0][0] > c.learn_window_s:
            self._window.popleft()
        if len(self._window) < 5 or t - self._window[0][0] < c.learn_window_s * 0.8:
            return
        values = [v for _, v in self._window]
        if statistics.pstdev(values) > c.learn_max_std_m:
            self._outside_since = None
            return
        median = statistics.median(values)
        kind = self.classify(median)
        if kind is None:
            self._outside_since = None
            self.d0 = self._clamp(median)
            self.calibrated = True
            return
        # stable but outside the band
        if self._outside_since is None:
            self._outside_since = t
        stable_for = t - self._outside_since
        if kind == "step_up" and stable_for >= c.relearn_shorter_after_s:
            self.d0 = self._clamp(median)
            self._outside_since = None
        elif kind == "drop" and c.allow_relearn_longer and stable_for >= c.relearn_shorter_after_s:
            self.d0 = self._clamp(median)
            self._outside_since = None

    def update(self, t: float, d: float | None) -> DropoffResult | None:
        """Feed one filtered sample (None = no return). Returns an alert or None."""
        c = self.cfg
        kind = self.classify(d)
        result: DropoffResult | None = None
        if kind != self._cond_kind:
            self._cond_kind = kind
            self._cond_since = t
        elif kind is not None and t - self._cond_since >= c.sustain_s - 1e-9:
            last = self._last_alert.get(kind)
            if last is None or t - last >= c.cooldown_s:
                self._last_alert[kind] = t
                big = d is None or (kind == "drop" and d > self.d0 * max(c.big_drop_ratio, self.ratios[0]))
                result = DropoffResult(kind, d, self.d0, big)
        self._learn(t, d)
        return result


# ------------------------------------------------------------------------------ worker
class ReflexWorker:
    """50 Hz thread: reads both TF-Lunas, publishes ZoneChanged / DropoffDetected.

    ``sensor_factory(name)`` returns a sensor with ``read() -> LidarReading`` or raises; a missing
    sensor is retried every 5 s and never crashes the loop (the watchdog raises the FAULT because
    no heartbeat arrives). Imports no vision code (P5).
    """

    RETRY_S = 5.0

    def __init__(self, reflex_cfg: ReflexConfig, dropoff_cfg: DropoffConfig, bus, clock, heartbeat,
                 sensor_factory) -> None:
        import threading  # noqa: PLC0415

        self.cfg = reflex_cfg
        self.dcfg = dropoff_cfg
        self.bus = bus
        self.clock = clock
        self.heartbeat = heartbeat  # callable(component)
        self.sensor_factory = sensor_factory
        self.zone = ZoneTracker(reflex_cfg)
        self.dropoff = DropoffDetector(dropoff_cfg)
        self.fwd_filter = MedianFilter(reflex_cfg.median_window)
        self.down_filter = MedianFilter(reflex_cfg.median_window)
        self.sensors: dict[str, object | None] = {"forward": None, "down": None}
        self._next_try = {"forward": 0.0, "down": 0.0}
        self.last: dict[str, float | None] = {"forward": None, "down": None}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._threading = threading

    def _sensor(self, name: str, now: float):
        s = self.sensors[name]
        if s is None and now >= self._next_try[name]:
            try:
                s = self.sensor_factory(name)
                self.sensors[name] = s
                log.info("lidar %s opened", name)
            except Exception as exc:  # noqa: BLE001
                self._next_try[name] = now + self.RETRY_S
                log.warning("lidar %s unavailable: %s", name, exc)
        return s

    def _read(self, name: str, now: float):
        s = self._sensor(name, now)
        if s is None:
            return None
        try:
            r = s.read()
        except Exception as exc:  # noqa: BLE001
            log.debug("lidar %s read failed: %s", name, exc)
            return None
        self.heartbeat(f"lidar_{name}")
        return r

    def step(self) -> None:
        from ..events import DropoffDetected, LidarSample, ZoneChanged  # noqa: PLC0415

        t = self.clock.now()
        r = self._read("forward", t)
        if r is None:
            self.fwd_filter.reset()
        else:
            d = valid_distance(r.dist_m, r.strength, self.cfg.min_strength)
            self.bus.publish(LidarSample(ts=t, sensor="forward", dist_m=d, strength=r.strength))
            m = self.fwd_filter.add(d)
            self.last["forward"] = m
            prev = self.zone.zone
            z = self.zone.update(m, t)
            if z != prev:
                log.info("reflex zone=%d prev=%d dist_m=%s sample_ts=%.4f", z, prev,
                         f"{m:.2f}" if m is not None else "none", t)
                self.bus.publish(ZoneChanged(ts=t, zone=z, previous=prev, dist_m=m))

        if self.dcfg.enabled:
            t2 = self.clock.now()
            r2 = self._read("down", t2)
            if r2 is None:
                self.down_filter.reset()
            else:
                d2 = valid_distance(r2.dist_m, r2.strength, self.cfg.min_strength)
                self.bus.publish(LidarSample(ts=t2, sensor="down", dist_m=d2, strength=r2.strength))
                m2 = self.down_filter.add(d2)
                self.last["down"] = m2
                res = self.dropoff.update(t2, m2)
                if res is not None:
                    log.info("reflex dropoff kind=%s dist_m=%s d0_m=%.2f big=%s sample_ts=%.4f", res.kind,
                             f"{res.dist_m:.2f}" if res.dist_m is not None else "none", res.d0_m, res.big, t2)
                    self.bus.publish(DropoffDetected(ts=t2, kind=res.kind, dist_m=res.dist_m,
                                                     d0_m=res.d0_m, big=res.big))

    def _run(self) -> None:
        period = 1.0 / self.cfg.rate_hz
        next_t = self.clock.now()
        while not self._stop.is_set():
            try:
                self.step()
            except Exception:  # noqa: BLE001 - the reflex loop must never die
                log.exception("reflex step failed")
            next_t += period
            delay = next_t - self.clock.now()
            if delay < -period:
                next_t = self.clock.now()
                delay = 0
            self._stop.wait(max(0.0, delay))

    def start(self) -> None:
        if self._thread is None:
            self._thread = self._threading.Thread(target=self._run, name="reflex", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        for s in self.sensors.values():
            if s is not None:
                try:
                    s.close()  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass
