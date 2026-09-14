"""Desktop debug dashboard for ``--sim`` (spec §9).

Shows the video with boxes / track ids / TTC, the three motor intensity bars L/C/R, simulated
LiDAR forward/down values and IMU, active faults and the last spoken line.

Keys (spec §9): ``1``/``2``/``3`` short press B1..B3, ``Shift+1..3`` or ``q``/``w``/``e`` long,
``a``/``s``/``d`` double. Extra simulator keys: ``f`` simulate a fall, ``l`` / ``k`` unplug or
replug the forward / down LiDAR, ``c`` cover / uncover the camera (black frames),
``z`` hold B1 + B3 for 5 s (safe shutdown; poweroff is only logged in simulation),
``v`` toggle Pi under-voltage, ``t`` toggle overheating (85 degC), ``Esc`` or ``x`` quit. Trackbars set the simulated forward and down distances (0 = no return).
"""

from __future__ import annotations

import dataclasses
import logging
import time
from typing import TYPE_CHECKING

import cv2
import numpy as np

from ..events import Detections
from ..input.buttons import KEYMAP, SHUTDOWN_KEY

if TYPE_CHECKING:  # pragma: no cover
    from ..app import App

log = logging.getLogger("owsh.dashboard")

WINDOW = "OWSH simulator"
PANEL_W = 340
COLORS = {"left": (255, 160, 0), "center": (0, 200, 255), "right": (255, 0, 200)}


def _put(img: np.ndarray, text: str, org: tuple[int, int], scale: float = 0.5, color=(255, 255, 255), thick: int = 1) -> None:
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def annotate(frame: np.ndarray, det: Detections | None) -> np.ndarray:
    """Draw tracks (box, id, label, score, TTC) on ``frame`` in place and return it."""
    if det is None:
        return frame
    scale = max(0.4, frame.shape[1] / 1800.0)
    for tr in det.tracks:
        if tr.missed_s > 0:
            continue  # kept alive by the tracker but not detected in this frame
        x1, y1, x2, y2 = (int(v) for v in tr.box)
        color = COLORS.get(tr.direction.value, (0, 255, 0)) if tr.is_mover else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        ttc = "" if tr.ttc_s is None or not np.isfinite(tr.ttc_s) else f" ttc={tr.ttc_s:.1f}s"
        label = f"#{tr.track_id} {tr.label} {tr.score:.2f}{ttc}"
        (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        ty = max(th + base, y1)
        cv2.rectangle(frame, (x1, ty - th - base), (x1 + tw, ty), color, -1)
        cv2.putText(frame, label, (x1, ty - base), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 1, cv2.LINE_AA)
    return frame


class Dashboard:
    def __init__(self, app: "App") -> None:
        self.app = app
        self.camera_covered = False

    def _trackbars(self) -> None:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        s = self.app.sim_state
        cv2.createTrackbar("forward cm", WINDOW, int(max(0, s.forward_m) * 100), 800, self._on_forward)
        cv2.createTrackbar("down cm", WINDOW, int(max(0, s.down_m) * 100), 800, self._on_down)

    def _on_forward(self, v: int) -> None:
        self.app.sim_state.forward_m = v / 100.0

    def _on_down(self, v: int) -> None:
        self.app.sim_state.down_m = v / 100.0

    def _bar(self, img: np.ndarray, x: int, y: int, label: str, value: float, duty: float) -> None:
        h = 120
        cv2.rectangle(img, (x, y), (x + 50, y + h), (80, 80, 80), 1)
        fill = int(h * min(1.0, value))
        cv2.rectangle(img, (x + 1, y + h - fill), (x + 49, y + h - 1), (0, 0, 255) if value > 0.8 else (0, 180, 255), -1)
        _put(img, label, (x + 18, y + h + 18))
        _put(img, f"{duty:.2f}", (x + 8, y + h + 36), 0.45)

    def render(self) -> np.ndarray:
        app = self.app
        frame, det = app.vision.latest() if app.vision else (None, None)
        if frame is None:
            view = np.zeros((480, 640, 3), np.uint8)
            _put(view, "no camera frame", (220, 240), 0.7, (0, 0, 255))
        else:
            view = frame.copy()
            if view.shape[1] > 960:
                scale = 960.0 / view.shape[1]
                view = cv2.resize(view, (960, int(view.shape[0] * scale)))
                if det is not None:
                    det = dataclasses.replace(det, tracks=tuple(
                        dataclasses.replace(tr, box=tuple(v * scale for v in tr.box)) for tr in det.tracks))
            annotate(view, det)
            if app.vision:
                _put(view, f"fps {app.vision.fps:.1f}  lum {app.vision.last_stats[0]:.0f}", (8, 20), 0.55, (0, 255, 0))
        h = max(view.shape[0], 560)
        panel = np.full((h, PANEL_W, 3), 30, np.uint8)
        y = 24
        _put(panel, "Haptics (intensity / duty)", (10, y))
        duties = app.haptics.backend.duties
        for i, lab in enumerate(("L", "C", "R")):
            self._bar(panel, 20 + i * 100, y + 10, lab, app.haptics.intensities[i], duties[i])
        y += 190
        active = ", ".join(sorted(set(app.haptics.active_names())))[:40]
        _put(panel, f"patterns: {active}", (10, y), 0.42)
        y += 26
        fwd = app.reflex.last["forward"] if app.reflex else None
        down = app.reflex.last["down"] if app.reflex else None
        zone = app.reflex.zone.zone if app.reflex else 0
        _put(panel, f"LiDAR fwd: {'no return' if fwd is None else f'{fwd:.2f} m'}  zone Z{zone}", (10, y))
        y += 22
        d0 = app.reflex.dropoff.d0 if app.reflex else 0.0
        _put(panel, f"LiDAR down: {'no return' if down is None else f'{down:.2f} m'}  d0 {d0:.2f}", (10, y))
        y += 22
        g = app.imu.last_g if app.imu else None
        if g:
            mag = float(np.sqrt(sum(v * v for v in g)))
            _put(panel, f"IMU |a| {mag:.2f} g  ({g[0]:.2f},{g[1]:.2f},{g[2]:.2f})", (10, y), 0.45)
        y += 22
        _put(panel, f"SOS: {app.sos.state}   muted: {app.speech.muted}", (10, y))
        y += 22
        sim = app.sim_state
        _put(panel, f"power: undervolt={sim.undervoltage} hot={sim.overheat}", (10, y), 0.45)
        y += 26
        faults = app.watchdog.active_faults()
        _put(panel, "FAULTS:" if faults else "faults: none", (10, y), 0.5, (0, 0, 255) if faults else (0, 255, 0))
        for f in faults[:6]:
            y += 20
            _put(panel, f"  {f}", (10, y), 0.45, (0, 0, 255))
        y += 30
        _put(panel, "Last speech:", (10, y))
        line = app.speech.last_line
        for i in range(0, min(len(line), 132), 44):
            y += 20
            _put(panel, line[i:i + 44].encode("ascii", "replace").decode(), (10, y), 0.42, (200, 255, 200))
        y = h - 50
        _put(panel, "1/2/3 short  q/w/e long  a/s/d double", (10, y), 0.42)
        _put(panel, "f fall  l/k lidar  c cam  z off  v/t power", (10, y + 20), 0.42)
        if view.shape[0] < h:
            view = cv2.copyMakeBorder(view, 0, h - view.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=0)
        return np.hstack([view, panel])

    def handle_key(self, key: int) -> bool:
        """Returns False to quit."""
        if key < 0:
            return True
        app = self.app
        ch = chr(key & 0xFF) if (key & 0xFF) < 128 else ""
        if key == 27 or ch == "x":
            return False
        if ch in KEYMAP:
            button, gesture = KEYMAP[ch]
            app.buttons.inject(button, gesture)
        elif ch == SHUTDOWN_KEY:
            app.buttons.inject_shutdown_chord()
        elif ch == "v":
            app.sim_state.undervoltage = not app.sim_state.undervoltage
            log.info("simulated under-voltage=%s", app.sim_state.undervoltage)
        elif ch == "t":
            app.sim_state.overheat = not app.sim_state.overheat
            log.info("simulated overheat=%s", app.sim_state.overheat)
        elif ch == "f" and app.sim_imu is not None:
            log.info("simulated fall")
            app.sim_imu.trigger_fall()
        elif ch in ("l", "k"):
            lidar = app.sim_lidars.get("forward" if ch == "l" else "down")
            if lidar is not None:
                lidar.fail = not lidar.fail
                log.info("simulated %s LiDAR failure=%s", "forward" if ch == "l" else "down", lidar.fail)
        elif ch == "c" and app.vision is not None:
            self.camera_covered = not self.camera_covered
            log.info("simulated camera cover=%s", self.camera_covered)
            self._cover(self.camera_covered)
        return True

    def _cover(self, on: bool) -> None:
        vision = self.app.vision
        original = vision.process
        if on:
            def covered(frame, t, _orig=original):
                return _orig(np.zeros_like(frame), t)

            vision._orig_process = original  # type: ignore[attr-defined]
            vision.process = covered  # type: ignore[method-assign]
        elif hasattr(vision, "_orig_process"):
            vision.process = vision._orig_process  # type: ignore[method-assign]
            del vision._orig_process

    def run(self, t_end: float | None = None) -> None:
        self._trackbars()
        try:
            while not self.app.stop_event.is_set():
                if t_end is not None and time.monotonic() >= t_end:
                    break
                cv2.imshow(WINDOW, self.render())
                if not self.handle_key(cv2.waitKey(30)):
                    break
                if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            cv2.destroyAllWindows()
