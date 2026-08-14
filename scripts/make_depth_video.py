#!/usr/bin/env python3
"""Create a timing-preserving grayscale depth MP4 from a local video."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def source_info(path: Path) -> dict:
    inspector = Path(__file__).with_name("inspect_video.py")
    result = subprocess.run(
        [sys.executable, str(inspector), str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def parse_device(value: str):
    if value == "cpu":
        return -1
    if value == "cuda":
        return 0
    if value == "mps":
        import torch

        return torch.device("mps")
    if value == "auto":
        import torch

        if torch.cuda.is_available():
            return 0
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return torch.device("mps")
        return -1
    fail("--device must be auto, cpu, cuda, or mps")


def normalize_depth(image, np):
    array = np.asarray(image).astype("float32")
    if array.ndim == 3:
        array = array[..., 0]
    low, high = np.percentile(array, [2, 98])
    if high <= low:
        return np.zeros(array.shape, dtype=np.uint8)
    normalized = np.clip((array - low) / (high - low), 0.0, 1.0)
    return (normalized * 255.0).astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--model-id",
        default="depth-anything/Depth-Anything-V2-Small-hf",
        help="Hugging Face depth-estimation model ID",
    )
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate source metadata without loading the depth model",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        fail(f"input video not found: {args.input}")
    if args.output.exists() and not args.force:
        fail(f"output already exists: {args.output}; use --force to overwrite")
    info = source_info(args.input)
    if info["fps"] <= 0 or info["width"] <= 0 or info["height"] <= 0:
        fail("source must have a valid video FPS and dimensions")
    if args.check_only:
        print(json.dumps({"ok": True, "source": info}, ensure_ascii=False, indent=2))
        return

    try:
        import cv2
        import numpy as np
        from PIL import Image
        import torch
        from transformers import pipeline
    except ImportError as exc:
        fail(
            "depth generation requires torch, transformers, pillow, opencv-python, and numpy; "
            f"missing import: {exc.name}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    depth_pipe = pipeline("depth-estimation", model=args.model_id, device=parse_device(args.device))
    capture = cv2.VideoCapture(str(args.input))
    if not capture.isOpened():
        fail("could not open source video")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        fail("ffmpeg is required but was not found on PATH")
    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "-s",
        f"{info['width']}x{info['height']}",
        "-r",
        f"{info['fps']:.09f}",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(args.output),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_count = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = depth_pipe(Image.fromarray(rgb))
            depth = result.get("depth")
            if depth is None:
                fail("depth model did not return a depth image")
            gray = normalize_depth(depth.resize((info["width"], info["height"])), np)
            encoder.stdin.write(gray.tobytes())
            frame_count += 1
    except BrokenPipeError:
        stderr = encoder.stderr.read().decode("utf-8", errors="replace")
        fail(stderr.strip() or "ffmpeg stopped while encoding")
    finally:
        capture.release()
        if encoder.stdin:
            encoder.stdin.close()
    stderr = encoder.stderr.read().decode("utf-8", errors="replace")
    return_code = encoder.wait()
    if return_code != 0:
        fail(stderr.strip() or "ffmpeg failed to encode depth video")
    if frame_count == 0:
        fail("source contained no decodable frames")

    output_info = source_info(args.output)
    duration_delta = abs(output_info["duration_seconds"] - info["duration_seconds"])
    frame_tolerance = 1.0 / info["fps"]
    if duration_delta > frame_tolerance:
        fail(
            f"depth video duration changed by {duration_delta:.4f}s; "
            f"allowed tolerance is {frame_tolerance:.4f}s"
        )
    print(
        json.dumps(
            {
                "ok": True,
                "model_id": args.model_id,
                "frames_processed": frame_count,
                "source": info,
                "depth_video": output_info,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
