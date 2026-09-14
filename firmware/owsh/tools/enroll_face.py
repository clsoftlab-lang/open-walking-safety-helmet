"""Enrol a person in the local face database (spec §5.4).

    python -m owsh.tools.enroll_face --name "Mina" --tag friend --camera 0 [--count 5]
    python -m owsh.tools.enroll_face --name "Mina" --tag friend --images a.jpg b.jpg
    python -m owsh.tools.enroll_face --list
    python -m owsh.tools.enroll_face --remove "Mina"

Photos go to ``data/faces/<name>/`` and the tag to ``data/faces/index.json``. Only images in
which YuNet finds a face are kept. Nothing leaves the device. Ask the person for consent.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from ..config import ConfigError, load_config
from ..vision.faces import TAGS, FaceDB, FaceEngine, safe_name


def _save_jpg(path: Path, img: np.ndarray) -> None:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    path.write_bytes(buf.tobytes())  # works with non-ASCII (e.g. Korean) paths on Windows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config")
    p.add_argument("--name")
    p.add_argument("--tag", choices=TAGS, default="friend")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--camera", type=int, help="capture from this OpenCV camera index")
    src.add_argument("--images", nargs="+", help="image files")
    p.add_argument("--count", type=int, default=5, help="photos to capture from the camera")
    p.add_argument("--list", action="store_true")
    p.add_argument("--remove", metavar="NAME")
    args = p.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    db = FaceDB(cfg.data_dir / "faces")

    if args.list:
        for name, meta in db.load_index().items():
            n = len(list((db.root / name).glob("*.jpg")))
            print(f"{name}\t{meta['tag']}\t{n} photos")
        return 0
    if args.remove:
        people = db.load_index()
        if args.remove not in people:
            print("not enrolled", file=sys.stderr)
            return 1
        del people[args.remove]
        db.people = people
        db.save_index()
        shutil.rmtree(db.root / safe_name(args.remove), ignore_errors=True)
        print(f"removed {args.remove}")
        return 0
    if not args.name or (args.camera is None and not args.images):
        p.error("--name and one of --camera / --images are required")

    f = cfg.faces
    engine = FaceEngine(str(cfg.model_path(f.detector_model)), str(cfg.model_path(f.recognizer_model)),
                        f.detect_width, f.detect_score_min, f.nms_threshold)
    folder = db.add_person(args.name, args.tag)
    stamp = time.strftime("%Y%m%d%H%M%S")
    saved = 0

    if args.images:
        for i, path in enumerate(args.images):
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None or engine.largest_face_feature(img) is None:
                print(f"skipped {path}: no face found")
                continue
            _save_jpg(folder / f"{stamp}_{i:02d}.jpg", img)
            saved += 1
    else:
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            print(f"cannot open camera {args.camera}", file=sys.stderr)
            return 1
        print("Look at the camera. Move your head slightly between photos.")
        deadline = time.monotonic() + 30 + args.count * 2
        try:
            while saved < args.count and time.monotonic() < deadline:
                ok, frame = cap.read()
                if not ok:
                    continue
                if engine.largest_face_feature(frame) is None:
                    continue
                _save_jpg(folder / f"{stamp}_{saved:02d}.jpg", frame)
                saved += 1
                print(f"photo {saved}/{args.count}")
                time.sleep(0.7)
        finally:
            cap.release()

    print(f"{args.name} ({args.tag}): {saved} photo(s) saved in {folder}")
    return 0 if saved else 1


if __name__ == "__main__":
    sys.exit(main())
