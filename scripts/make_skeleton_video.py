#!/usr/bin/env python3
"""Extract a timing-preserving full-body pose skeleton MP4 from a local video."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


POSE_CONNECTIONS = [
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (11, 23),
    (12, 24),
    (23, 24),
    (23, 25),
    (25, 27),
    (27, 29),
    (29, 31),
    (24, 26),
    (26, 28),
    (28, 30),
    (30, 32),
]


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def source_info(path: Path) -> dict:
    inspector = Path(__file__).with_name("inspect_video.py")
    try:
        result = subprocess.run(
            [sys.executable, str(inspector), str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        fail(exc.stderr.strip() or "could not inspect source video")
    return json.loads(result.stdout)


def visible(landmarks, index: int, threshold: float) -> bool:
    return landmarks[index].visibility >= threshold


def pixel(landmark, width: int, height: int) -> tuple[int, int]:
    x = min(max(int(landmark.x * width), 0), width - 1)
    y = min(max(int(landmark.y * height), 0), height - 1)
    return x, y


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--visibility", type=float, default=0.35)
    parser.add_argument("--line-width", type=int, default=0, help="0 derives width from video size")
    parser.add_argument("--point-radius", type=int, default=0, help="0 derives radius from video size")
    parser.add_argument("--background", choices=["black", "white"], default="black")
    parser.add_argument("--check-only", action="store_true", help="validate source metadata without loading MediaPipe")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        fail(f"input video not found: {args.input}")
    if args.output.exists() and not args.force:
        fail(f"output already exists: {args.output}; use --force to overwrite")
    if not 0.0 <= args.visibility <= 1.0:
        fail("--visibility must be between 0 and 1")

    info = source_info(args.input)
    if info["fps"] <= 0 or info["width"] <= 0 or info["height"] <= 0:
        fail("source must have a valid video FPS and dimensions")
    if args.check_only:
        print(json.dumps({"ok": True, "source": info}, ensure_ascii=False, indent=2))
        return

    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError as exc:
        fail(f"skeleton generation requires mediapipe, opencv-python, and numpy; missing import: {exc.name}")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        fail("ffmpeg is required but was not found on PATH")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    width = info["width"]
    height = info["height"]
    line_width = args.line_width or max(3, round(min(width, height) / 120))
    point_radius = args.point_radius or max(5, line_width * 2)
    background_value = 0 if args.background == "black" else 255
    foreground = (255, 255, 255) if background_value == 0 else (0, 0, 0)

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{width}x{height}",
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

    capture = cv2.VideoCapture(str(args.input))
    if not capture.isOpened():
        fail("could not open source video")
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    frame_count = 0
    detected_frames = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            canvas = np.full((height, width, 3), background_value, dtype=np.uint8)
            result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.pose_landmarks:
                landmarks = result.pose_landmarks.landmark
                detected_frames += 1
                for start, end in POSE_CONNECTIONS:
                    if not visible(landmarks, start, args.visibility) or not visible(landmarks, end, args.visibility):
                        continue
                    cv2.line(
                        canvas,
                        pixel(landmarks[start], width, height),
                        pixel(landmarks[end], width, height),
                        foreground,
                        line_width,
                        cv2.LINE_AA,
                    )
                for index in {11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32}:
                    if visible(landmarks, index, args.visibility):
                        cv2.circle(canvas, pixel(landmarks[index], width, height), point_radius, foreground, -1, cv2.LINE_AA)
            try:
                encoder.stdin.write(canvas.tobytes())
            except BrokenPipeError:
                error = encoder.stderr.read().decode("utf-8", errors="replace")
                fail(error.strip() or "ffmpeg stopped while encoding")
            frame_count += 1
    finally:
        pose.close()
        capture.release()
        if encoder.stdin:
            encoder.stdin.close()

    error = encoder.stderr.read().decode("utf-8", errors="replace")
    return_code = encoder.wait()
    if return_code != 0:
        fail(error.strip() or "ffmpeg failed to encode skeleton video")
    if frame_count == 0:
        fail("source contained no decodable frames")

    output_info = source_info(args.output)
    duration_delta = abs(output_info["duration_seconds"] - info["duration_seconds"])
    frame_tolerance = 1.0 / info["fps"]
    if duration_delta > frame_tolerance:
        fail(
            f"skeleton video duration changed by {duration_delta:.4f}s; "
            f"allowed tolerance is {frame_tolerance:.4f}s"
        )
    if info.get("frame_count") and output_info.get("frame_count"):
        if abs(output_info["frame_count"] - info["frame_count"]) > 1:
            fail(
                f"skeleton video frame count changed from {info['frame_count']} "
                f"to {output_info['frame_count']}"
            )

    report = {
        "ok": True,
        "frames_processed": frame_count,
        "detected_frames": detected_frames,
        "detection_rate": round(detected_frames / frame_count, 4),
        "visibility_threshold": args.visibility,
        "source": info,
        "skeleton_video": output_info,
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
