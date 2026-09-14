"""Application wiring: threads, event bus, arbiter, SOS, watchdog, buttons, phone link.

Thread overview (spec §3): reflex (50 Hz LiDAR), imu (100 Hz), vision, faces (<= 2 Hz), haptics
(10 ms mixer), speech, buttons (poll), watchdog (10 Hz, also drives arbiter/SOS timers), ble.
The dashboard (``--sim`` with a window) runs in the main thread because GUI toolkits need it.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .arbiter import Arbiter, Cooldown, SosManager
from .bus import EventBus
from .clock import SYSTEM_CLOCK, Clock
from .config import Config
from .events import ButtonGesture, Detections, FallDetected, Level, PowerWarning
from .i18n import I18n
from .input.buttons import ButtonInput
from .link.ble import Link, NullLink, create_link
from .output.audio import SpeechOutput, create_tts_backend
from .output.haptics import HapticEngine, StatusLed, create_haptic_backend
from .sensors.imu import ImuWorker, Mpu6050, SimImu
from .sensors.power import THROTTLED_NOW, UNDERVOLTAGE_NOW, PowerControl, PowerMonitor, PowerWorker
from .sensors.reflex import ReflexWorker
from .sensors.tfluna import SimLidar, TFLunaI2C
from .watchdog import Watchdog

log = logging.getLogger("owsh.app")


def cpu_temp_c() -> float | None:
    try:
        return round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000.0, 1)
    except (OSError, ValueError):
        return None


@dataclass
class SimState:
    """Values the dashboard sliders/keys change in --sim."""

    forward_m: float = 0.0  # <= 0 = no return
    down_m: float = 2.2
    undervoltage: bool = False
    overheat: bool = False


@dataclass
class RunOptions:
    sim: bool = False
    window: bool = True
    max_seconds: float | None = None
    frames: int | None = None
    tts: str | None = None
    ble: bool = True
    realtime: bool = True
    save_dir: str | None = None
    save_every: int = 0
    config_error: str | None = None


class Controller:
    """Buttons, SOS triggers, phone messages, status reports and location requests."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self.location: dict[str, Any] | None = None
        self.location_t = -1e9
        self._location_wait_until: float | None = None
        self._last_status_t = -1e9
        self._last_status_key: tuple | None = None
        self._ocr_busy = threading.Lock()
        self.started_t = app.clock.now()
        self._cooldown = Cooldown()
        self.volume = app.cfg.audio.volume
        self.shutting_down = False
        self.power: PowerMonitor | None = None

    # -- helpers
    @property
    def i18n(self) -> I18n:
        return self.app.i18n

    def say(self, key: str, level: Level = Level.P3, requested: bool = True, **params: Any) -> None:
        self.app.speech.say(self.i18n.sentence(key, **params), level, requested=requested, cacheable=not params)

    # -- buttons
    def on_gesture(self, ev: ButtonGesture) -> None:
        app = self.app
        if ev.button == "b1+b3" and ev.gesture == "shutdown":
            self.shutdown()
            return
        if ev.gesture == "press":
            app.haptics.play("tick", key="tick", source_ts=ev.ts)
            if app.sos.cancellable:
                app.sos.cancel()
                app.buttons.cancel_all()
            return
        action = {
            ("b1", "short"): self.read_text,
            ("b1", "long"): self.repeat_last,
            ("b2", "short"): self.describe,
            ("b2", "long"): self.where_am_i,
            ("b2", "double"): self.who_is_here,
            ("b3", "short"): self.status_report,
            ("b3", "long"): lambda: app.sos.trigger("button"),
            ("b3", "double"): self.toggle_mute,
        }.get((ev.button, ev.gesture))
        if action is None:
            log.info("no action for %s %s", ev.button, ev.gesture)
            return
        action()

    def _fresh_frame(self, max_age_s: float = 1.5):
        vision = self.app.vision
        if vision is None:
            return None, None
        frame, det = vision.latest()
        if frame is None or det is None or self.app.clock.now() - det.ts > max_age_s:
            return None, None
        return frame, det

    def read_text(self) -> None:
        ocr = self.app.ocr
        if ocr is None or not ocr.available:
            self.say("ocr.not_installed")
            return
        frame, _ = self._fresh_frame()
        if frame is None:
            self.say("describe.no_camera")
            return
        if not self._ocr_busy.acquire(blocking=False):
            return

        def work() -> None:
            try:
                res = ocr.read(frame)
                if res is None:
                    self.say("ocr.no_text")
                    return
                text = self.i18n.t("ocr.warning_prefix", text=res.text) if res.warning else res.text
                self.app.speech.say(text, Level.P3, requested=True)
                self.app.arbiter.alert(Level.P3, "sign", "center", text)
            except Exception:  # noqa: BLE001
                log.exception("OCR failed")
                self.say("ocr.failed")
            finally:
                self._ocr_busy.release()

        threading.Thread(target=work, name="ocr", daemon=True).start()

    def repeat_last(self) -> None:
        text = self.app.speech.last_text
        if text:
            self.app.speech.say(text, Level.P3, requested=True)
        else:
            self.say("repeat.nothing")

    def describe(self) -> None:
        from .vision.describe import describe_scene  # noqa: PLC0415

        _, det = self._fresh_frame()
        if det is None:
            self.say("describe.no_camera")
            return
        self.app.speech.say(describe_scene(det.tracks, self.i18n,self.app.cfg.vision.describe_max_objects),
                            Level.P3, requested=True)

    def where_am_i(self) -> None:
        app = self.app
        now = app.clock.now()
        if app.link.connected:
            app.link.send("need_location")
        if self.location is not None and now - self.location_t <= app.cfg.location.fresh_s:
            self._speak_location()
        elif app.link.connected:
            self._location_wait_until = now + app.cfg.location.wait_s
        else:
            self.say("phone.not_connected")

    def _speak_location(self) -> None:
        loc = self.location or {}
        if loc.get("addr"):
            self.say("location.address", addr=loc["addr"])
            return
        acc = loc.get("acc_m")
        imperial = self.app.cfg.general.units == "imperial"
        if acc is None:
            self.say("location.unavailable")
            return
        value = round(acc * 3.28084) if imperial else round(acc)
        self.say("location.no_address", acc=value, unit=self.i18n.t("unit.feet" if imperial else "unit.meters"))

    def who_is_here(self) -> None:
        faces = self.app.faces
        if faces is None:
            self.say("face.not_available")
            return

        def done(results) -> None:
            if results is None:
                self.say("face.not_available")
                return
            from .vision.tracker import direction_from_angle, horizontal_angle_deg  # noqa: PLC0415

            frame, _ = self.app.vision.latest() if self.app.vision else (None, None)
            width = frame.shape[1] if frame is not None else 1280
            known = [r for r in results if r.name]
            if not known:
                if results:
                    self.say("face.unknown", count=len(results))
                else:
                    self.say("face.none")
                return
            for r in known:
                angle = horizontal_angle_deg((r.box[0] + r.box[2]) / 2.0, width, self.app.cfg.vision.hfov_deg)
                side = direction_from_angle(angle, self.app.cfg.vision.tracker.center_deg).value
                key = f"face.avoid.{side}" if r.tag == "avoid" else f"face.friend.{side}"
                self.say(key, Level.P2 if r.tag == "avoid" else Level.P3, name=r.name)

        faces.request(done)

    def status_report(self) -> None:
        app = self.app
        faults = app.watchdog.active_faults()
        if faults:
            names = ", ".join(self.i18n.component(c) for c in faults)
            self.say("status.faults", components=names)
        else:
            self.say("status.ok")
        self.say("status.phone_connected" if app.link.connected else "status.phone_disconnected")
        if app.speech.muted:
            self.say("status.muted")

    def toggle_mute(self) -> None:
        sp = self.app.speech
        sp.set_muted(not sp.muted)
        self.say("mute.on" if sp.muted else "mute.off", Level.P4)
        self.send_status(force=True)

    def shutdown(self) -> None:
        """Safe shutdown (B1 + B3 held 5 s): voice, reversed ready pattern, then poweroff."""
        app = self.app
        if self.shutting_down:
            return
        self.shutting_down = True
        log.warning("safe shutdown requested by button chord")
        self.say("power.shutting_down", Level.P1)
        app.haptics.play("ready_reverse", key="shutdown")
        timer = threading.Timer(app.cfg.power.shutdown_delay_s, app.power_control.poweroff)
        timer.daemon = True
        timer.start()

    def on_power_status(self, monitor: PowerMonitor) -> None:
        prev = None if self.power is None else (self.power.undervoltage, self.power.throttled)
        self.power = monitor
        if prev is not None and prev != (monitor.undervoltage, monitor.throttled):
            self.send_status(force=True)

    def on_power_warning(self, ev: PowerWarning) -> None:
        key = "power.low" if ev.kind == "undervoltage" else "power.overheating"
        text = self.i18n.sentence(key)
        self.app.speech.say(text, Level.P2)
        self.app.arbiter.alert(Level.P2, "fault", "all", text, label=ev.kind)

    def on_new_bond(self, name: str) -> None:
        clean = "".join(ch for ch in str(name) if ch.isprintable())[:30] or "?"
        self.say("ble.phone_paired", Level.P2, name=clean)

    def on_fall(self, ev: FallDetected) -> None:
        self.app.sos.trigger("fall")

    # -- phone
    def on_phone(self, msg: dict[str, Any]) -> None:
        app = self.app
        t = msg["t"]
        log.info("phone rx %s", t)
        if t == "loc":
            self.location = msg
            self.location_t = app.clock.now()
            if self._location_wait_until is not None:
                self._location_wait_until = None
                self._speak_location()
        elif t == "ack":
            app.sos.on_ack(msg["id"])
        elif t == "ping":
            app.link.send("pong", id=msg["id"])
        elif t == "say":
            # capped at P2 by protocol.validate_phone; at most one per ble.say_min_interval_s
            if not self._cooldown.ready("phone_say", app.clock.now(), app.cfg.ble.say_min_interval_s):
                log.warning("phone say dropped (rate limit %.1f s)", app.cfg.ble.say_min_interval_s)
                return
            app.speech.say(msg["text"], Level(max(2, msg["level"])), requested=True)
        elif t == "cfg":
            self._apply_cfg(msg)

    def _apply_cfg(self, msg: dict[str, Any]) -> None:
        """Apply phone settings. Changes that reduce safety are always confirmed by voice (P2,
        not affected by mute) so the wearer knows: mute on, drop-off sensitivity low, volume < 30."""
        app = self.app
        if "lang" in msg and msg["lang"] != app.i18n.lang and app.i18n.set_lang(msg["lang"]):
            self.say("settings.language_changed", Level.P4)
        if "muted" in msg:
            was = app.speech.muted
            app.speech.set_muted(msg["muted"])
            if msg["muted"] and not was:
                self.say("ble.cfg_muted", Level.P2)
        if "volume" in msg:
            volume = int(msg["volume"])
            try:
                app.speech.backend.set_volume(volume)
            except Exception:  # noqa: BLE001
                log.exception("set_volume failed")
            if volume < app.cfg.ble.confirm_volume_below and volume != self.volume:
                self.say("ble.cfg_volume_low", Level.P2, volume=volume)
            self.volume = volume
        if "dropoff_sensitivity" in msg and app.reflex is not None:
            before = app.reflex.dropoff.sensitivity
            level = msg["dropoff_sensitivity"]
            app.reflex.dropoff.set_sensitivity(level)
            if level != before:
                if level == "low":
                    self.say("ble.cfg_sensitivity_low", Level.P2)
                else:
                    self.say("settings.sensitivity_changed", Level.P4)
        self.send_status(force=True)

    def on_connection(self, connected: bool) -> None:
        app = self.app
        if connected:
            app.link.send("hello", fw=__version__, lang=app.i18n.lang, features=app.features())
            self.send_status(force=True)
        app.sos.on_connection(connected)

    def send_status(self, force: bool = False) -> None:
        app = self.app
        if not app.link.connected:
            return
        faults = app.watchdog.active_faults()
        pw = self.power
        uv = None if pw is None else pw.undervoltage
        thr = None if pw is None else pw.throttled
        key = (tuple(faults), app.speech.muted, uv, thr)
        now = app.clock.now()
        if not force and key == self._last_status_key and now - self._last_status_t < app.cfg.ble.status_every_s:
            return
        self._last_status_key = key
        self._last_status_t = now
        fps = app.vision.fps if app.vision is not None else 0.0
        app.link.send("status", uptime_s=int(now - self.started_t), cpu_temp_c=cpu_temp_c(), fps=round(fps, 1),
                      faults=faults, muted=app.speech.muted, undervoltage=uv, throttled=thr)

    def tick(self, now: float) -> None:
        if self._location_wait_until is not None and now >= self._location_wait_until:
            self._location_wait_until = None
            self.say("location.unavailable")
        self.send_status()
        app = self.app
        if app.sos.active:
            app.led.set_mode("fast_blink")
        elif app.watchdog.active_faults():
            app.led.set_mode("slow_blink")
        else:
            app.led.set_mode("on")


class App:
    def __init__(self, cfg: Config, options: RunOptions, clock: Clock = SYSTEM_CLOCK) -> None:
        self.cfg = cfg
        self.opt = options
        self.clock = clock
        self.stop_event = threading.Event()
        self.bus = EventBus()
        self.i18n = I18n(cfg.general.lang)
        self.watchdog = Watchdog(self.bus, clock)
        self.sim_state = SimState(forward_m=cfg.sim.forward_m, down_m=cfg.sim.down_m)
        self.sim_lidars: dict[str, SimLidar] = {}
        self.sim_imu: SimImu | None = None
        self.vision = None
        self.faces = None
        self.ocr = None
        self.reflex: ReflexWorker | None = None
        self.imu: ImuWorker | None = None
        self._pending_faults: list[tuple[str, str]] = []
        self.saved_frames: list[str] = []
        self._build()

    # ------------------------------------------------------------------------------ build
    def _build(self) -> None:
        cfg, sim, clock = self.cfg, self.opt.sim, self.clock

        backend, err = create_haptic_backend(cfg.haptics, cfg.pins, sim)
        if err:
            self._pending_faults.append(("haptics", err))
        self.haptics = HapticEngine(cfg.haptics, backend, clock)
        self.led = StatusLed(cfg.pins.status_led, sim)

        tts, err = create_tts_backend(cfg.audio, cfg.data_dir / cfg.audio.cache_dir, sim, self.opt.tts)
        if err:
            self._pending_faults.append(("audio", err))
        self.speech = SpeechOutput(cfg.audio, tts, clock, lambda: self.i18n.lang,
                                   on_spoken=self._on_spoken,
                                   on_backend_error=lambda e: self.watchdog.set_fault("audio", True, e))

        link: Link
        if sim or not self.opt.ble:
            link = NullLink(cfg.ble, clock)
        else:
            link, err = create_link(cfg.ble, clock)
            if err:
                self._pending_faults.append(("ble", err))
        self.link = link

        self.arbiter = Arbiter(cfg, clock, self.haptics, self.speech, self.link, self.i18n)
        self.sos = SosManager(cfg, clock, self.haptics, self.speech, self.link, self.i18n)
        self.controller = Controller(self)
        self.link.receiver = self.controller.on_phone
        self.link.on_connection = self.controller.on_connection
        self.link.on_error = lambda err: self.watchdog.set_fault("ble", err is not None, err or "")
        self.link.on_new_bond = self.controller.on_new_bond
        self.power_control = PowerControl(sim)
        self.power: PowerWorker | None = None
        if cfg.power.enabled:
            readers = {}
            if sim:
                readers = {
                    "bits_reader": lambda: (UNDERVOLTAGE_NOW | THROTTLED_NOW) if self.sim_state.undervoltage else 0,
                    "temp_reader": lambda: 85.0 if self.sim_state.overheat else 48.0,
                }
            self.power = PowerWorker(cfg.power, clock, self.controller.on_power_status,
                                     lambda kind: self.bus.publish(PowerWarning(ts=clock.now(), kind=kind)),
                                     **readers)

        self.buttons = ButtonInput(cfg.buttons, self.bus, clock)
        if not sim:
            err = self.buttons.attach_gpio(cfg.pins)
            if err:
                self._pending_faults.append(("buttons", err))

        # reflex path: independent of vision
        wd = cfg.watchdog
        self.watchdog.register("lidar_forward", wd.lidar_timeout_s, startup_grace_s=3.0)
        if cfg.dropoff.enabled:
            self.watchdog.register("lidar_down", wd.lidar_timeout_s, startup_grace_s=3.0)
        self.reflex = ReflexWorker(cfg.reflex, cfg.dropoff, self.bus, clock, self.watchdog.beat, self._lidar_factory)
        if cfg.imu.enabled:
            self.watchdog.register("imu", wd.imu_timeout_s, startup_grace_s=3.0)
            self.imu = ImuWorker(cfg.imu, self.bus, clock, self.watchdog.beat, self._imu_factory)

        if cfg.vision.enabled:
            from .vision.pipeline import FaceWorker, VisionWorker  # noqa: PLC0415 - heavy imports

            self.watchdog.register("camera", wd.camera_timeout_s, startup_grace_s=8.0)
            self.vision = VisionWorker(cfg, self.bus, clock, self.watchdog, sim, realtime=self.opt.realtime,
                                       max_frames=self.opt.frames, on_frame=self._on_frame,
                                       on_finished=self.stop_event.set)
            if cfg.faces.enabled:
                self.faces = FaceWorker(cfg, self.bus, clock, self.watchdog, self.vision)
        from .vision.ocr import OcrEngine  # noqa: PLC0415

        self.ocr = OcrEngine(cfg.ocr)
        if cfg.ocr.enabled and not self.ocr.available:
            log.info("OCR not installed (%s)", self.ocr.error)

        self.arbiter.subscribe(self.bus)
        self.bus.subscribe(ButtonGesture, self.controller.on_gesture)
        self.bus.subscribe(FallDetected, self.controller.on_fall)
        self.bus.subscribe(PowerWarning, self.controller.on_power_warning)
        self.watchdog.add_tick_hook(self.arbiter.tick)
        self.watchdog.add_tick_hook(self.sos.tick)
        self.watchdog.add_tick_hook(self.controller.tick)

    def _lidar_factory(self, name: str):
        if self.opt.sim:
            src = (lambda: self.sim_state.forward_m) if name == "forward" else (lambda: self.sim_state.down_m)
            lidar = SimLidar(src, self.cfg.sim.noise_m)
            self.sim_lidars[name] = lidar
            return lidar
        addr = self.cfg.i2c.tfluna_forward_addr if name == "forward" else self.cfg.i2c.tfluna_down_addr
        return TFLunaI2C(self.cfg.i2c.bus, addr)

    def _imu_factory(self):
        if self.opt.sim:
            self.sim_imu = SimImu(self.clock.now)
            return self.sim_imu
        return Mpu6050(self.cfg.i2c.bus, self.cfg.i2c.mpu6050_addr)

    def features(self) -> list[str]:
        feats = ["haptics", "lidar", "dropoff" if self.cfg.dropoff.enabled else None,
                 "imu" if self.cfg.imu.enabled else None, "vision" if self.vision else None,
                 "faces" if self.faces and not self.faces.error else None,
                 "ocr" if self.ocr and self.ocr.available else None, "sos"]
        return [f for f in feats if f]

    # ------------------------------------------------------------------------- callbacks
    def _on_spoken(self, text: str, level: Level) -> None:
        self.link.send("speech", text=text, level=int(level))

    def _on_frame(self, frame, det: Detections) -> None:
        if not self.opt.save_dir or self.opt.save_every <= 0 or self.vision is None:
            return
        n = self.vision.frames
        if n % self.opt.save_every != 0 or not det.tracks:
            return
        import cv2  # noqa: PLC0415

        from .sim.dashboard import annotate  # noqa: PLC0415

        out = Path(self.opt.save_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"frame_{n:05d}.jpg"
        cv2.imwrite(str(path), annotate(frame.copy(), det))
        self.saved_frames.append(str(path))
        log.info("saved annotated frame %s (%d tracks: %s)", path, len(det.tracks),
                 ", ".join(f"#{t.track_id} {t.label} {t.score:.2f}" for t in det.tracks[:8]))

    # ------------------------------------------------------------------------------- run
    def start(self) -> None:
        log.info("OWSH firmware %s starting (sim=%s, lang=%s)", __version__, self.opt.sim, self.i18n.lang)
        self.haptics.start()
        self.speech.start()
        for comp, err in self._pending_faults:
            self.watchdog.set_fault(comp, True, err)
        if self.opt.config_error:
            self.watchdog.set_fault("config", True, self.opt.config_error)
            self.controller.say("boot.config_invalid", Level.P1, requested=True)
        self.reflex.start()  # type: ignore[union-attr]
        if self.imu:
            self.imu.start()
        if self.vision:
            self.vision.start()
        if self.faces:
            self.faces.start()
        self.buttons.start()
        if self.power:
            self.power.start()
        self.link.start()
        self.watchdog.start(self.cfg.watchdog.check_hz)
        self._boot_announcement()

    def _boot_announcement(self) -> None:
        state_dir = self.cfg.data_dir / "state"
        marker = state_dir / "first_boot_done"
        self.haptics.play("ready")
        if not self.i18n.verified:
            self.controller.say("boot.unverified_language", Level.P3)
        self.controller.say("boot.ready", Level.P4)
        if not marker.exists():
            self.controller.say("boot.assist_notice", Level.P3)
            try:
                state_dir.mkdir(parents=True, exist_ok=True)
                marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
            except OSError as exc:
                log.warning("cannot write first-boot marker: %s", exc)

    def run(self) -> int:
        self.start()
        t_end = None if not self.opt.max_seconds else time.monotonic() + self.opt.max_seconds
        try:
            if self.opt.window:
                from .sim.dashboard import Dashboard  # noqa: PLC0415

                Dashboard(self).run(t_end)
            else:
                while not self.stop_event.is_set():
                    if t_end is not None and time.monotonic() >= t_end:
                        log.info("--max-seconds reached")
                        break
                    self.stop_event.wait(0.1)
        except KeyboardInterrupt:
            log.info("interrupted")
        finally:
            self.close()
        return 0

    def close(self) -> None:
        self.stop_event.set()
        for part in (self.watchdog, self.buttons, self.power, self.faces, self.vision, self.imu, self.reflex, self.link):
            if part is not None:
                try:
                    part.close()
                except Exception:  # noqa: BLE001
                    log.exception("closing %s failed", type(part).__name__)
        self.speech.close()
        self.haptics.close()
        self.led.close()
        if self.vision is not None:
            log.info("vision summary frames=%d fps=%.1f detections=%s", self.vision.frames, self.vision.fps,
                     dict(sorted(self.vision.det_counts.items(), key=lambda kv: -kv[1])))
        log.info("active faults at exit: %s", self.watchdog.active_faults())
