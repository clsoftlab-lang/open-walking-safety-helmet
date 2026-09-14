"""Button-triggered text reading with RapidOCR (optional, spec §5.5).

``pip install .[ocr]`` installs ``rapidocr_onnxruntime`` (Apache-2.0). Without it the helmet says
"Text reading is not installed". The bundled RapidOCR models read Latin/Chinese text; configure
``ocr.rec_model_path`` / ``ocr.rec_keys_path`` with a Korean recognition model for Hangul.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

from ..config import OcrConfig

log = logging.getLogger("owsh.ocr")


@dataclass(frozen=True)
class OcrResult:
    text: str
    warning: bool


def center_crop(img: np.ndarray, frac: float) -> np.ndarray:
    h, w = img.shape[:2]
    ch, cw = int(h * frac), int(w * frac)
    y0, x0 = (h - ch) // 2, (w - cw) // 2
    return img[y0:y0 + ch, x0:x0 + cw]


def order_lines(items: list[tuple[list, str, float]], min_score: float) -> list[str]:
    """RapidOCR items ``[box(4 points), text, score]`` -> texts ordered top to bottom, then left."""
    rows = []
    for box, text, score in items:
        try:
            s = float(score)
        except (TypeError, ValueError):
            s = 0.0
        if s < min_score or not str(text).strip():
            continue
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        rows.append((min(ys), min(xs), str(text).strip()))
    rows.sort(key=lambda r: (round(r[0] / 10.0), r[1]))
    return [r[2] for r in rows]


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    space = cut.rfind(" ")
    return cut[:space] if space > max_chars * 0.6 else cut


def has_danger_keyword(text: str, keywords: dict[str, list[str]]) -> bool:
    upper = text.upper()
    return any(k.upper() in upper for words in keywords.values() for k in words if k)


def postprocess(items: list, cfg: OcrConfig) -> OcrResult | None:
    lines = order_lines(items or [], cfg.min_score)
    if not lines:
        return None
    text = truncate(" ".join(lines), cfg.max_chars)
    return OcrResult(text, has_danger_keyword(text, cfg.danger_keywords))


class OcrEngine:
    def __init__(self, cfg: OcrConfig) -> None:
        self.cfg = cfg
        self._engine = None
        self._lock = threading.Lock()
        self.error: str | None = None
        self.available = False
        if not cfg.enabled:
            self.error = "disabled"
            return
        try:
            import rapidocr_onnxruntime  # noqa: PLC0415,F401

            self.available = True
        except Exception as exc:  # noqa: BLE001
            self.error = f"rapidocr_onnxruntime not installed: {exc}"

    def _ensure(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415

            kwargs = {}
            if self.cfg.det_model_path:
                kwargs["det_model_path"] = self.cfg.det_model_path
            if self.cfg.rec_model_path:
                kwargs["rec_model_path"] = self.cfg.rec_model_path
            if self.cfg.rec_keys_path:
                kwargs["rec_keys_path"] = self.cfg.rec_keys_path
            self._engine = RapidOCR(**kwargs)
        return self._engine

    def read(self, bgr: np.ndarray) -> OcrResult | None:
        if not self.available:
            raise RuntimeError(self.error or "OCR unavailable")
        crop = center_crop(bgr, self.cfg.crop_frac)
        with self._lock:
            result, _elapse = self._ensure()(crop)
        return postprocess(result or [], self.cfg)
