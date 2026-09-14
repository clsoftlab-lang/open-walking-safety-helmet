"""Buttons (spec §7.2): pure press-gesture state machine + gpiozero / keyboard front-ends.

Gestures per button:

* ``press``  - emitted on every debounced press-down (used for the immediate ``tick`` and to
  cancel an SOS countdown).
* ``short``  - released before ``short_max_s`` (0.8 s). For buttons that also have a double
  press it is emitted only after ``double_gap_s`` (0.4 s) without a second press.
* ``double`` - second short press starting < 0.4 s after the first release.
* ``long``   - emitted *while still held* once the hold reaches ``long_min_s`` (1.5 s), or
  ``sos_hold_s`` (3 s) for B3, whose long action is the SOS countdown.

Presses between 0.8 s and the long threshold are ignored (ambiguous, no action).

Chord B1 + B3 (safe shutdown): as soon as both buttons are (debounced) down, the current press
cycles of B1 and B3 are swallowed - so B3's 3 s SOS long press and B1's long press cannot fire -
and a ``shutdown`` gesture (button ``"b1+b3"``) is emitted once both have been held together for
``shutdown_hold_s`` (5 s), measured from the later of the two presses. Releasing either button
before that aborts the chord without any other action.

Debouncing: a raw level change is accepted only after it has been stable for ``debounce_s``;
the transition is time-stamped with the raw edge time. A short tap can therefore never leave
the machine in a stuck "pressed" state (which could fire a false long press / SOS).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from ..bus import EventBus
from ..clock import Clock
from ..config import ButtonsConfig, PinsConfig
from ..events import ButtonGesture

log = logging.getLogger("owsh.buttons")

BUTTONS = ("b1", "b2", "b3")
HAS_DOUBLE = {"b1": False, "b2": True, "b3": True}


class ButtonStateMachine:
    def __init__(self, name: str, cfg: ButtonsConfig, has_double: bool, long_s: float) -> None:
        self.name = name
        self.cfg = cfg
        self.has_double = has_double
        self.long_s = long_s
        self.raw = False
        self.raw_t = -1e9
        self.pressed = False
        self.press_t = 0.0
        self.long_fired = False
        self.ignoring = False  # swallow the rest of the current press cycle
        self.pending_short_release: float | None = None  # waiting to see if a double follows
        self.second_press = False

    def cancel(self) -> None:
        """Swallow the current press cycle (e.g. the press that cancelled an SOS countdown)."""
        self.ignoring = self.pressed or self.raw
        self.pending_short_release = None
        self.second_press = False

    def effective_pressed(self, t: float) -> bool:
        """Pressed state including a raw edge that is already stable but not yet polled."""
        return self.raw if t - self.raw_t >= self.cfg.debounce_s else self.pressed

    def effective_press_t(self, t: float) -> float:
        if self.raw and not self.pressed and t - self.raw_t >= self.cfg.debounce_s:
            return self.raw_t
        return self.press_t

    def on_edge(self, pressed: bool, t: float) -> list[str]:
        if pressed != self.raw:
            self.raw = pressed
            self.raw_t = t
        return self.poll(t)

    def _transition(self, pressed: bool, t: float) -> list[str]:
        out: list[str] = []
        if pressed:
            if self.pending_short_release is not None:
                if t - self.pending_short_release < self.cfg.double_gap_s:
                    self.second_press = True
                else:
                    out.append("short")
                    self.second_press = False
                self.pending_short_release = None
            else:
                self.second_press = False
            self.pressed = True
            self.press_t = t
            self.long_fired = False
            out.append("press")
            return out

        self.pressed = False
        duration = t - self.press_t
        second, self.second_press = self.second_press, False
        if self.ignoring:
            self.ignoring = False
            return out
        if self.long_fired:
            return out
        if duration < self.cfg.short_max_s:
            if second:
                out.append("double")
            elif self.has_double:
                self.pending_short_release = t
            else:
                out.append("short")
        else:
            log.info("button %s press of %.2fs ignored (between short and long)", self.name, duration)
        return out

    def poll(self, t: float, suppress_long: bool = False) -> list[str]:
        out: list[str] = []
        if self.raw != self.pressed and t - self.raw_t >= self.cfg.debounce_s:
            out += self._transition(self.raw, self.raw_t)
        if self.pending_short_release is not None and not self.pressed and not self.raw \
                and t - self.pending_short_release >= self.cfg.double_gap_s:
            self.pending_short_release = None
            out.append("short")
        if self.pressed and self.raw and not self.long_fired and not self.ignoring and not suppress_long \
                and t - self.press_t >= self.long_s:
            self.long_fired = True
            self.second_press = False
            out.append("long")
        return out


class ChordDetector:
    """Pure detector for two buttons held together (B1 + B3 -> safe shutdown)."""

    def __init__(self, hold_s: float = 5.0) -> None:
        self.hold_s = hold_s
        self.since: float | None = None
        self.fired = False

    def update(self, t: float, a_pressed: bool, b_pressed: bool, a_press_t: float, b_press_t: float) -> list[str]:
        if not (a_pressed and b_pressed):
            self.since = None
            self.fired = False
            return []
        out: list[str] = []
        if self.since is None:
            self.since = max(a_press_t, b_press_t)
            self.fired = False
            out.append("chord_start")
        if not self.fired and t - self.since >= self.hold_s - 1e-9:
            self.fired = True
            out.append("shutdown")
        return out


class ButtonInput:
    """Owns the three state machines and publishes :class:`ButtonGesture` events."""

    def __init__(self, cfg: ButtonsConfig, bus: EventBus, clock: Clock) -> None:
        self.cfg = cfg
        self.bus = bus
        self.clock = clock
        self._lock = threading.RLock()
        self.machines = {
            b: ButtonStateMachine(b, cfg, HAS_DOUBLE[b], cfg.sos_hold_s if b == "b3" else cfg.long_min_s)
            for b in BUTTONS
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._gpio: list = []
        self._swallow_injected = False
        self.chord = ChordDetector(cfg.shutdown_hold_s)

    def _emit(self, button: str, gestures: list[str], t: float) -> None:
        for g in gestures:
            if g != "press" and self.machines[button].ignoring:
                continue
            log.info("button %s %s", button, g)
            self.bus.publish(ButtonGesture(ts=t, button=button, gesture=g))

    def edge(self, button: str, pressed: bool, t: float | None = None) -> None:
        t = self.clock.now() if t is None else t
        with self._lock:
            m = self.machines[button]
            if pressed != m.raw:
                m.raw = pressed
                m.raw_t = t
        self.poll(t)

    def poll(self, t: float | None = None) -> None:
        t = self.clock.now() if t is None else t
        with self._lock:
            b1, b3 = self.machines["b1"], self.machines["b3"]
            # The chord is evaluated BEFORE the per-button timeouts so that B3's SOS long press can
            # never fire in the same step in which B1 joins it.
            chord = self.chord.update(t, b1.effective_pressed(t), b3.effective_pressed(t),
                                      b1.effective_press_t(t), b3.effective_press_t(t))
            if "chord_start" in chord:
                log.info("button chord B1+B3 started (SOS / long presses suppressed)")
                b1.cancel()
                b3.cancel()
            # While B1 and B3 are both down - even before debouncing confirms it - neither may fire
            # its long press: a genuine chord is confirmed within debounce_s, a bounce only delays it.
            both_raw = b1.raw and b3.raw
            results = [(b, m.poll(t, suppress_long=both_raw and b in ("b1", "b3")))
                       for b, m in self.machines.items()]
        for b, gestures in results:
            self._emit(b, gestures, t)
        if "shutdown" in chord:
            log.warning("button chord B1+B3 held %.1f s: shutdown", self.cfg.shutdown_hold_s)
            self.bus.publish(ButtonGesture(ts=t, button="b1+b3", gesture="shutdown"))

    def cancel_all(self) -> None:
        """Swallow the current press cycle of every button (called when a press cancels SOS)."""
        with self._lock:
            for m in self.machines.values():
                m.cancel()
            self._swallow_injected = True

    def inject(self, button: str, gesture: str) -> None:
        """Keyboard / test front-end: a complete gesture (press tick, then the gesture)."""
        t = self.clock.now()
        self._swallow_injected = False
        self._emit(button, ["press"], t)
        if self._swallow_injected:
            self._swallow_injected = False
            for m in self.machines.values():
                m.ignoring = False
            return
        self._emit(button, [gesture], t)

    def inject_shutdown_chord(self) -> None:
        """Keyboard / test front-end for the B1 + B3 shutdown chord."""
        t = self.clock.now()
        self._emit("b1", ["press"], t)
        self._emit("b3", ["press"], t)
        self.bus.publish(ButtonGesture(ts=t, button="b1+b3", gesture="shutdown"))

    # -- GPIO
    def attach_gpio(self, pins: PinsConfig) -> str | None:
        """Attach gpiozero buttons (active-low, internal pull-up). Returns an error or None."""
        try:
            from gpiozero import Button  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            return f"gpiozero unavailable: {exc}"
        try:
            for name, pin in zip(BUTTONS, (pins.button_b1, pins.button_b2, pins.button_b3)):
                btn = Button(pin, pull_up=True, bounce_time=None)
                btn.when_pressed = self._cb(name, True)
                btn.when_released = self._cb(name, False)
                self._gpio.append(btn)
            return None
        except Exception as exc:  # noqa: BLE001
            return f"GPIO buttons failed: {exc}"

    def _cb(self, name: str, pressed: bool) -> Callable[[], None]:
        return lambda: self.edge(name, pressed)

    def _run(self) -> None:
        period = 1.0 / self.cfg.poll_hz
        while not self._stop.wait(period):
            try:
                self.poll()
            except Exception:  # noqa: BLE001
                log.exception("button poll failed")

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="buttons", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        for b in self._gpio:
            try:
                b.close()
            except Exception:  # noqa: BLE001
                pass


# Keyboard map for --sim (spec §9): 1/2/3 short, Shift+1..3 or q/w/e long, a/s/d double.
KEYMAP: dict[str, tuple[str, str]] = {
    "1": ("b1", "short"), "2": ("b2", "short"), "3": ("b3", "short"),
    "!": ("b1", "long"), "@": ("b2", "long"), "#": ("b3", "long"),
    "q": ("b1", "long"), "w": ("b2", "long"), "e": ("b3", "long"),
    "a": ("b1", "double"), "s": ("b2", "double"), "d": ("b3", "double"),
}
SHUTDOWN_KEY = "z"  # simulates holding B1 + B3 for 5 s
