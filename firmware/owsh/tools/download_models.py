"""Download the OpenCV Zoo ONNX models used by OWSH into ``firmware/models/``.

Usage::

    python -m owsh.tools.download_models [--dest models] [--force]

For every model the GitHub raw URL is tried first and a Hugging Face mirror second.
A download is only accepted when it is a real ONNX file: larger than 100 KB and not a
Git LFS pointer text file. After download the SHA-256 of every file is written to
``models/MODELS.md`` together with its source URL and licence.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("owsh.tools.download_models")

FIRMWARE_ROOT = Path(__file__).resolve().parents[2]
MIN_SIZE_BYTES = 100 * 1024
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec"


@dataclass(frozen=True)
class ModelSpec:
    directory: str
    filename: str
    licence: str
    purpose: str

    @property
    def urls(self) -> list[str]:
        return [
            f"https://github.com/opencv/opencv_zoo/raw/main/models/{self.directory}/{self.filename}",
            f"https://huggingface.co/opencv/{self.directory}/resolve/main/{self.filename}",
        ]


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("object_detection_nanodet", "object_detection_nanodet_2022nov.onnx",
              "Apache-2.0", "Object detector NanoDet-Plus-m 416 (COCO, 80 classes)"),
    ModelSpec("face_detection_yunet", "face_detection_yunet_2023mar.onnx",
              "MIT", "Face detector YuNet"),
    ModelSpec("face_recognition_sface", "face_recognition_sface_2021dec.onnx",
              "Apache-2.0", "Face recogniser SFace"),
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def looks_like_onnx(path: Path) -> tuple[bool, str]:
    """Return (ok, reason). Rejects tiny files, Git LFS pointers and HTML error pages."""
    size = path.stat().st_size
    with path.open("rb") as f:
        head = f.read(256)
    if head.startswith(LFS_POINTER_PREFIX):
        return False, "Git LFS pointer file, not the model"
    if head.lstrip().lower().startswith((b"<!doctype", b"<html")):
        return False, "HTML page, not the model"
    if size <= MIN_SIZE_BYTES:
        return False, f"file too small ({size} bytes)"
    # An ONNX ModelProto is a protobuf; field 1 (ir_version, varint) is encoded as 0x08.
    if head[:1] != b"\x08":
        return False, "does not start like an ONNX protobuf"
    return True, "ok"


def _fetch(url: str, dest: Path, timeout: float = 60.0) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "owsh-download-models/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)


def download_model(spec: ModelSpec, dest_dir: Path, force: bool = False) -> tuple[Path, str] | None:
    """Download one model. Returns (path, source_url) or None on failure."""
    target = dest_dir / spec.filename
    if target.exists() and not force:
        ok, reason = looks_like_onnx(target)
        if ok:
            log.info("present: %s (%d bytes)", target.name, target.stat().st_size)
            return target, "(already present)"
        log.warning("existing %s is invalid (%s); re-downloading", target.name, reason)

    for url in spec.urls:
        for attempt in (1, 2):
            fd, tmp_name = tempfile.mkstemp(prefix=spec.filename + ".", suffix=".part", dir=dest_dir)
            os.close(fd)  # Windows: an open handle blocks replace()/unlink()
            tmp = Path(tmp_name)
            try:
                log.info("downloading %s (attempt %d) from %s", spec.filename, attempt, url)
                _fetch(url, tmp)
                ok, reason = looks_like_onnx(tmp)
                if not ok:
                    log.warning("rejected %s: %s", url, reason)
                    break  # retrying the same URL will not help
                tmp.replace(target)
                log.info("saved %s (%d bytes)", target, target.stat().st_size)
                return target, url
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                log.warning("failed %s: %s", url, exc)
                time.sleep(1.0)
            finally:
                if tmp.exists():
                    tmp.unlink()
    log.error("could not download %s from any source", spec.filename)
    return None


def write_manifest(dest_dir: Path, results: dict[str, tuple[Path, str]]) -> Path:
    manifest = dest_dir / "MODELS.md"
    previous_sources: dict[str, str] = {}
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 5 and parts[0].endswith(".onnx"):
                previous_sources[parts[0].strip("`")] = parts[3]
    lines = [
        "# Models",
        "",
        "Downloaded by `python -m owsh.tools.download_models` from the OpenCV Zoo",
        "(https://github.com/opencv/opencv_zoo). The `.onnx` files are not committed (see `.gitignore`).",
        "Verify your copy with `sha256sum models/*.onnx`.",
        "",
        "| File | Purpose | Licence | Source URL | SHA-256 | Size (bytes) |",
        "|---|---|---|---|---|---|",
    ]
    for spec in MODELS:
        path = dest_dir / spec.filename
        if not path.exists():
            lines.append(f"| `{spec.filename}` | {spec.purpose} | {spec.licence} | (missing) | - | - |")
            continue
        src = results.get(spec.filename, (path, ""))[1]
        if not src or src.startswith("("):
            src = previous_sources.get(spec.filename, spec.urls[0])
        lines.append(f"| `{spec.filename}` | {spec.purpose} | {spec.licence} | {src} | "
                     f"`{sha256_of(path)}` | {path.stat().st_size} |")
    lines += [
        "",
        "Licences: NanoDet-Plus and SFace directories of OpenCV Zoo are Apache-2.0; YuNet is MIT.",
        "See the LICENSE file in each model directory of the OpenCV Zoo repository.",
        "",
    ]
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return manifest


def verify_loads(dest_dir: Path) -> bool:
    """Try loading each model with OpenCV. Returns True if all load."""
    try:
        import cv2  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - OpenCV missing
        log.error("OpenCV not importable, cannot verify models: %s", exc)
        return False
    from owsh.vision.detector import load_net  # noqa: PLC0415
    from owsh.vision.faces import create_face_detector, create_face_recognizer  # noqa: PLC0415

    ok = True
    checks = (
        ("object_detection_nanodet_2022nov.onnx", lambda p: load_net(p)),
        ("face_detection_yunet_2023mar.onnx", lambda p: create_face_detector(p, (320, 320))),
        ("face_recognition_sface_2021dec.onnx", lambda p: create_face_recognizer(p)),
    )
    for name, loader in checks:
        path = dest_dir / name
        if not path.exists():
            ok = False
            continue
        try:
            loader(str(path))
            log.info("cv2 %s loads %s: OK", cv2.__version__, name)
        except Exception as exc:
            ok = False
            log.error("cv2 %s failed to load %s: %s", cv2.__version__, name, exc)
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", default=str(FIRMWARE_ROOT / "models"), help="destination directory")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    parser.add_argument("--no-verify", action="store_true", help="skip loading the models with OpenCV")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    results: dict[str, tuple[Path, str]] = {}
    failed = []
    for spec in MODELS:
        res = download_model(spec, dest, force=args.force)
        if res is None:
            failed.append(spec.filename)
        else:
            results[spec.filename] = res
    manifest = write_manifest(dest, results)
    log.info("wrote %s", manifest)
    for spec in MODELS:
        p = dest / spec.filename
        if p.exists():
            print(f"{spec.filename}  sha256={sha256_of(p)}  size={p.stat().st_size}")
    if not args.no_verify and not failed:
        if not verify_loads(dest):
            return 2
    if failed:
        print("FAILED: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
