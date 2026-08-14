#!/usr/bin/env python3
"""Build a MaybeAI reference-to-video payload from role-labelled media URLs."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


SEEDANCE_MODEL = "bytedance/seedance-2.0/fast/reference-to-video"
H3_MODEL = "fal-ai/minimax_h3/reference-to-video/lora"


MIME_TYPES = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".mp4": "video/mp4", ".mov": "video/quicktime",
}


def reference_url(value: str, field: str, category: str) -> str:
    if value.startswith("data:"):
        header = value.partition(",")[0].lower()
        if not header.startswith(f"data:{category}/") or ";base64" not in header:
            raise ValueError(f"{field} data URI must be a base64 {category} media value")
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be an HTTP(S) URL; upload local media before building the MaybeAI payload")
    return value


def reference_file(value: str, field: str, category: str) -> str:
    path = Path(value)
    if not path.is_file():
        raise ValueError(f"{field} file does not exist")
    mime = MIME_TYPES.get(path.suffix.lower())
    if not mime or not mime.startswith(f"{category}/"):
        raise ValueError(f"{field} file must be a supported {category} format")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_prompt(has_scene: bool, duration: str, aspect_ratio: str, action: str) -> str:
    scene_role = (
        "@Image2 controls only the scene, spatial layout, and lighting. "
        "Do not use it to alter the character. "
        if has_scene
        else "Use a clean scene described by the prompt; do not invent extra people, text, logos, or watermarks. "
    )
    return (
        "@Image1 controls only the target character appearance, body proportions, costume, and identity. "
        f"{scene_role}"
        "@Video1 is a grayscale depth video and controls only motion, body-weight shifts, torso orientation, "
        "front/back spatial relations, occlusion, limb paths, footwork, action order, and timing. "
        "Do not copy the source person's identity, face, hairstyle, clothing, background, camera style, text, logos, or audio. "
        f"{action.strip()} Generate a {duration}-second {aspect_ratio} video with a stable full-body character. "
        "Keep hands and feet intact, preserve the reference action without unrelated movement, and avoid deformation, "
        "flicker, camera drift, extra people, text, logos, and watermarks."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    character = parser.add_mutually_exclusive_group(required=True)
    character.add_argument("--character-url")
    character.add_argument("--character-file")
    motion = parser.add_mutually_exclusive_group(required=True)
    motion.add_argument("--motion-video-url")
    motion.add_argument("--motion-video-file")
    parser.add_argument("--motion-duration-seconds", type=float, help="duration of this one uploaded motion segment")
    scene = parser.add_mutually_exclusive_group()
    scene.add_argument("--scene-url")
    scene.add_argument("--scene-file")
    parser.add_argument("--model", choices=(SEEDANCE_MODEL, H3_MODEL), default=SEEDANCE_MODEL)
    parser.add_argument("--duration", default="5")
    parser.add_argument("--resolution")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--task-id")
    parser.add_argument(
        "--action",
        default="Follow the depth-reference action exactly at its supplied timing.",
    )
    parser.add_argument("--output", help="optional JSON output path; stdout is always written")
    return parser.parse_args()


def build_payload(args: argparse.Namespace) -> dict:
    character = (
        reference_url(args.character_url, "character_url", "image")
        if args.character_url else reference_file(args.character_file, "character_file", "image")
    )
    motion = (
        reference_url(args.motion_video_url, "motion_video_url", "video")
        if args.motion_video_url else reference_file(args.motion_video_file, "motion_video_file", "video")
    )
    scene = (
        reference_url(args.scene_url, "scene_url", "image") if args.scene_url
        else reference_file(args.scene_file, "scene_file", "image") if args.scene_file else None
    )
    if args.motion_duration_seconds is not None and args.motion_duration_seconds > 15:
        raise ValueError("motion video longer than 15 seconds must be segmented before building a MaybeAI reference payload")
    duration = str(args.duration).removesuffix("s")
    allowed_durations = {str(value) for value in range(5 if args.model == H3_MODEL else 4, 16)}
    if duration not in allowed_durations:
        raise ValueError(f"duration must be one of: {', '.join(sorted(allowed_durations, key=int))}")
    allowed_ratios = {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}
    if args.aspect_ratio not in allowed_ratios:
        raise ValueError(f"aspect_ratio must be one of: {', '.join(sorted(allowed_ratios))}")
    resolution = args.resolution or ("768P" if args.model == H3_MODEL else "720p")
    payload = {
        "model": args.model,
        "prompt": build_prompt(scene is not None, duration, args.aspect_ratio, args.action),
        "image_urls": [character, *([scene] if scene else [])],
        "video_urls": [motion],
        "resolution": resolution,
        "duration": duration,
        "aspect_ratio": args.aspect_ratio,
    }
    if args.task_id:
        payload["task_id"] = args.task_id
    if args.model != H3_MODEL:
        payload["generate_audio"] = False
    return payload


def main() -> None:
    try:
        args = parse_args()
        payload = build_payload(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(f"{rendered}\n")
    print(rendered)


if __name__ == "__main__":
    main()
