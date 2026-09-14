"""Face detection (YuNet 2023mar) + recognition (SFace 2021dec) + local enrolment DB (spec §5.4).

API usage follows the OpenCV Zoo wrappers (face_detection_yunet/yunet.py,
face_recognition_sface/sface.py): ``cv2.FaceDetectorYN.create(model, "", input_size,
score_threshold, nms_threshold, top_k)``, ``detect(img) -> (retval, faces Nx15)``;
``cv2.FaceRecognizerSF.create(model, "")``, ``alignCrop(img, face)``, ``feature(crop)``,
cosine similarity threshold 0.363.

Database layout: ``data/faces/<name>/*.jpg`` and ``data/faces/index.json``::

    {"Mina": {"tag": "friend"}, "Mr X": {"tag": "avoid"}}

Privacy: photos and embeddings never leave the helmet; only names are sent over BLE.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("owsh.faces")

TAGS = ("friend", "avoid")


def _factory(cls_name: str):
    cls = getattr(cv2, cls_name, None)
    if cls is not None and hasattr(cls, "create"):
        return cls.create
    legacy = getattr(cv2, f"{cls_name}_create", None)  # OpenCV 4.5.x naming
    if legacy is None:
        raise RuntimeError(f"this OpenCV build ({cv2.__version__}) has no {cls_name}")
    return legacy


def create_face_detector(model_path: str, input_size: tuple[int, int], score_threshold: float = 0.6,
                         nms_threshold: float = 0.3, top_k: int = 5000):
    return _factory("FaceDetectorYN")(model_path, "", tuple(input_size), score_threshold, nms_threshold, top_k)


def create_face_recognizer(model_path: str):
    return _factory("FaceRecognizerSF")(model_path, "")


def safe_name(name: str) -> str:
    name = name.strip()
    if not name or name in (".", "..") or re.search(r"[\\/:*?\"<>|\x00-\x1f]", name):
        raise ValueError(f"invalid person name {name!r}")
    return name


@dataclass(frozen=True)
class FaceResult:
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in frame pixels
    det_score: float
    name: str | None
    tag: str | None
    similarity: float


class FaceEngine:
    def __init__(self, detector_model: str, recognizer_model: str, detect_width: int = 640,
                 score_min: float = 0.6, nms: float = 0.3) -> None:
        self.detect_width = detect_width
        self.detector = create_face_detector(detector_model, (320, 320), score_min, nms)
        self.recognizer = create_face_recognizer(recognizer_model)
        self._size: tuple[int, int] | None = None
        self._lock = threading.Lock()

    def detect(self, bgr: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
        """Returns (faces Nx15 in the *scaled* image, scale, scaled image)."""
        h, w = bgr.shape[:2]
        scale = min(1.0, self.detect_width / float(w))
        img = bgr if scale == 1.0 else cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        size = (img.shape[1], img.shape[0])
        with self._lock:
            if size != self._size:
                self.detector.setInputSize(size)
                self._size = size
            _, faces = self.detector.detect(img)
        return (np.empty((0, 15), np.float32) if faces is None else faces), scale, img

    def feature(self, img: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        with self._lock:
            crop = self.recognizer.alignCrop(img, face_row)
            feat = self.recognizer.feature(crop)
        feat = np.asarray(feat, dtype=np.float32).reshape(-1)
        return feat / max(1e-9, float(np.linalg.norm(feat)))

    def largest_face_feature(self, bgr: np.ndarray) -> np.ndarray | None:
        faces, _, img = self.detect(bgr)
        if len(faces) == 0:
            return None
        row = max(faces, key=lambda f: f[2] * f[3])
        return self.feature(img, row)


class FaceDB:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.people: dict[str, dict] = {}
        self.features: dict[str, np.ndarray] = {}  # name -> (k, 128) normalised

    @property
    def index_path(self) -> Path:
        return self.root / "index.json"

    def load_index(self) -> dict[str, dict]:
        if not self.index_path.exists():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("face index unreadable: %s", exc)
            return {}
        out = {}
        for name, meta in (data or {}).items():
            tag = (meta or {}).get("tag", "friend")
            out[name] = {"tag": tag if tag in TAGS else "friend"}
        return out

    def save_index(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(self.people, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, engine: FaceEngine) -> int:
        self.people = self.load_index()
        self.features.clear()
        for name in self.people:
            feats = []
            for img_path in sorted((self.root / name).glob("*.jpg")):
                img = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    continue
                f = engine.largest_face_feature(img)
                if f is not None:
                    feats.append(f)
            if feats:
                self.features[name] = np.stack(feats)
            else:
                log.warning("no usable face images for %s", name)
        log.info("face DB: %d people, %d with features", len(self.people), len(self.features))
        return len(self.features)

    def match(self, feat: np.ndarray, threshold: float) -> tuple[str | None, float]:
        best_name, best = None, -1.0
        for name, feats in self.features.items():
            sim = float(np.max(feats @ feat))
            if sim > best:
                best_name, best = name, sim
        if best_name is not None and best >= threshold:
            return best_name, best
        return None, best

    def add_person(self, name: str, tag: str) -> Path:
        name = safe_name(name)
        if tag not in TAGS:
            raise ValueError("tag must be friend or avoid")
        self.people = self.load_index()
        self.people[name] = {"tag": tag}
        folder = self.root / name
        folder.mkdir(parents=True, exist_ok=True)
        self.save_index()
        return folder


class FaceRecognizer:
    """Detector + recogniser + DB. ``analyze(frame)`` returns every face with an optional match."""

    def __init__(self, engine: FaceEngine, db: FaceDB, cosine_threshold: float) -> None:
        self.engine = engine
        self.db = db
        self.threshold = cosine_threshold

    def analyze(self, bgr: np.ndarray) -> list[FaceResult]:
        faces, scale, img = self.engine.detect(bgr)
        results = []
        for row in faces:
            x, y, w, h = (float(v) / scale for v in row[:4])
            name, sim, tag = None, -1.0, None
            if self.db.features:
                feat = self.engine.feature(img, row)
                name, sim = self.db.match(feat, self.threshold)
                tag = self.db.people.get(name, {}).get("tag") if name else None
            results.append(FaceResult((x, y, x + w, y + h), float(row[14]), name, tag, sim))
        return results
