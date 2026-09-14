# Models

Downloaded by `python -m owsh.tools.download_models` from the OpenCV Zoo
(https://github.com/opencv/opencv_zoo). The `.onnx` files are not committed (see `.gitignore`).
Verify your copy with `sha256sum models/*.onnx`.

| File | Purpose | Licence | Source URL | SHA-256 | Size (bytes) |
|---|---|---|---|---|---|
| `object_detection_nanodet_2022nov.onnx` | Object detector NanoDet-Plus-m 416 (COCO, 80 classes) | Apache-2.0 | https://github.com/opencv/opencv_zoo/raw/main/models/object_detection_nanodet/object_detection_nanodet_2022nov.onnx | `4b82da9944b88577175ee23a459dce2e26e6e4be573def65b1055dc2d9720186` | 3800954 |
| `face_detection_yunet_2023mar.onnx` | Face detector YuNet | MIT | https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` | 232589 |
| `face_recognition_sface_2021dec.onnx` | Face recogniser SFace | Apache-2.0 | https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` | 38696353 |

Licences: NanoDet-Plus and SFace directories of OpenCV Zoo are Apache-2.0; YuNet is MIT.
See the LICENSE file in each model directory of the OpenCV Zoo repository.
