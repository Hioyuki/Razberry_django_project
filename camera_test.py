#!/usr/bin/env python3
"""CLI camera test for Raspberry Pi.

Examples:
  python camera_test.py --once --output frame.jpg
  python camera_test.py --seconds 5 --interval 1 --out-dir captures
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raspberry Pi camera test")
    parser.add_argument(
        "--backend",
        choices=["auto", "picamera2", "cv2"],
        default="auto",
        help="Camera backend (default: auto)",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=0,
        help="Camera index for cv2 backend (default: 0)",
    )
    parser.add_argument("--once", action="store_true", help="Capture only one frame")
    parser.add_argument(
        "--seconds",
        type=int,
        default=5,
        help="Capture duration for continuous mode (default: 5)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Capture interval seconds in continuous mode (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        default="camera_test.jpg",
        help="Output file path for --once mode",
    )
    parser.add_argument(
        "--out-dir",
        default="camera_captures",
        help="Output directory for continuous mode",
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    return parser.parse_args()


def capture_once_picamera2(width: int, height: int, output_path: Path) -> None:
    from picamera2 import Picamera2  # type: ignore
    import cv2  # type: ignore

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cam = Picamera2()
    config = cam.create_preview_configuration(main={"size": (width, height)})
    cam.configure(config)
    cam.start()
    try:
        frame = cam.capture_array()
    finally:
        cam.stop()

    ok = cv2.imwrite(str(output_path), frame)
    if not ok:
        raise RuntimeError(f"Failed to write image: {output_path}")
    print(f"OK: saved {output_path.resolve()}")


def capture_continuous_picamera2(
    width: int, height: int, seconds: int, interval: float, out_dir: Path
) -> None:
    from picamera2 import Picamera2  # type: ignore
    import cv2  # type: ignore

    out_dir.mkdir(parents=True, exist_ok=True)
    cam = Picamera2()
    config = cam.create_preview_configuration(main={"size": (width, height)})
    cam.configure(config)
    cam.start()

    start = time.time()
    index = 0
    try:
        while time.time() - start < seconds:
            frame = cam.capture_array()
            ts = int(time.time() * 1000)
            path = out_dir / f"frame_{index:03d}_{ts}.jpg"
            ok = cv2.imwrite(str(path), frame)
            if not ok:
                print(f"NG: write failed {path}")
            else:
                print(f"OK: {path}")
            index += 1
            time.sleep(interval)
    finally:
        cam.stop()

    print(f"Done: captured {index} frame(s)")


def capture_once_cv2(width: int, height: int, output_path: Path, camera_index: int) -> None:
    import cv2  # type: ignore

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"cv2.VideoCapture({camera_index}) could not be opened")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    try:
        ret, frame = cap.read()
    finally:
        cap.release()

    if not ret or frame is None:
        raise RuntimeError("Failed to read frame from cv2 camera")

    ok = cv2.imwrite(str(output_path), frame)
    if not ok:
        raise RuntimeError(f"Failed to write image: {output_path}")
    print(f"OK: saved {output_path.resolve()}")


def capture_continuous_cv2(
    width: int, height: int, seconds: int, interval: float, out_dir: Path, camera_index: int
) -> None:
    import cv2  # type: ignore

    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"cv2.VideoCapture({camera_index}) could not be opened")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))

    start = time.time()
    index = 0
    try:
        while time.time() - start < seconds:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("NG: frame read failed")
                time.sleep(interval)
                continue
            ts = int(time.time() * 1000)
            path = out_dir / f"frame_{index:03d}_{ts}.jpg"
            ok = cv2.imwrite(str(path), frame)
            if not ok:
                print(f"NG: write failed {path}")
            else:
                print(f"OK: {path}")
            index += 1
            time.sleep(interval)
    finally:
        cap.release()

    print(f"Done: captured {index} frame(s)")


def run_picamera2(args: argparse.Namespace) -> None:
    if args.once:
        capture_once_picamera2(args.width, args.height, Path(args.output))
    else:
        capture_continuous_picamera2(
            args.width,
            args.height,
            args.seconds,
            args.interval,
            Path(args.out_dir),
        )


def run_cv2(args: argparse.Namespace) -> None:
    if args.once:
        capture_once_cv2(args.width, args.height, Path(args.output), args.camera_index)
    else:
        capture_continuous_cv2(
            args.width,
            args.height,
            args.seconds,
            args.interval,
            Path(args.out_dir),
            args.camera_index,
        )


def main() -> int:
    args = parse_args()
    try:
        if args.backend == "picamera2":
            run_picamera2(args)
        elif args.backend == "cv2":
            run_cv2(args)
        else:
            try:
                run_picamera2(args)
            except Exception as exc:
                print(f"picamera2 backend unavailable, fallback to cv2: {exc}")
                run_cv2(args)
        return 0
    except ModuleNotFoundError as exc:
        print(f"Import error: {exc}")
        print("Run: pip install opencv-python")
        return 1
    except Exception as exc:
        print(f"Camera test failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
