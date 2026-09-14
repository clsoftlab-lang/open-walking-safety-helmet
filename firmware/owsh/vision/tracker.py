"""IoU-greedy tracker, direction and time-to-contact (spec §5.3), plus the approach alert policy.

TTC = dt / (s - 1) with s = (smoothed bbox height now) / (smoothed bbox height dt ago), dt >= 0.4 s.
Derivation: bbox height h ~ 1/Z, so s = Z_then / Z_now; closing speed v = (Z_then - Z_now) / dt;
TTC = Z_now / v = dt / (s - 1). Non-approaching tracks (s <= 1) have no TTC.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

from ..config import ApproachConfig, DetectorConfig, TrackerConfig
from ..events import Direction, Level, TrackInfo
from .detector import Detection


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1e-9, area_a + area_b - inter)


def horizontal_angle_deg(cx: float, frame_w: int, hfov_deg: float) -> float:
    """Pinhole model: angle of pixel column ``cx`` from the optical axis (negative = left)."""
    f = (frame_w / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)
    return math.degrees(math.atan((cx - frame_w / 2.0) / f))


def direction_from_angle(angle_deg: float, center_deg: float = 15.0) -> Direction:
    """LEFT < -15 deg <= CENTER <= +15 deg < RIGHT."""
    if angle_deg < -center_deg:
        return Direction.LEFT
    if angle_deg > center_deg:
        return Direction.RIGHT
    return Direction.CENTER


def time_to_contact(history: list[tuple[float, float]] | deque, now: float, min_window_s: float,
                    max_window_s: float) -> float | None:
    """TTC from a (t, smoothed_height) history. Uses the newest sample that is at least
    ``min_window_s`` old and at most ``max_window_s`` old. Returns None when unknown, ``inf``
    when not approaching."""
    if not history:
        return None
    t_now, h_now = history[-1]
    ref = None
    for t, h in reversed(history):
        age = t_now - t
        if age >= min_window_s - 1e-9:
            if age <= max_window_s + 1e-9:
                ref = (t, h)
            break
    if ref is None or ref[1] <= 0:
        return None
    dt = t_now - ref[0]
    s = h_now / ref[1]
    if s <= 1.0 + 1e-6:
        return math.inf
    return dt / (s - 1.0)


@dataclass
class Track:
    track_id: int
    label: str
    score: float
    box: tuple[float, float, float, float]
    first_seen: float
    last_seen: float
    h_smooth: float
    history: deque = field(default_factory=lambda: deque(maxlen=64))
    ttc_s: float | None = None
    hits: int = 1


class IoUTracker:
    def __init__(self, cfg: TrackerConfig, hfov_deg: float, movers: list[str] | None = None) -> None:
        self.cfg = cfg
        self.hfov_deg = hfov_deg
        self.movers = set(movers or DetectorConfig().movers)
        self.tracks: dict[int, Track] = {}
        self._next_id = 1

    def update(self, detections: list[Detection], t: float, frame_w: int, frame_h: int) -> list[TrackInfo]:
        c = self.cfg
        pairs = []
        for tid, tr in self.tracks.items():
            for di, det in enumerate(detections):
                if det.label != tr.label:
                    continue
                v = iou(tr.box, det.box)
                if v >= c.iou_threshold:
                    pairs.append((v, tid, di))
        pairs.sort(reverse=True)
        used_tracks: set[int] = set()
        used_dets: set[int] = set()
        for _, tid, di in pairs:
            if tid in used_tracks or di in used_dets:
                continue
            used_tracks.add(tid)
            used_dets.add(di)
            self._update_track(self.tracks[tid], detections[di], t)
        for di, det in enumerate(detections):
            if di in used_dets:
                continue
            h = det.box[3] - det.box[1]
            tr = Track(self._next_id, det.label, det.score, det.box, t, t, h)
            tr.history.append((t, h))
            self.tracks[tr.track_id] = tr
            self._next_id += 1
        for tid in [tid for tid, tr in self.tracks.items() if t - tr.last_seen > c.max_age_s]:
            del self.tracks[tid]
        return [self.info(tr, t, frame_w, frame_h) for tr in self.tracks.values()]

    def _update_track(self, tr: Track, det: Detection, t: float) -> None:
        c = self.cfg
        h = det.box[3] - det.box[1]
        a = c.height_smoothing
        tr.h_smooth = a * h + (1.0 - a) * tr.h_smooth
        tr.box = det.box
        tr.score = det.score
        tr.last_seen = t
        tr.hits += 1
        tr.history.append((t, tr.h_smooth))
        while tr.history and t - tr.history[0][0] > c.ttc_max_window_s + 0.5:
            tr.history.popleft()
        tr.ttc_s = time_to_contact(tr.history, t, c.ttc_window_s, c.ttc_max_window_s)

    def info(self, tr: Track, t: float, frame_w: int, frame_h: int) -> TrackInfo:
        cx = (tr.box[0] + tr.box[2]) / 2.0
        angle = horizontal_angle_deg(cx, frame_w, self.hfov_deg)
        return TrackInfo(
            track_id=tr.track_id, label=tr.label, score=tr.score, box=tr.box,
            height_frac=(tr.box[3] - tr.box[1]) / max(1, frame_h), angle_deg=angle,
            direction=direction_from_angle(angle, self.cfg.center_deg),
            ttc_s=tr.ttc_s if tr.last_seen == t else None, age_s=t - tr.first_seen,
            is_mover=tr.label in self.movers, missed_s=t - tr.last_seen,
        )


class ApproachPolicy:
    """APPROACH P1 / P2 decision with per-track cooldown; escalation bypasses the cooldown."""

    def __init__(self, cfg: ApproachConfig, vehicles: list[str]) -> None:
        self.cfg = cfg
        self.vehicles = set(vehicles)
        self._last: dict[int, tuple[Level, float]] = {}
        self._streak: dict[int, int] = {}

    def level_for(self, tr: TrackInfo) -> Level | None:
        c = self.cfg
        if not tr.is_mover or tr.ttc_s is None or math.isinf(tr.ttc_s) or tr.ttc_s <= 0:
            return None
        if tr.ttc_s < c.p1_ttc_s and tr.height_frac > c.p1_min_height:
            return Level.P1
        limit = c.p2_vehicle_ttc_s if tr.label in self.vehicles else c.p2_ttc_s
        if tr.ttc_s < limit and tr.height_frac > c.p2_min_height:
            return Level.P2
        return None

    def evaluate(self, tr: TrackInfo, now: float) -> Level | None:
        level = self.level_for(tr)
        # Require the condition on `confirm_frames` consecutive updates of the track, so a single
        # jittery bbox height does not raise an alarm (false alarms train users to ignore alerts).
        streak = self._streak.get(tr.track_id, 0) + 1 if level is not None else 0
        self._streak[tr.track_id] = streak
        if level is None or streak < self.cfg.confirm_frames:
            return None
        last = self._last.get(tr.track_id)
        if last is not None:
            last_level, last_t = last
            within = now - last_t < self.cfg.cooldown_s
            if within and level >= last_level:  # same or lower importance: suppressed
                return None
        self._last[tr.track_id] = (level, now)
        return level

    def forget_older_than(self, now: float, age_s: float = 30.0) -> None:
        for tid in [k for k, (_, t) in self._last.items() if now - t > age_s]:
            del self._last[tid]
        if len(self._streak) > 500:
            self._streak = {k: v for k, v in self._streak.items() if v > 0}
