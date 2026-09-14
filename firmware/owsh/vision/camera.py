"""Frame sources: Picamera2 (Raspberry Pi), OpenCV camera index, or a video file.

All sources return BGR ``numpy`` frames from ``read() -> (ok, frame)``.
"""

from __future__ import annotations

import logging
import sys
import time

import cv2
import numpy as np

from ..config import VisionConfig

log = logging.getLogger("owsh.camera")


class FrameSource:
    name = "base"

    def read(self) -> tuple[bool, np.ndarray | None]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class Picamera2Source(FrameSource):
    name = "picamera2"

    def __init__(self, width: int, height: int) -> None:
        from picamera2 import Picamera2  # noqa: PLC0415 - apt python3-picamera2 on the Pi

        self._cam = Picamera2()
        # "RGB888" in libcamera/Picamera2 yields a 3-channel array in B,G,R order (OpenCV native).
        config = self._cam.create_video_configuration(main={"size": (width, height), "format": "RGB888"})
        self._cam.configure(config)
        self._cam.start()

    def read(self) -> tuple[bool, np.ndarray | None]:
        try:
            frame = self._cam.capture_array("main")
        except Exception as exc:  # noqa: BLE001
            log.warning("picamera2 capture failed: %s", exc)
            return False, None
        return True, frame

    def close(self) -> None:
        try:
            self._cam.stop()
            self._cam.close()
        except Exception:  # noqa: BLE001
            pass


class OpenCVSource(FrameSource):
    name = "opencv"

    def __init__(self, index: int, width: int, height: int) -> None:
        api = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(index, api)
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open camera index {index}")
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._cap.read()
        return (bool(ok) and frame is not None), frame

    def close(self) -> None:
        self._cap.release()


class VideoFileSource(FrameSource):
    """Video file. With ``realtime`` frames are paced at the file's FPS and late frames are
    skipped, like a live camera would; otherwise every frame is returned as fast as possible."""

    name = "video"

    def __init__(self, path: str, loop: bool = True, realtime: bool = True) -> None:
        self.path = path
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open video {path}")
        self.fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        if not (1.0 <= self.fps <= 240.0):
            self.fps = 25.0
        self.loop = loop
        self.realtime = realtime
        self.frame_index = -1  # index of the last returned frame within the file
        self._t0: float | None = None
        self._pos = 0  # next frame index to decode

    def _rewind(self) -> bool:
        if not self.loop:
            return False
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._pos = 0
        self._t0 = None
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.realtime:
            now = time.monotonic()
            if self._t0 is None:
                self._t0 = now - self._pos / self.fps
            due = int((now - self._t0) * self.fps)
            while self._pos < due:  # we are late: drop frames like a live sensor
                if not self._cap.grab():
                    if not self._rewind():
                        return False, None
                    break
                self._pos += 1
            wait = self._t0 + self._pos / self.fps - time.monotonic()
            if wait > 0:
                time.sleep(wait)
        ok, frame = self._cap.read()
        if not ok:
            if not self._rewind():
                return False, None
            ok, frame = self._cap.read()
            if not ok:
                return False, None
        self.frame_index = self._pos
        self._pos += 1
        return True, frame

    def close(self) -> None:
        self._cap.release()


def open_source(cfg: VisionConfig, sim: bool, realtime: bool = True) -> FrameSource:
    """Open the configured source. Raises on failure (the caller retries and the watchdog
    raises the camera FAULT)."""
    source = cfg.source
    if cfg.video_path and source in ("auto", "video"):
        return VideoFileSource(cfg.video_path, loop=cfg.video_loop, realtime=realtime)
    if source == "video":
        raise RuntimeError("vision.source=video but no video_path")
    if source == "picamera2" or (source == "auto" and not sim):
        try:
            return Picamera2Source(cfg.width, cfg.height)
        except Exception as exc:  # noqa: BLE001
            if source == "picamera2":
                raise
            log.warning("Picamera2 unavailable (%s), trying OpenCV camera %d", exc, cfg.camera_index)
    return OpenCVSource(cfg.camera_index, cfg.width, cfg.height)
