"""Watchdog (spec §5.7): heartbeats -> FAULT events, plus the camera-blocked detector.

Principle P4: silence must never mean "safe" when something is broken. Every component that
registers must beat within its timeout, *including right after start-up* - a camera that never
delivers a first frame is a fault too.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

from .bus import EventBus
from .clock import Clock
from .config import BlockedConfig
from .events import FaultChanged

log = logging.getLogger("owsh.watchdog")


@dataclass
class _Component:
    timeout_s: float
    last_beat: float
    faulted: bool = False


class Watchdog:
    def __init__(self, bus: EventBus, clock: Clock) -> None:
        self.bus = bus
        self.clock = clock
        self._lock = threading.Lock()
        self._components: dict[str, _Component] = {}
        self._external: dict[str, str] = {}  # component -> detail, faults set explicitly
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick_hooks: list[Callable[[float], None]] = []

    def register(self, component: str, timeout_s: float, startup_grace_s: float = 0.0) -> None:
        """``startup_grace_s`` extends only the deadline of the *first* heartbeat (e.g. camera
        start-up and model loading); afterwards the plain timeout applies."""
        with self._lock:
            self._components[component] = _Component(timeout_s, self.clock.now() + startup_grace_s)

    def unregister(self, component: str) -> None:
        with self._lock:
            comp = self._components.pop(component, None)
        if comp is not None and comp.faulted:
            self._publish(component, False, "unregistered")

    def beat(self, component: str) -> None:
        now = self.clock.now()
        recovered = False
        with self._lock:
            comp = self._components.get(component)
            if comp is None:
                return
            comp.last_beat = now
            if comp.faulted:
                comp.faulted = False
                recovered = True
        if recovered:
            log.warning("component %s recovered", component)
            self._publish(component, False, "heartbeat resumed")

    def set_fault(self, component: str, active: bool, detail: str = "") -> None:
        """Explicit faults (camera blocked, audio backend init failure, missing hardware...)."""
        with self._lock:
            was = component in self._external
            if active:
                self._external[component] = detail
            else:
                self._external.pop(component, None)
        if active != was:
            log.warning("fault %s active=%s %s", component, active, detail)
            self._publish(component, active, detail)

    def _publish(self, component: str, active: bool, detail: str) -> None:
        self.bus.publish(FaultChanged(ts=self.clock.now(), component=component, active=active, detail=detail))

    def active_faults(self) -> list[str]:
        with self._lock:
            hb = [n for n, c in self._components.items() if c.faulted]
            return sorted(set(hb) | set(self._external))

    def check(self, now: float | None = None) -> None:
        now = self.clock.now() if now is None else now
        newly: list[tuple[str, float]] = []
        with self._lock:
            for name, comp in self._components.items():
                if not comp.faulted and now - comp.last_beat > comp.timeout_s:
                    comp.faulted = True
                    newly.append((name, now - comp.last_beat))
        for name, age in newly:
            log.error("component %s heartbeat timeout (%.2fs)", name, age)
            self._publish(name, True, f"no heartbeat for {age:.1f}s")

    def add_tick_hook(self, hook: Callable[[float], None]) -> None:
        """Run ``hook(now)`` in the watchdog thread every check (arbiter/SOS timers)."""
        self._tick_hooks.append(hook)

    def _run(self, period: float) -> None:
        while not self._stop.wait(period):
            now = self.clock.now()
            try:
                self.check(now)
            except Exception:  # noqa: BLE001
                log.exception("watchdog check failed")
            for hook in self._tick_hooks:
                try:
                    hook(now)
                except Exception:  # noqa: BLE001
                    log.exception("watchdog hook failed")

    def start(self, check_hz: float = 10.0) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, args=(1.0 / check_hz,), name="watchdog", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)


class CameraBlockedDetector:
    """Lens covered / pitch dark / smeared (spec §5.7).

    blocked when (mean < 12 and std < 6) for >= 3 s, or Laplacian variance < 5 for >= 5 s.
    Clears after both conditions have been false for ``clear_hold_s``.

    Extension (safer than the spec wording): a frame is also "dark" when at least
    ``dark_pixel_frac`` (97 %) of its pixels are darker than ``dark_mean_max``. Without it a
    covered lens with a tiny light leak, or a camera driver that overlays a small "camera off"
    icon on black frames (seen with a Windows privacy shutter: mean 0.3, std 8.7), is missed
    because the few bright pixels push the std-dev above 6.
    Feed it ``update(t, mean, std, lapvar, dark_frac)``; see ``vision.preprocess.frame_stats_ex``.
    """

    def __init__(self, cfg: BlockedConfig) -> None:
        self.cfg = cfg
        self.blocked = False
        self.reason = ""
        self._dark_since: float | None = None
        self._blur_since: float | None = None
        self._clear_since: float | None = None

    def update(self, t: float, mean: float, std: float, lapvar: float, dark_frac: float = 0.0) -> bool | None:
        """Returns True when it becomes blocked, False when it clears, None when unchanged."""
        c = self.cfg
        dark = (mean < c.dark_mean_max and std < c.dark_std_max) or dark_frac >= c.dark_pixel_frac
        blur = lapvar < c.blur_lapvar_max
        self._dark_since = (self._dark_since if self._dark_since is not None else t) if dark else None
        self._blur_since = (self._blur_since if self._blur_since is not None else t) if blur else None
        dark_hit = dark and t - self._dark_since >= c.dark_hold_s - 1e-9  # type: ignore[operator]
        blur_hit = blur and t - self._blur_since >= c.blur_hold_s - 1e-9  # type: ignore[operator]
        if not self.blocked:
            if dark_hit or blur_hit:
                self.blocked = True
                self.reason = "dark" if dark_hit else "blur"
                self._clear_since = None
                return True
            return None
        if dark or blur:
            self._clear_since = None
            return None
        if self._clear_since is None:
            self._clear_since = t
        if t - self._clear_since >= c.clear_hold_s - 1e-9:
            self.blocked = False
            self.reason = ""
            return False
        return None
