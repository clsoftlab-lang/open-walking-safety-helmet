"""Detector FPS benchmark (spec §11 T3: >= 8 FPS NanoDet 416 on a Pi 5).

    python -m owsh.tools.bench --video samples/vtest.avi [--frames 300] [--warmup 10]
    python -m owsh.tools.bench --images "frames/*.jpg"

Reports detector-only FPS and full pipeline FPS (stats + dehaze + detector + tracker).
"""

from __future__ import annotations

import argparse
import glob
import statistics
import sys
import time

import cv2

from ..config import ConfigError, load_config
from ..vision.detector import NanoDetDetector
from ..vision.preprocess import Dehazer, frame_stats
from ..vision.tracker import IoUTracker


def _frames(args):
    if args.images:
        for path in sorted(glob.glob(args.images))[: args.frames]:
            img = cv2.imread(path)
            if img is not None:
                yield img
        return
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open {args.video}")
    n = 0
    while n < args.frames:
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
            if not ok:
                break
        n += 1
        yield frame
    cap.release()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--video")
    src.add_argument("--images", help="glob pattern")
    p.add_argument("--frames", type=int, default=300)
    p.add_argument("--warmup", type=int, default=10)
    p.add_argument("--resize", default="", help="resize input to WxH first, e.g. 1280x720 (camera size)")
    args = p.parse_args(argv)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    d = cfg.vision.detector
    det = NanoDetDetector(str(cfg.model_path(d.model)), d.input_size, d.score_threshold, d.nms_threshold,
                          d.classes, d.num_threads, d.color_order)
    tracker = IoUTracker(cfg.vision.tracker, cfg.vision.hfov_deg, d.movers)
    dehazer = Dehazer(cfg.vision)
    size = tuple(int(v) for v in args.resize.lower().split("x")) if args.resize else None

    det_times, pipe_times, counts = [], [], []
    for i, frame in enumerate(_frames(args)):
        if size:
            frame = cv2.resize(frame, size)
        t0 = time.perf_counter()
        mean, std, _ = frame_stats(frame)
        img = dehazer.apply(frame, mean, std)
        t1 = time.perf_counter()
        dets = det.detect(img)
        t2 = time.perf_counter()
        tracker.update(dets, t2, frame.shape[1], frame.shape[0])
        t3 = time.perf_counter()
        if i < args.warmup:
            continue
        det_times.append(t2 - t1)
        pipe_times.append(t3 - t0)
        counts.append(len(dets))
    if not det_times:
        print("no frames measured", file=sys.stderr)
        return 1
    det_ms = statistics.mean(det_times) * 1000
    pipe_ms = statistics.mean(pipe_times) * 1000
    print(f"OpenCV {cv2.__version__}, frames measured: {len(det_times)}, input {frame.shape[1]}x{frame.shape[0]}")
    print(f"detector: {det_ms:.1f} ms/frame (p95 {sorted(det_times)[int(len(det_times) * 0.95) - 1] * 1000:.1f} ms) "
          f"= {1000 / det_ms:.1f} FPS")
    print(f"pipeline: {pipe_ms:.1f} ms/frame = {1000 / pipe_ms:.1f} FPS")
    print(f"detections per frame: mean {statistics.mean(counts):.1f}, max {max(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
