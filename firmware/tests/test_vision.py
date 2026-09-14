from pathlib import Path

import numpy as np
import pytest

from owsh.config import Config
from owsh.events import Direction, TrackInfo
from owsh.i18n import I18n
from owsh.vision.describe import describe_scene
from owsh.vision.detector import NanoDetDetector, letterbox, unletterbox
from owsh.vision.ocr import has_danger_keyword, order_lines, postprocess, truncate

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "object_detection_nanodet_2022nov.onnx"
VIDEO = ROOT / "samples" / "vtest.avi"


def test_letterbox_roundtrip_16_9():
    img = np.zeros((720, 1280, 3), np.uint8)
    out, lb = letterbox(img, (416, 416))
    assert out.shape == (416, 416, 3)
    top, left, newh, neww = lb
    assert (top, left, newh, neww) == (91, 0, 234, 416)
    boxes = np.array([[0, top, 416, top + newh], [208, 208, 312, 260]], np.float32)
    back = unletterbox(boxes, (720, 1280), lb)
    assert np.allclose(back[0], [0, 0, 1280, 720], atol=1)
    assert np.allclose(back[1], [640, (208 - 91) * 720 / 234, 960, (260 - 91) * 720 / 234], atol=1)


def track(label, h, direction, tid=1):
    return TrackInfo(tid, label, 0.9, (0, 0, 1, 1), h, 0.0, direction, None, 1.0, True)


def test_describe_scene_grouping_en_ko():
    tracks = [
        track("person", 0.4, Direction.CENTER, 1),
        track("bicycle", 0.3, Direction.RIGHT, 2),
        track("person", 0.35, Direction.CENTER, 3),
        track("car", 0.05, Direction.LEFT, 4),
        track("dog", 0.2, Direction.LEFT, 5),
        track("bench", 0.1, Direction.LEFT, 6),
        track("truck", 0.01, Direction.RIGHT, 7),  # 7th object: dropped (max 5)
    ]
    assert describe_scene(tracks, I18n("en")) == "2 people ahead, bicycle on the right, dog on the left, bench on the left."
    assert describe_scene(tracks, I18n("ko")) == "앞에 사람 2명, 오른쪽에 자전거, 왼쪽에 개, 왼쪽에 벤치."
    assert describe_scene([], I18n("en")) == "Nothing detected ahead."


def test_ocr_postprocessing():
    cfg = Config().ocr
    items = [
        [[[10, 50], [100, 50], [100, 70], [10, 70]], "WET FLOOR", 0.9],
        [[[10, 10], [100, 10], [100, 30], [10, 30]], "CAUTION", 0.95],
        [[[10, 90], [100, 90], [100, 99], [10, 99]], "noise", 0.2],
    ]
    assert order_lines(items, 0.5) == ["CAUTION", "WET FLOOR"]
    res = postprocess(items, cfg)
    assert res.text == "CAUTION WET FLOOR" and res.warning
    assert has_danger_keyword("공사 중입니다", cfg.danger_keywords)
    assert not has_danger_keyword("Exit 3", cfg.danger_keywords)
    assert len(truncate("word " * 100, 200)) <= 200
    assert postprocess([], cfg) is None


@pytest.mark.skipif(not MODEL.exists(), reason="run python -m owsh.tools.download_models")
def test_nanodet_output_grouping_and_blank_frame():
    det = NanoDetDetector(str(MODEL))
    assert det.detect(np.zeros((720, 1280, 3), np.uint8)) == []


@pytest.mark.skipif(not (MODEL.exists() and VIDEO.exists()), reason="model or samples/vtest.avi missing")
def test_nanodet_finds_people_in_vtest():
    import cv2

    cap = cv2.VideoCapture(str(VIDEO))
    for _ in range(60):
        ok, frame = cap.read()
    cap.release()
    assert ok
    dets = NanoDetDetector(str(MODEL), classes=["person"]).detect(frame)
    people = [d for d in dets if d.label == "person" and d.score > 0.5]
    assert len(people) >= 3
    for d in people:
        x1, y1, x2, y2 = d.box
        assert 0 <= x1 < x2 <= frame.shape[1] and 0 <= y1 < y2 <= frame.shape[0]
        assert (y2 - y1) > (x2 - x1)  # pedestrians are taller than wide
