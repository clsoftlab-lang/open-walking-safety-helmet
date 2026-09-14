"""Haptic pattern engine and mixer (spec §6).

* Patterns follow the authoritative table in spec §6.2.
* The mixer renders every active pattern and takes the **maximum** intensity per motor at each
  10 ms tick, so continuous reflex patterns and one-shot patterns coexist.
* ``haptics.max_duty`` (0.75) is applied in the backend, right before the PWM output, so no
  code path can overdrive the 3 V motors.
* Every motor off->on transition caused by a pattern that carries a ``source_ts`` is logged with
  the latency since that source sample (spec §11 T2).
"""

from __future__ import annotations

import itertools
import logging
import threading
from dataclasses import dataclass, field

from ..clock import Clock
from ..config import HapticsConfig, PinsConfig
from ..events import Level

log = logging.getLogger("owsh.haptics")

Intensity = tuple[float, float, float]  # left, center, right in 0..1
OFF: Intensity = (0.0, 0.0, 0.0)
MOTORS = ("L", "C", "R")


@dataclass(frozen=True)
class Segment:
    dur_s: float
    lcr: Intensity


@dataclass(frozen=True)
class Pattern:
    name: str
    segments: tuple[Segment, ...]
    loop: bool = False
    level: Level = Level.P4

    @property
    def duration_s(self) -> float:
        return sum(s.dur_s for s in self.segments)

    def value_at(self, t: float) -> Intensity | None:
        """Intensity at ``t`` seconds after start, or None when a one-shot has finished."""
        total = self.duration_s
        if t < 0:
            return OFF
        if total <= 0:
            return None
        if self.loop:
            t = t % total
        elif t >= total - 1e-9:
            return None
        acc = 0.0
        for seg in self.segments:
            acc += seg.dur_s
            if t < acc - 1e-9:
                return seg.lcr
        return self.segments[-1].lcr


def _side(side: str, x: float) -> Intensity:
    return {
        "left": (x, 0.0, 0.0),
        "center": (0.0, x, 0.0),
        "right": (0.0, 0.0, x),
        "all": (x, x, x),
    }[side]


def _pulses(n: int, on_ms: float, off_ms: float, lcr: Intensity) -> tuple[Segment, ...]:
    segs: list[Segment] = []
    for _ in range(n):
        segs.append(Segment(on_ms / 1000.0, lcr))
        segs.append(Segment(off_ms / 1000.0, OFF))
    return tuple(segs)


def make_pattern(pattern_id: str, *, level: Level | None = None, n: int = 1, repeats: int = 10) -> Pattern:
    """Build a pattern from the spec §6.2 table.

    ``pattern_id`` examples: ``tick``, ``zone2``, ``drop``, ``approach_left``,
    ``person_friend_right``, ``turn_left``, ``count`` (with ``n``), ``sos_countdown``, ``fault``.
    """
    pid = pattern_id
    if pid == "tick":
        return Pattern(pid, (Segment(0.040, _side("center", 0.60)),), level=Level.P4)
    if pid == "zone3":
        return Pattern(pid, _pulses(1, 60, 440, _side("center", 0.40)), loop=True, level=Level.P3)
    if pid == "zone2":
        return Pattern(pid, _pulses(1, 80, 120, _side("center", 0.70)), loop=True, level=Level.P2)
    if pid == "zone1":
        return Pattern(pid, (Segment(0.100, _side("center", 1.0)),), loop=True, level=Level.P1)
    if pid == "drop":
        return Pattern(pid, _pulses(2, 400, 150, _side("all", 1.0)), level=Level.P1)
    if pid == "step_up":
        return Pattern(pid, _pulses(3, 100, 100, _side("center", 0.80)), level=Level.P2)
    if pid.startswith("approach_"):
        side = pid.split("_", 1)[1]
        lvl = Level.P1 if level is None else level
        x = 1.0 if lvl <= Level.P1 else 0.70
        return Pattern(pid, _pulses(3, 150, 80, _side(side, x)), level=lvl)
    if pid.startswith("person_friend_"):
        side = pid.rsplit("_", 1)[1]
        return Pattern(pid, _pulses(2, 80, 120, _side(side, 0.60)), level=Level.P3)
    if pid.startswith("person_avoid_"):
        side = pid.rsplit("_", 1)[1]
        return Pattern(pid, _pulses(4, 60, 60, _side(side, 0.90)), level=Level.P2)
    if pid in ("turn_left", "turn_right"):
        side = pid.split("_", 1)[1]
        return Pattern(pid, _pulses(1, 250, 750, _side(side, 0.70)), loop=True, level=Level.P3)
    if pid == "count":
        n = max(1, min(10, int(n)))
        return Pattern(f"count_{n}", _pulses(n, 120, 280, _side("center", 0.70)), level=Level.P3)
    if pid == "sos_countdown":
        # 1 Hz, 200 ms @ 100 % on all motors; 10 repeats = 10 s (60 for the no-phone alarm)
        return Pattern(pid, _pulses(max(1, repeats), 200, 800, _side("all", 1.0)), level=Level.P0)
    if pid == "fault":
        return Pattern(pid, _pulses(3, 50, 50, _side("center", 1.0)), level=Level.P0)
    if pid == "ready":
        return Pattern(pid, (Segment(0.1, _side("left", 0.6)), Segment(0.1, _side("center", 0.6)),
                             Segment(0.1, _side("right", 0.6))), level=Level.P4)
    if pid == "ready_reverse":  # safe shutdown: ready pattern reversed R -> C -> L
        return Pattern(pid, (Segment(0.1, _side("right", 0.6)), Segment(0.1, _side("center", 0.6)),
                             Segment(0.1, _side("left", 0.6))), level=Level.P1)
    raise KeyError(f"unknown haptic pattern {pattern_id!r}")


# ------------------------------------------------------------------------------ mixer
@dataclass
class _Active:
    pattern: Pattern
    start: float
    source_ts: float | None
    logged: set[int] = field(default_factory=set)


class HapticMixer:
    """Pure mixer: no threads, no hardware. ``render(now)`` -> max intensity per motor."""

    def __init__(self) -> None:
        self._active: dict[str, _Active] = {}
        self._auto = itertools.count()

    def play(self, pattern: Pattern, now: float, key: str | None = None, source_ts: float | None = None) -> str:
        """Start ``pattern``. A pattern with the same ``key`` is replaced (restarted)."""
        k = key if key is not None else f"{pattern.name}#{next(self._auto)}"
        self._active[k] = _Active(pattern, now, source_ts)
        return k

    def ensure(self, pattern: Pattern, now: float, key: str, source_ts: float | None = None) -> None:
        """Start ``pattern`` under ``key`` unless the same pattern already runs there."""
        cur = self._active.get(key)
        if cur is None or cur.pattern != pattern:
            self.play(pattern, now, key, source_ts)

    def stop(self, key: str) -> bool:
        return self._active.pop(key, None) is not None

    def stop_prefix(self, prefix: str) -> None:
        for k in [k for k in self._active if k.startswith(prefix)]:
            del self._active[k]

    def is_active(self, key: str) -> bool:
        return key in self._active

    def active_names(self) -> list[str]:
        return [a.pattern.name for a in self._active.values()]

    def render(self, now: float) -> tuple[Intensity, list[tuple[int, str, float]]]:
        """Return (intensity, onsets). ``onsets`` lists (motor index, pattern name, source_ts)
        for patterns with a source timestamp whose first non-zero output on a motor is now."""
        out = [0.0, 0.0, 0.0]
        onsets: list[tuple[int, str, float]] = []
        finished = []
        for key, act in self._active.items():
            val = act.pattern.value_at(now - act.start)
            if val is None:
                finished.append(key)
                continue
            for i in range(3):
                if val[i] > out[i]:
                    out[i] = val[i]
                if val[i] > 0 and act.source_ts is not None and i not in act.logged:
                    act.logged.add(i)
                    onsets.append((i, act.pattern.name, act.source_ts))
        for key in finished:
            del self._active[key]
        return (out[0], out[1], out[2]), onsets


def intensity_to_duty(x: float, max_duty: float, mode: str = "cap") -> float:
    x = min(1.0, max(0.0, float(x)))
    if mode == "scale":
        return x * max_duty
    return min(x, max_duty)


# ---------------------------------------------------------------------------- backends
class HapticBackend:
    """Applies the ``max_duty`` cap, then writes duties via :meth:`_write`."""

    name = "base"

    def __init__(self, cfg: HapticsConfig) -> None:
        self.cfg = cfg
        self.duties: Intensity = OFF

    def set_intensities(self, lcr: Intensity) -> Intensity:
        duties = tuple(intensity_to_duty(v, self.cfg.max_duty, self.cfg.duty_mode) for v in lcr)
        self.duties = duties  # type: ignore[assignment]
        self._write(self.duties)
        return self.duties

    def _write(self, duties: Intensity) -> None:  # pragma: no cover - overridden
        pass

    def close(self) -> None:
        try:
            self._write(OFF)
        except Exception:  # noqa: BLE001
            pass


class SimHapticBackend(HapticBackend):
    name = "sim"

    def _write(self, duties: Intensity) -> None:
        log.debug("sim motors L=%.2f C=%.2f R=%.2f", *duties)


class GpioHapticBackend(HapticBackend):
    """gpiozero PWMOutputDevice on the ULN2003 inputs (GPIO high = motor on)."""

    name = "gpio"

    def __init__(self, cfg: HapticsConfig, pins: PinsConfig) -> None:
        super().__init__(cfg)
        from gpiozero import PWMOutputDevice  # noqa: PLC0415 - optional dependency

        freq = int(cfg.pwm_hz)
        self._devs = [PWMOutputDevice(p, active_high=True, initial_value=0, frequency=freq)
                      for p in (pins.haptic_left, pins.haptic_center, pins.haptic_right)]

    def _write(self, duties: Intensity) -> None:
        for dev, d in zip(self._devs, duties):
            dev.value = d

    def close(self) -> None:
        super().close()
        for dev in self._devs:
            dev.close()


def create_haptic_backend(cfg: HapticsConfig, pins: PinsConfig, sim: bool) -> tuple[HapticBackend, str | None]:
    """Return (backend, error). On failure a sim backend is returned with the error text so the
    caller raises a FAULT instead of crashing."""
    if sim:
        return SimHapticBackend(cfg), None
    try:
        return GpioHapticBackend(cfg, pins), None
    except Exception as exc:  # noqa: BLE001 - gpiozero/lgpio missing or GPIO busy
        log.error("GPIO haptics unavailable: %s", exc)
        return SimHapticBackend(cfg), str(exc)


class StatusLed:
    """Status LED for sighted helpers: on = running, slow blink = fault, fast blink = SOS."""

    def __init__(self, pin: int, sim: bool) -> None:
        self._led = None
        self.mode = "off"
        if not sim:
            try:
                from gpiozero import LED  # noqa: PLC0415

                self._led = LED(pin)
            except Exception as exc:  # noqa: BLE001
                log.warning("status LED unavailable: %s", exc)

    def set_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        self.mode = mode
        log.info("led mode=%s", mode)
        if self._led is None:
            return
        try:
            if mode == "on":
                self._led.on()
            elif mode == "slow_blink":
                self._led.blink(on_time=0.5, off_time=1.5, background=True)
            elif mode == "fast_blink":
                self._led.blink(on_time=0.1, off_time=0.1, background=True)
            else:
                self._led.off()
        except Exception as exc:  # noqa: BLE001
            log.warning("status LED error: %s", exc)

    def close(self) -> None:
        if self._led is not None:
            try:
                self._led.close()
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------------------------ engine
class HapticEngine:
    """Thread-safe engine: 10 ms tick loop that renders the mixer to the backend."""

    def __init__(self, cfg: HapticsConfig, backend: HapticBackend, clock: Clock) -> None:
        self.cfg = cfg
        self.backend = backend
        self.clock = clock
        self._mixer = HapticMixer()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.intensities: Intensity = OFF
        self.last_latency_ms: float | None = None

    # -- control API (called from any thread)
    def play(self, pattern_id: str | Pattern, key: str | None = None, source_ts: float | None = None,
             **kw) -> str:
        pattern = pattern_id if isinstance(pattern_id, Pattern) else make_pattern(pattern_id, **kw)
        with self._lock:
            k = self._mixer.play(pattern, self.clock.now(), key, source_ts)
        self._wake.set()
        return k

    def ensure(self, pattern_id: str | Pattern, key: str, source_ts: float | None = None, **kw) -> None:
        pattern = pattern_id if isinstance(pattern_id, Pattern) else make_pattern(pattern_id, **kw)
        with self._lock:
            self._mixer.ensure(pattern, self.clock.now(), key, source_ts)
        self._wake.set()

    def stop(self, key: str) -> None:
        with self._lock:
            self._mixer.stop(key)
        self._wake.set()

    def is_active(self, key: str) -> bool:
        with self._lock:
            return self._mixer.is_active(key)

    def active_names(self) -> list[str]:
        with self._lock:
            return self._mixer.active_names()

    # -- rendering
    def tick(self) -> Intensity:
        now = self.clock.now()
        with self._lock:
            lcr, onsets = self._mixer.render(now)
        prev = self.intensities
        self.intensities = lcr
        if lcr != prev:
            self.backend.set_intensities(lcr)
        for motor, name, src in onsets:
            latency = (now - src) * 1000.0
            self.last_latency_ms = latency
            log.info("haptic_on motor=%s pattern=%s source_ts=%.4f on_ts=%.4f latency_ms=%.1f",
                     MOTORS[motor], name, src, now, latency)
        return lcr

    def _run(self) -> None:
        period = self.cfg.tick_ms / 1000.0
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001
                log.exception("haptic tick failed")
            self._wake.wait(period)
            self._wake.clear()

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="haptics", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.backend.close()
