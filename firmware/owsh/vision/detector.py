"""NanoDet-Plus-m 416 object detector via ``cv2.dnn`` (spec §5.3).

Pre- and post-processing follow the official OpenCV Zoo demo exactly:
  https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_nanodet/nanodet.py
  https://github.com/opencv/opencv_zoo/blob/main/models/object_detection_nanodet/demo.py
(Apache-2.0). Summary:
  * BGR frame -> RGB -> letterbox to 416x416 (INTER_AREA resize, zero border, centred)
  * (img - mean) / std with mean = [103.53, 116.28, 123.675], std = [57.375, 57.12, 58.395]
  * ``blobFromImage`` (NCHW, no further scaling)
  * per level: anchor centres cx = x*stride + 0.5*(stride-1); box distances are a softmax over
    reg_max+1 = 8 bins projected onto [0..7], times stride; x1 = cx - l, y1 = cy - t,
    x2 = cx + r, y2 = cy + b, clipped to the input size
  * class = argmax of the per-class scores, confidence = max score; NMS (0.35 / 0.6)
  * boxes are mapped back through the letterbox ("unletterbox").

Differences from the demo, all deliberate:
  1. Output tensors are grouped by shape instead of assuming the interleaved order
     ``cls8, box8, cls16, ...``: the OpenCV 5.x graph engine returns them as
     ``cls8, cls16, cls32, box8, box16, box32``. Strides are derived from the anchor counts.
  2. ``color_order`` is configurable. The Zoo demo feeds RGB (default here); upstream NanoDet
     (RangiLyu/nanodet) feeds BGR with the same mean/std, which on OpenCV's vtest.avi gave similar
     confident detections and fewer low-confidence person boxes.
  3. NMS is class-aware (``NMSBoxesBatched`` when available) so a person standing in front of a
     bench or car is not suppressed by the larger box of another class.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger("owsh.detector")

COCO_CLASSES = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog",
    "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle",
    "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant",
    "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush",
)

MEAN = np.array([103.53, 116.28, 123.675], dtype=np.float32).reshape(1, 1, 3)
STD = np.array([57.375, 57.12, 58.395], dtype=np.float32).reshape(1, 1, 3)
REG_MAX = 7


@dataclass(frozen=True)
class Detection:
    label: str
    class_id: int
    score: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in source-frame pixels


def cv2_major() -> int:
    try:
        return int(cv2.__version__.split(".")[0])
    except ValueError:
        return 4


def load_net(model_path: str) -> "cv2.dnn.Net":
    net = cv2.dnn.readNet(model_path)
    if cv2_major() < 5:
        # OpenCV 5's new graph engine warns that targets are unsupported; defaults are CPU anyway.
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net


def letterbox(src: np.ndarray, target_size: tuple[int, int] = (416, 416)) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """OpenCV Zoo demo ``letterbox``. Returns (image, (top, left, newh, neww))."""
    img = src
    top, left, newh, neww = 0, 0, target_size[0], target_size[1]
    if img.shape[0] != img.shape[1]:
        hw_scale = img.shape[0] / img.shape[1]
        if hw_scale > 1:
            newh, neww = target_size[0], int(target_size[1] / hw_scale)
            img = cv2.resize(img, (neww, newh), interpolation=cv2.INTER_AREA)
            left = int((target_size[1] - neww) * 0.5)
            img = cv2.copyMakeBorder(img, 0, 0, left, target_size[1] - neww - left, cv2.BORDER_CONSTANT, value=0)
        else:
            newh, neww = int(target_size[0] * hw_scale), target_size[1]
            img = cv2.resize(img, (neww, newh), interpolation=cv2.INTER_AREA)
            top = int((target_size[0] - newh) * 0.5)
            img = cv2.copyMakeBorder(img, top, target_size[0] - newh - top, 0, 0, cv2.BORDER_CONSTANT, value=0)
    else:
        img = cv2.resize(img, (target_size[1], target_size[0]), interpolation=cv2.INTER_AREA)
    return img, (top, left, newh, neww)


def unletterbox(boxes: np.ndarray, original_hw: tuple[int, int], lb: tuple[int, int, int, int]) -> np.ndarray:
    """Vectorised OpenCV Zoo demo ``unletterbox`` (float output, clipped to the frame)."""
    h, w = original_hw
    top, left, newh, neww = lb
    out = boxes.astype(np.float32).copy()
    ratioh, ratiow = h / newh, w / neww
    out[:, 0] = np.clip((out[:, 0] - left) * ratiow, 0, w)
    out[:, 1] = np.clip((out[:, 1] - top) * ratioh, 0, h)
    out[:, 2] = np.clip((out[:, 2] - left) * ratiow, 0, w)
    out[:, 3] = np.clip((out[:, 3] - top) * ratioh, 0, h)
    return out


class NanoDetDetector:
    def __init__(self, model_path: str, input_size: int = 416, score_threshold: float = 0.35,
                 nms_threshold: float = 0.6, classes: list[str] | None = None, num_threads: int = 0,
                 color_order: str = "rgb") -> None:
        if num_threads > 0:
            cv2.setNumThreads(num_threads)
        self.net = load_net(model_path)
        self.size = input_size
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.allowed = set(classes) if classes else None
        self.color_order = color_order
        self.out_names = self.net.getUnconnectedOutLayersNames()
        self.project = np.arange(REG_MAX + 1, dtype=np.float32)
        self._anchor_cache: dict[int, np.ndarray] = {}

    def _anchors(self, stride: int) -> np.ndarray:
        a = self._anchor_cache.get(stride)
        if a is None:
            feat = int(math.ceil(self.size / stride))
            shift = np.arange(0, feat) * stride
            xv, yv = np.meshgrid(shift, shift)
            cx = xv.flatten() + 0.5 * (stride - 1)
            cy = yv.flatten() + 0.5 * (stride - 1)
            a = np.column_stack((cx, cy)).astype(np.float32)
            self._anchor_cache[stride] = a
        return a

    def _pre(self, bgr: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
        src = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB) if self.color_order == "rgb" else bgr  # Zoo demo: RGB
        img, lb = letterbox(src, (self.size, self.size))
        img = (img.astype(np.float32) - MEAN) / STD
        return cv2.dnn.blobFromImage(img), lb

    def _group_outputs(self, outs) -> list[tuple[int, np.ndarray, np.ndarray]]:
        cls_outs, box_outs = [], []
        for o in outs:
            o = np.asarray(o)
            if o.ndim == 3:
                o = o[0]
            if o.shape[-1] == 4 * (REG_MAX + 1):
                box_outs.append(o)
            else:
                cls_outs.append(o)
        cls_outs.sort(key=lambda a: -a.shape[0])
        box_outs.sort(key=lambda a: -a.shape[0])
        levels = []
        for c, b in zip(cls_outs, box_outs):
            n = c.shape[0]
            if b.shape[0] != n:
                raise RuntimeError("NanoDet output shapes do not match")
            stride = int(round(self.size / math.sqrt(n)))
            levels.append((stride, c, b))
        return levels

    def detect(self, bgr: np.ndarray) -> list[Detection]:
        blob, lb = self._pre(bgr)
        self.net.setInput(blob)
        outs = self.net.forward(self.out_names)
        bboxes_mlvl, scores_mlvl = [], []
        for stride, cls_score, bbox_pred in self._group_outputs(outs):
            x_exp = np.exp(bbox_pred.reshape(-1, REG_MAX + 1))
            dist = (x_exp / np.sum(x_exp, axis=1, keepdims=True)) @ self.project
            dist = dist.reshape(-1, 4) * stride
            anchors = self._anchors(stride)
            nms_pre = 1000
            if cls_score.shape[0] > nms_pre:
                topk = cls_score.max(axis=1).argsort()[::-1][:nms_pre]
                anchors, dist, cls_score = anchors[topk], dist[topk], cls_score[topk]
            x1 = np.clip(anchors[:, 0] - dist[:, 0], 0, self.size)
            y1 = np.clip(anchors[:, 1] - dist[:, 1], 0, self.size)
            x2 = np.clip(anchors[:, 0] + dist[:, 2], 0, self.size)
            y2 = np.clip(anchors[:, 1] + dist[:, 3], 0, self.size)
            bboxes_mlvl.append(np.column_stack([x1, y1, x2, y2]))
            scores_mlvl.append(cls_score)
        if not bboxes_mlvl:
            return []
        bboxes = np.concatenate(bboxes_mlvl, axis=0)
        scores = np.concatenate(scores_mlvl, axis=0)
        class_ids = np.argmax(scores, axis=1)
        conf = scores[np.arange(scores.shape[0]), class_ids]
        keep = conf >= self.score_threshold
        if self.allowed is not None:
            keep &= np.array([COCO_CLASSES[i] in self.allowed if i < len(COCO_CLASSES) else False
                              for i in class_ids], dtype=bool)
        if not np.any(keep):
            return []
        bboxes, conf, class_ids = bboxes[keep], conf[keep], class_ids[keep]
        wh = bboxes.copy()
        wh[:, 2:4] = wh[:, 2:4] - wh[:, 0:2]
        if hasattr(cv2.dnn, "NMSBoxesBatched"):
            idx = cv2.dnn.NMSBoxesBatched(wh.tolist(), conf.tolist(), class_ids.tolist(),
                                          self.score_threshold, self.nms_threshold)
        else:  # pragma: no cover - very old OpenCV
            idx = cv2.dnn.NMSBoxes(wh.tolist(), conf.tolist(), self.score_threshold, self.nms_threshold)
        idx = np.array(idx).reshape(-1).astype(int)
        if idx.size == 0:
            return []
        boxes = unletterbox(bboxes[idx], bgr.shape[:2], lb)
        dets = []
        for b, s, c in zip(boxes, conf[idx], class_ids[idx]):
            if b[2] - b[0] < 2 or b[3] - b[1] < 2:
                continue
            dets.append(Detection(COCO_CLASSES[int(c)], int(c), float(s),
                                  (float(b[0]), float(b[1]), float(b[2]), float(b[3]))))
        return dets
