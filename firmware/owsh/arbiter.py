"""Hazard arbiter: events -> haptic patterns, speech and phone alerts, with cooldowns (spec §5, §6).

Also contains the SOS state machine (spec §7.3). Everything here is driven by events and an
explicit ``tick(now)`` so it can be unit-tested with a fake clock, fake haptics and fake speech.

Priorities (spec §6.1): haptics are mixed (max per motor, see ``output/haptics.py``); speech uses
strict preemption (``output/audio.py``). Handlers are called synchronously from sensor threads and
only enqueue work, so they are fast.
"""

from __future__ import annotations

import itertools
import logging
import threading
import uuid
from typing import Any, Protocol

from .clock import Clock
from .config import Config
from .events import (
    ApproachAlert,
    Direction,
    DropoffDetected,
    FaceSeen,
    FaultChanged,
    Level,
    ZoneChanged,
)
from .i18n import I18n

log = logging.getLogger("owsh.arbiter")

# Components whose failure makes warnings untrustworthy: P0 FAULT pattern + voice, repeated every
# 10 s (spec §5.7, P4). Other components (faces, OCR, BLE, config) are announced once at P2.
CRITICAL_COMPONENTS = frozenset({
    "camera", "camera_blocked", "detector", "lidar_forward", "lidar_down", "imu", "audio",
    "haptics", "buttons",
})
VISION_COMPONENTS = frozenset({"camera", "camera_blocked", "detector"})
ZONE_LEVEL = {3: Level.P3, 2: Level.P2, 1: Level.P1}


class Haptics(Protocol):
    def play(self, pattern_id: str, key: str | None = None, source_ts: float | None = None, **kw: Any) -> str: ...
    def ensure(self, pattern_id: str, key: str, source_ts: float | None = None, **kw: Any) -> None: ...
    def stop(self, key: str) -> None: ...


class Speaker(Protocol):
    muted: bool

    def say(self, text: str, level: Level, requested: bool = False, cacheable: bool = False) -> None: ...


class LinkLike(Protocol):
    @property
    def connected(self) -> bool: ...

    def send(self, msg_type: str, **fields: Any) -> None: ...


class Cooldown:
    def __init__(self) -> None:
        self._last: dict[Any, float] = {}

    def ready(self, key: Any, now: float, period_s: float) -> bool:
        """True (and restarts the period) if ``period_s`` elapsed since the last accepted call."""
        last = self._last.get(key)
        if last is not None and now - last < period_s:
            return False
        self._last[key] = now
        return True


class Arbiter:
    def __init__(self, cfg: Config, clock: Clock, haptics: Haptics, speech: Speaker, link: LinkLike,
                 i18n: I18n) -> None:
        self.cfg = cfg
        self.clock = clock
        self.haptics = haptics
        self.speech = speech
        self.link = link
        self.i18n = i18n
        self.cooldown = Cooldown()
        self.faults: dict[str, str] = {}
        self._last_fault_repeat = 0.0
        self._lock = threading.RLock()
        self._alert_ids = itertools.count(1)
        self.zone = 0
        self.last_speech: str = ""

    # ----------------------------------------------------------------------------- helpers
    def say(self, key: str, level: Level, requested: bool = False, **params: Any) -> str:
        text = self.i18n.sentence(key, **params)
        self.speech.say(text, level, requested=requested, cacheable=not params)
        self.last_speech = text
        return text

    def alert(self, level: Level, kind: str, direction: str, text: str, dist_m: float | None = None,
              label: str | None = None) -> None:
        """Send an ``alert`` to the phone for every spoken/haptic alert of P3 or more important."""
        if level > Level.P3:
            return
        self.link.send("alert", id=next(self._alert_ids), level=int(level), kind=kind, dir=direction,
                       dist_m=None if dist_m is None else round(dist_m, 2), label=label, text=text)

    def subscribe(self, bus) -> None:
        bus.subscribe(ZoneChanged, self.on_zone)
        bus.subscribe(DropoffDetected, self.on_dropoff)
        bus.subscribe(ApproachAlert, self.on_approach)
        bus.subscribe(FaceSeen, self.on_face)
        bus.subscribe(FaultChanged, self.on_fault)

    # -------------------------------------------------------------------------- reflex path
    def on_zone(self, ev: ZoneChanged) -> None:
        with self._lock:
            now = self.clock.now()
            r = self.cfg.reflex
            self.zone = ev.zone
            if ev.zone == 0 or "lidar_forward" in self.faults:
                self.haptics.stop("zone")
                return
            self.haptics.ensure(f"zone{ev.zone}", key="zone", source_ts=ev.ts)
            level = ZONE_LEVEL[ev.zone]
            text = ""
            if ev.zone == 1:
                if self.cooldown.ready("voice_z1", now, r.zone1_voice_cooldown_s):
                    text = self.say("obstacle.stop", Level.P1)
            elif ev.zone == 2:
                if ev.previous in (0, 3) and self.cooldown.ready("voice_z2", now, r.zone2_voice_cooldown_s):
                    text = self.say("obstacle.ahead", Level.P2)
            if ev.zone in (1, 2) or self.cooldown.ready("alert_z3", now, r.zone3_alert_cooldown_s):
                self.alert(level, "obstacle", "center", text, dist_m=ev.dist_m)

    def on_dropoff(self, ev: DropoffDetected) -> None:
        with self._lock:
            if ev.kind == "drop":
                self.haptics.play("drop", key="dropoff", source_ts=ev.ts)
                text = self.say("drop.big" if ev.big else "drop.step_down", Level.P1)
                self.alert(Level.P1, "drop", "center", text, dist_m=ev.dist_m)
            elif ev.kind == "step_up":
                self.haptics.play("step_up", key="dropoff", source_ts=ev.ts)
                text = self.say("drop.step_up", Level.P2)
                self.alert(Level.P2, "step_up", "center", text, dist_m=ev.dist_m)

    # --------------------------------------------------------------------------- vision path
    def on_approach(self, ev: ApproachAlert) -> None:
        with self._lock:
            level = Level.P1 if ev.level <= Level.P1 else Level.P2
            side = ev.direction.value if ev.direction != Direction.ALL else "center"
            self.haptics.play(f"approach_{side}", key=f"approach_{side}", source_ts=ev.ts, level=level)
            what = self.i18n.class_name(ev.label)
            text = self.say(f"approach.p{int(level)}.{side}", level, what=what)
            self.alert(level, "approach", side, text, label=ev.label)

    def on_face(self, ev: FaceSeen) -> None:
        with self._lock:
            now = self.clock.now()
            if not self.cooldown.ready(("face", ev.name), now, self.cfg.faces.cooldown_s):
                return
            side = ev.direction.value if ev.direction != Direction.ALL else "center"
            if ev.tag == "avoid":
                self.haptics.play(f"person_avoid_{side}", source_ts=ev.ts)
                text = self.say(f"face.avoid.{side}", Level.P2, name=ev.name)
                self.alert(Level.P2, "face", side, text, label=ev.name)
            else:
                self.haptics.play(f"person_friend_{side}", source_ts=ev.ts)
                text = self.say(f"face.friend.{side}", Level.P3, name=ev.name)
                self.alert(Level.P3, "face", side, text, label=ev.name)

    # -------------------------------------------------------------------------------- faults
    def critical_faults(self) -> list[str]:
        return sorted(c for c in self.faults if c in CRITICAL_COMPONENTS)

    def _fault_text(self, component: str) -> str:
        if component == "camera_blocked":
            return self.i18n.t("fault.camera_blocked")
        return self.i18n.sentence("fault.active", component=self.i18n.component(component))

    def on_fault(self, ev: FaultChanged) -> None:
        with self._lock:
            now = self.clock.now()
            comp = ev.component
            if ev.active:
                if comp in self.faults:
                    return
                self.faults[comp] = ev.detail
                if comp == "lidar_forward":
                    self.haptics.stop("zone")
                text = self._fault_text(comp)
                if comp in CRITICAL_COMPONENTS:
                    self.haptics.play("fault", key="fault", source_ts=ev.ts)
                    if comp in VISION_COMPONENTS and "lidar_forward" not in self.faults:
                        text = f"{text} {self.i18n.t('fault.lidar_still_active')}"
                    self.speech.say(text, Level.P0)
                    self._last_fault_repeat = now
                    self.alert(Level.P0, "fault", "all", text, label=comp)
                else:
                    self.speech.say(text, Level.P2)
                    self.alert(Level.P2, "fault", "all", text, label=comp)
                self.last_speech = text
            else:
                if comp not in self.faults:
                    return
                del self.faults[comp]
                if comp == "camera_blocked":
                    name = self.i18n.t("component.camera")
                else:
                    name = self.i18n.component(comp)
                text = self.say("fault.recovered", Level.P2, component=name)
                self.alert(Level.P2, "fault", "all", text, label=comp)

    def tick(self, now: float) -> None:
        """Periodic work: FAULT repeats every ``fault_repeat_s`` while a critical fault is active."""
        with self._lock:
            crit = self.critical_faults()
            if crit and now - self._last_fault_repeat >= self.cfg.watchdog.fault_repeat_s:
                self._last_fault_repeat = now
                self.haptics.play("fault", key="fault")
                names = ", ".join(self.i18n.component(c) for c in crit)
                self.speech.say(self.i18n.t("fault.repeat", components=names), Level.P0)


class SosManager:
    """SOS flow (spec §7.3).

    IDLE -> COUNTDOWN (10 s, ``sos_countdown`` pattern, any button cancels)
         -> SENT (phone connected; ``sos`` repeated every 5 s until ``ack``) -> IDLE on ack
         -> NO_PHONE (no phone: "Phone not connected" every 10 s + pattern for 60 s, LED fast)
            -> PENDING (after 60 s; still sends as soon as a phone connects)
    Interpretation: "Emergency alert sent" is spoken when the phone acknowledges; on the first
    transmission the helmet says "Sending emergency alert to the phone".
    """

    IDLE, COUNTDOWN, SENT, NO_PHONE, PENDING = "idle", "countdown", "sent", "no_phone", "pending"

    def __init__(self, cfg: Config, clock: Clock, haptics: Haptics, speech: Speaker, link: LinkLike,
                 i18n: I18n) -> None:
        self.cfg = cfg
        self.clock = clock
        self.haptics = haptics
        self.speech = speech
        self.link = link
        self.i18n = i18n
        self.state = self.IDLE
        self.sos_id = ""
        self.reason = ""
        self._t_state = 0.0
        self._last_send = 0.0
        self._last_voice = 0.0
        self._lock = threading.RLock()

    @property
    def cancellable(self) -> bool:
        return self.state in (self.COUNTDOWN, self.NO_PHONE)

    @property
    def active(self) -> bool:
        return self.state != self.IDLE

    def _say(self, key: str, level: Level = Level.P0, **params: Any) -> None:
        self.speech.say(self.i18n.sentence(key, **params), level, requested=True, cacheable=not params)

    def _send(self, state: str) -> None:
        self.link.send("sos", id=self.sos_id, reason=self.reason, state=state)

    def trigger(self, reason: str) -> bool:
        with self._lock:
            if self.state in (self.COUNTDOWN, self.SENT, self.NO_PHONE):
                return False
            now = self.clock.now()
            self.state = self.COUNTDOWN
            self.reason = reason if reason in ("button", "fall") else "button"
            self.sos_id = uuid.uuid4().hex[:8]
            self._t_state = now
            log.warning("SOS countdown started reason=%s id=%s", self.reason, self.sos_id)
            reps = max(1, int(round(self.cfg.sos.countdown_s)))
            self.haptics.play("sos_countdown", key="sos", repeats=reps)
            if self.reason == "fall":
                self._say("sos.fall_detected")
            self._say("sos.countdown", seconds=int(round(self.cfg.sos.countdown_s)))
            if self.link.connected:
                self._send("countdown")
            return True

    def cancel(self) -> bool:
        with self._lock:
            if not self.cancellable:
                return False
            log.warning("SOS cancelled id=%s state=%s", self.sos_id, self.state)
            self.state = self.IDLE
            self.haptics.stop("sos")
            self._say("sos.cancelled", Level.P1)
            if self.link.connected:
                self._send("cancelled")
            return True

    def on_ack(self, ack_id: Any) -> None:
        with self._lock:
            if self.state in (self.SENT, self.NO_PHONE, self.PENDING) and str(ack_id) == self.sos_id:
                log.warning("SOS acknowledged by phone id=%s", self.sos_id)
                self.state = self.IDLE
                self.haptics.stop("sos")
                self._say("sos.sent")

    def _transmit(self, now: float) -> None:
        first = self.state != self.SENT
        self._send("sent")
        self._last_send = now
        if first:
            self.state = self.SENT
            self.haptics.stop("sos")
            self._say("sos.sending", Level.P1)

    def on_connection(self, connected: bool) -> None:
        with self._lock:
            if connected and self.state in (self.NO_PHONE, self.PENDING):
                self._transmit(self.clock.now())

    def tick(self, now: float) -> None:
        with self._lock:
            s = self.cfg.sos
            if self.state == self.COUNTDOWN and now - self._t_state >= s.countdown_s:
                if self.link.connected:
                    self._transmit(now)
                else:
                    log.warning("SOS: no phone connected, local alarm")
                    self.state = self.NO_PHONE
                    self._t_state = now
                    self._last_voice = now
                    self.haptics.play("sos_countdown", key="sos", repeats=int(round(s.no_phone_alarm_s)))
                    self._say("phone.not_connected")
            elif self.state == self.SENT:
                if self.link.connected and now - self._last_send >= s.resend_s:
                    self._send("sent")
                    self._last_send = now
            elif self.state == self.NO_PHONE:
                if now - self._t_state >= s.no_phone_alarm_s:
                    self.state = self.PENDING
                    self.haptics.stop("sos")
                elif now - self._last_voice >= s.no_phone_voice_every_s:
                    self._last_voice = now
                    self._say("phone.not_connected")
