"""``python -m owsh [--config path] [--sim] [--video file] [--no-window] ...``"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from . import __version__
from .config import Config, ConfigError, load_config


class _MonotonicFilter(logging.Filter):
    """Adds ``mono`` (time.monotonic) to every record so logs can be correlated with event
    timestamps, e.g. LiDAR sample -> motor on latency (spec §11 T2)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.mono = time.monotonic()
        return True


LOG_FORMAT = "%(asctime)s.%(msecs)03d mono=%(mono).4f %(levelname)s %(threadName)s %(name)s: %(message)s"


def setup_logging(level: str, log_file: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    flt = _MonotonicFilter()
    fmt = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S")
    for h in handlers:
        h.addFilter(flt)
        h.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    for h in handlers:
        root.addHandler(h)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m owsh", description="Open Walking Safety Helmet firmware")
    p.add_argument("--version", action="version", version=f"owsh {__version__}")
    p.add_argument("--config", help="YAML config (default: config/default.yaml)")
    p.add_argument("--sim", action="store_true", help="simulate LiDARs, IMU, motors and buttons (PC)")
    p.add_argument("--video", help="use a video file instead of the camera")
    p.add_argument("--camera", type=int, help="OpenCV camera index (overrides config)")
    p.add_argument("--no-window", action="store_true", help="headless: no dashboard window")
    p.add_argument("--max-seconds", type=float, help="exit after this many seconds")
    p.add_argument("--frames", type=int, help="exit after this many processed camera/video frames")
    p.add_argument("--lang", help="voice language (en, ko)")
    p.add_argument("--tts", choices=["auto", "piper", "espeak-ng", "pyttsx3", "print"], help="speech backend override")
    p.add_argument("--no-ble", action="store_true", help="disable the Bluetooth link")
    p.add_argument("--no-vision", action="store_true", help="disable the camera pipeline (reflex path only)")
    p.add_argument("--fast", action="store_true", help="process video frames as fast as possible (no real-time pacing)")
    p.add_argument("--save-frames", metavar="DIR", help="save annotated frames with detections to DIR")
    p.add_argument("--save-every", type=int, default=100, help="with --save-frames: every Nth frame (default 100)")
    p.add_argument("--log-level", default=None, help="DEBUG, INFO, WARNING (default from config)")
    p.add_argument("--log-file", help="also write logs to this file")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_error = None
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        # Never refuse to boot because of a settings typo: fall back to the spec defaults and
        # announce it (FAULT "config").
        config_error = str(exc)
        cfg = Config()
    setup_logging(args.log_level or cfg.general.log_level, args.log_file)
    log = logging.getLogger("owsh")
    if config_error:
        log.error("config invalid, using defaults: %s", config_error)

    if args.video:
        cfg.vision.video_path = args.video
        cfg.vision.source = "video"
        cfg.vision.enabled = True
    if args.camera is not None:
        cfg.vision.camera_index = args.camera
        if not args.video:
            cfg.vision.source = "opencv"
    if args.no_vision:
        cfg.vision.enabled = False
    if args.lang:
        cfg.general.lang = args.lang

    from .app import App, RunOptions  # noqa: PLC0415

    options = RunOptions(
        sim=args.sim, window=not args.no_window, max_seconds=args.max_seconds, frames=args.frames,
        tts=args.tts, ble=not args.no_ble, realtime=not args.fast, save_dir=args.save_frames,
        save_every=args.save_every if args.save_frames else 0, config_error=config_error,
    )
    if options.window:
        try:
            import cv2  # noqa: PLC0415

            if not hasattr(cv2, "imshow"):
                raise ImportError("OpenCV without GUI")
        except ImportError as exc:
            log.warning("no GUI available (%s), running headless", exc)
            options.window = False
    return App(cfg, options).run()


if __name__ == "__main__":
    sys.exit(main())
