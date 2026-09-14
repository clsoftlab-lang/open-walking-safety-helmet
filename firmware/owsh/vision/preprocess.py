"""Image pre-processing: frame statistics for the blocked-camera watchdog and CLAHE dehaze
(spec §5.3 pre-filter, §5.7)."""

from __future__ import annotations

import cv2
import numpy as np

from ..config import VisionConfig

STATS_WIDTH = 640  # statistics are computed on a 640 px wide grey image (cheap on a Pi)


def to_gray_small(bgr: np.ndarray, width: int = STATS_WIDTH) -> np.ndarray:
    gray = bgr if bgr.ndim == 2 else cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if w > width:
        gray = cv2.resize(gray, (width, max(1, int(h * width / w))), interpolation=cv2.INTER_AREA)
    return gray


def frame_stats(bgr: np.ndarray) -> tuple[float, float, float]:
    """(mean luminance, luminance std-dev, Laplacian variance) on a 0..255 scale."""
    mean, std, lapvar, _ = frame_stats_ex(bgr)
    return mean, std, lapvar


def frame_stats_ex(bgr: np.ndarray, dark_level: float = 12.0) -> tuple[float, float, float, float]:
    """Like :func:`frame_stats` plus the fraction of pixels darker than ``dark_level``."""
    gray = to_gray_small(bgr)
    mean, std = cv2.meanStdDev(gray)
    lapvar = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    dark_frac = float(np.count_nonzero(gray < dark_level)) / float(gray.size)
    return float(mean.ravel()[0]), float(std.ravel()[0]), lapvar, dark_frac


class Dehazer:
    """CLAHE on the L channel of LAB. ``auto`` applies it for dark or low-contrast frames."""

    def __init__(self, cfg: VisionConfig) -> None:
        self.cfg = cfg
        self._clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip, tileGridSize=(cfg.clahe_grid, cfg.clahe_grid))
        self.active = False

    def should_apply(self, mean: float, std: float) -> bool:
        mode = self.cfg.dehaze
        if mode == "on":
            return True
        if mode == "off":
            return False
        return mean < self.cfg.dehaze_auto_mean_below or std < self.cfg.dehaze_auto_std_below

    def apply(self, bgr: np.ndarray, mean: float, std: float) -> np.ndarray:
        self.active = self.should_apply(mean, std)
        if not self.active:
            return bgr
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_ch = self._clahe.apply(l_ch)
        return cv2.cvtColor(cv2.merge((l_ch, a_ch, b_ch)), cv2.COLOR_LAB2BGR)
