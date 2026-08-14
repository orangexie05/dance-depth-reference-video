#!/usr/bin/env python3
"""Inspect and validate local video metadata using ffprobe."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def probe(path: Path) -> dict:
    if not path.is_file():
        fail(f"video not found: {path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames:format=duration,size",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        fail("ffprobe is required but was not found on PATH")
    except subprocess.CalledProcessError as exc:
        fail(exc.stderr.strip() or "ffprobe could not read the video")
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError:
        fail("ffprobe returned invalid JSON")

    streams = [stream for stream in raw.get("streams", []) if stream.get("codec_type") == "video"]
    if not streams:
        fail("no video stream found")
    stream = streams[0]
    rate = stream.get("r_frame_rate", "")
    try:
        fps = float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    format_data = raw.get("format", {})
    duration = float(format_data.get("duration", 0.0) or 0.0)
    size = int(format_data.get("size", path.stat().st_size) or path.stat().st_size)
    frames = stream.get("nb_frames")
    frame_count = int(frames) if frames and str(frames).isdigit() else None
    return {
        "path": str(path.resolve()),
        "duration_seconds": duration,
        "fps": fps,
        "frame_count": frame_count,
        "width": int(stream.get("width", 0) or 0),
        "height": int(stream.get("height", 0) or 0),
        "codec": stream.get("codec_name"),
        "size_bytes": size,
        "has_audio": any(s.get("codec_type") == "audio" for s in raw.get("streams", [])),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--min-duration", type=float, default=None)
    parser.add_argument("--max-duration", type=float, default=None)
    parser.add_argument("--max-bytes", type=int, default=None)
    args = parser.parse_args()

    info = probe(args.video)
    if args.min_duration is not None and info["duration_seconds"] < args.min_duration:
        fail(f"duration {info['duration_seconds']:.3f}s is below {args.min_duration:.3f}s")
    if args.max_duration is not None and info["duration_seconds"] > args.max_duration:
        fail(f"duration {info['duration_seconds']:.3f}s exceeds {args.max_duration:.3f}s")
    if args.max_bytes is not None and info["size_bytes"] > args.max_bytes:
        fail(f"file size {info['size_bytes']} exceeds {args.max_bytes} bytes")
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
