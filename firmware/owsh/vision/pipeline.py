"""Vision thread (capture -> blocked check -> dehaze -> detector -> tracker -> TTC -> alerts)
and the low-rate face thread. Nothing in the reflex path depends on these threads (P5)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np

from ..bus import EventBus
from ..clock import Clock
from ..config import Config
from ..events import ApproachAlert, Detections, FaceSeen
from ..watchdog import CameraBlockedDetector, Watchdog
from .camera import FrameSource, VideoFileSource, open_source
from .preprocess import Dehazer, frame_stats_ex
from .tracker import ApproachPolicy, IoUTracker, direction_from_angle, horizontal_angle_deg

log = logging.getLogger("owsh.vision")

FrameCallback = Callable[[np.ndarray, Detections], None]


class VisionWorker:
    RETRY_S = 2.0

    def __init__(self, cfg: Config, bus: EventBus, clock: Clock, watchdog: Watchdog, sim: bool,
                 realtime: bool = True, max_frames: int | None = None,
                 on_frame: FrameCallback | None = None, on_finished: Callable[[], None] | None = None) -> None:
        self.cfg = cfg
        self.bus = bus
        self.clock = clock
        self.watchdog = watchdog
        self.sim = sim
        self.realtime = realtime
        self.max_frames = max_frames
        self.on_frame = on_frame
        self.on_finished = on_finished
        v = cfg.vision
        self.tracker = IoUTracker(v.tracker, v.hfov_deg, v.detector.movers)
        self.policy = ApproachPolicy(v.approach, v.detector.vehicles)
        self.blocked = CameraBlockedDetector(v.blocked)
        self.dehazer = Dehazer(v)
        self.detector = None
        self.detector_error: str | None = None
        self.source: FrameSource | None = None
        self.frames = 0
        self.fps = 0.0
        self.last_stats: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._latest_frame: np.ndarray | None = None
        self._latest_det: Detections | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._next_stats = 0.0
        self.det_counts: dict[str, int] = {}

    # -- shared state for other threads
    def latest(self) -> tuple[np.ndarray | None, Detections | None]:
        with self._lock:
            return self._latest_frame, self._latest_det

    def _load_detector(self) -> None:
        d = self.cfg.vision.detector
        path = self.cfg.model_path(d.model)
        try:
            from .detector import NanoDetDetector  # noqa: PLC0415

            if not path.exists():
                raise FileNotFoundError(f"{path} missing - run python -m owsh.tools.download_models")
            self.detector = NanoDetDetector(str(path), d.input_size, d.score_threshold, d.nms_threshold,
                                            d.classes, d.num_threads, d.color_order)
            log.info("detector loaded: %s", path.name)
            self.watchdog.set_fault("detector", False)
        except Exception as exc:  # noqa: BLE001
            self.detector_error = str(exc)
            log.error("detector unavailable: %s", exc)
            self.watchdog.set_fault("detector", True, str(exc))

    def _open(self) -> bool:
        try:
            self.source = open_source(self.cfg.vision, self.sim, self.realtime)
            log.info("camera source: %s", self.source.name)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("camera open failed: %s", exc)
            self.source = None
            return False

    def process(self, frame: np.ndarray, t: float) -> Detections:
        """One frame through the pipeline (also used by the benchmark and tests)."""
        v = self.cfg.vision
        h, w = frame.shape[:2]
        if t >= self._next_stats:
            self._next_stats = t + 1.0 / v.blocked.check_hz
            mean, std, lapvar, dark_frac = frame_stats_ex(frame, v.blocked.dark_mean_max)
            self.last_stats = (mean, std, lapvar)
            change = self.blocked.update(t, mean, std, lapvar, dark_frac)
            if change is True:
                log.warning("camera blocked (%s) mean=%.1f std=%.1f lapvar=%.1f dark_frac=%.3f",
                            self.blocked.reason, mean, std, lapvar, dark_frac)
                self.watchdog.set_fault("camera_blocked", True, self.blocked.reason)
            elif change is False:
                self.watchdog.set_fault("camera_blocked", False)
        dets = []
        if self.detector is not None and not self.blocked.blocked:
            mean, std, _ = self.last_stats
            img = self.dehazer.apply(frame, mean, std)
            try:
                dets = self.detector.detect(img)
            except Exception as exc:  # noqa: BLE001
                log.exception("detector failed")
                self.watchdog.set_fault("detector", True, str(exc))
        for d in dets:
            self.det_counts[d.label] = self.det_counts.get(d.label, 0) + 1
        tracks = self.tracker.update(dets, t, w, h)
        for tr in tracks:
            level = self.policy.evaluate(tr, t)
            if level is not None:
                log.info("approach level=P%d track=%d label=%s dir=%s ttc=%.2f h=%.2f", level, tr.track_id,
                         tr.label, tr.direction.value, tr.ttc_s, tr.height_frac)
                self.bus.publish(ApproachAlert(ts=t, track_id=tr.track_id, label=tr.label, direction=tr.direction,
                                               ttc_s=float(tr.ttc_s), level=level, height_frac=tr.height_frac))
        if self.frames % 200 == 0:
            self.policy.forget_older_than(t)
        det = Detections(ts=t, frame_w=w, frame_h=h, tracks=tuple(tracks), fps=self.fps)
        self.bus.publish(det)
        return det

    def _run(self) -> None:
        self._load_detector()
        last_t = None
        while not self._stop.is_set():
            if self.source is None:
                if not self._open():
                    self._stop.wait(self.RETRY_S)
                    continue
            ok, frame = self.source.read()  # type: ignore[union-attr]
            if not ok or frame is None:
                ended = isinstance(self.source, VideoFileSource) and not self.source.loop
                self.source.close()  # type: ignore[union-attr]
                self.source = None
                if ended:
                    log.info("video ended")
                    if self.on_finished:
                        self.on_finished()
                    return
                self._stop.wait(0.5)
                continue
            t = self.clock.now()
            self.watchdog.beat("camera")
            if last_t is not None and t > last_t:
                inst = 1.0 / (t - last_t)
                self.fps = inst if self.fps == 0 else 0.9 * self.fps + 0.1 * inst
            last_t = t
            try:
                det = self.process(frame, t)
            except Exception:  # noqa: BLE001
                log.exception("vision frame failed")
                continue
            with self._lock:
                self._latest_frame = frame
                self._latest_det = det
            self.frames += 1
            if self.frames % 50 == 0:
                log.info("vision frames=%d fps=%.1f tracks=%d mean_lum=%.1f", self.frames, self.fps,
                         len(det.tracks), self.last_stats[0])
            if self.on_frame:
                try:
                    self.on_frame(frame, det)
                except Exception:  # noqa: BLE001
                    log.exception("frame callback failed")
            if self.max_frames and self.frames >= self.max_frames:
                log.info("reached --frames %d", self.max_frames)
                if self.on_finished:
                    self.on_finished()
                return

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="vision", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        if self.source is not None:
            self.source.close()


class FaceWorker:
    """Runs face recognition at <= rate_hz while persons are visible, or once on request."""

    def __init__(self, cfg: Config, bus: EventBus, clock: Clock, watchdog: Watchdog, vision: VisionWorker) -> None:
        self.cfg = cfg
        self.bus = bus
        self.clock = clock
        self.watchdog = watchdog
        self.vision = vision
        self.recognizer = None
        self.error: str | None = None
        self._requests: list[Callable[[list | None], None]] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def request(self, callback: Callable[[list | None], None]) -> None:
        """Run once on the latest frame; ``callback(results or None-if-unavailable)``."""
        with self._lock:
            self._requests.append(callback)
        self._wake.set()

    def _load(self) -> None:
        from .faces import FaceDB, FaceEngine, FaceRecognizer  # noqa: PLC0415

        f = self.cfg.faces
        try:
            det_p, rec_p = self.cfg.model_path(f.detector_model), self.cfg.model_path(f.recognizer_model)
            for p in (det_p, rec_p):
                if not p.exists():
                    raise FileNotFoundError(f"{p} missing - run python -m owsh.tools.download_models")
            engine = FaceEngine(str(det_p), str(rec_p), f.detect_width, f.detect_score_min, f.nms_threshold)
            db = FaceDB(self.cfg.data_dir / "faces")
            db.load(engine)
            self.recognizer = FaceRecognizer(engine, db, f.cosine_threshold)
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            log.error("face recognition unavailable: %s", exc)
            self.watchdog.set_fault("faces", True, str(exc))

    def _run(self) -> None:
        self._load()
        period = 1.0 / max(0.1, self.cfg.faces.rate_hz)
        while not self._stop.is_set():
            self._wake.wait(period)
            self._wake.clear()
            if self._stop.is_set():
                return
            with self._lock:
                requests, self._requests = self._requests, []
            frame, det = self.vision.latest()
            fresh = det is not None and self.clock.now() - det.ts < 1.0
            persons = fresh and any(tr.label == "person" for tr in det.tracks)  # type: ignore[union-attr]
            if not requests and not (persons and self.recognizer is not None and self.recognizer.db.features):
                continue
            results = None
            if self.recognizer is not None and frame is not None and fresh:
                try:
                    results = self.recognizer.analyze(frame)
                except Exception:  # noqa: BLE001
                    log.exception("face analysis failed")
            if results and persons:
                w = frame.shape[1]  # type: ignore[union-attr]
                for r in results:
                    if r.name is None:
                        continue
                    angle = horizontal_angle_deg((r.box[0] + r.box[2]) / 2.0, w, self.cfg.vision.hfov_deg)
                    self.bus.publish(FaceSeen(ts=det.ts, name=r.name, tag=r.tag or "friend",  # type: ignore[union-attr]
                                              direction=direction_from_angle(angle, self.cfg.vision.tracker.center_deg),
                                              score=r.similarity))
            for cb in requests:
                try:
                    cb(results if self.recognizer is not None and fresh else None)
                except Exception:  # noqa: BLE001
                    log.exception("face request callback failed")

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="faces", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
