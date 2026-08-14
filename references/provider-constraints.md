# Provider Constraints

## Seedance 2.0 Mini

Use model ID `bytedance/seedance-2.0/mini/reference-to-video`.

```json
{
  "prompt": "@Image1 is the character appearance reference. @Image2 is the scene reference. @Video1 is the motion reference.",
  "image_urls": ["https://.../character.png", "https://.../scene.png"],
  "video_urls": ["https://.../depth.mp4"],
  "resolution": "720p",
  "duration": "13",
  "aspect_ratio": "1:1",
  "generate_audio": false
}
```

Supported reference inputs are HTTP(S) image and video URLs or supported data URIs. Reference videos may total 2-15 seconds, with no more than three video files and less than 50 MB combined. The output duration field accepts `auto` or integer seconds from 4 to 15. It cannot express a duration such as `13.47` exactly.

Use `@Image1` for the character, optional `@Image2` for the scene, `@Video1` for motion, and `@Audio1` for audio according to list order. Replace the motion URL with a skeleton video when testing joint-trajectory control. Do not put a local filesystem path in the API payload; upload it first. Keep the character and scene roles explicit in the prompt.

## Kling O3 Standard Reference-to-Video

Use endpoint `fal-ai/kling-video/o3/standard/reference-to-video`.

```json
{
  "prompt": "@Image1 is character appearance only. @Image2 is the scene only. @Element1 is motion only.",
  "start_image_url": "https://.../character.png",
  "image_urls": ["https://.../character.png", "https://.../scene.png"],
  "elements": [
    {"video_url": "https://.../depth.mp4"}
  ],
  "duration": "10",
  "shot_type": "customize",
  "aspect_ratio": "1:1",
  "generate_audio": false
}
```

The reference video input is hard-limited to 10.05 seconds. The API may accept the queue submission and reject the result request with `video_duration_too_long`; a successful queue response is not proof that generation will succeed. Use `@Element1` for the video element. A skeleton can replace the depth video for an A/B test, but do not include both unless the endpoint documents multi-video conditioning. Do not include empty element objects, empty image fields, or an unrelated end image.

## MiniMax H3 LoRA Reference-to-Video

Use endpoint `fal-ai/minimax_h3/reference-to-video/lora`.

```json
{
  "prompt": "@图片1 只作为角色外观参考。@图片2 只作为场景和构图参考。@视频1 只作为动作和节奏参考。",
  "duration": 10,
  "resolution": "768P",
  "enable_prompt_expansion": false,
  "enable_safety_checker": true,
  "aspect_ratio": "1:1",
  "reference_image_urls": ["https://.../character.png", "https://.../scene.png"],
  "reference_video_urls": ["https://.../depth.mp4"],
  "loras": [
    {
      "path": "https://.../adapter.safetensors",
      "scale": 1
    }
  ],
  "reference_audio_urls": []
}
```

The public schema accepts duration integers from 5 through 15, resolutions `768P`, `2K`, and `4K`, and aspect ratios `adaptive`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, and `9:16`. Reference videos are 2-15 seconds each, with combined reference video duration at most 15 seconds; all reference image, video, and audio files together are limited to 12.

The endpoint describes references as Image 1, Image 2, and Video 1. Map image 1 to the character and image 2 to the scene. The user's working call uses the localized tokens `@图片1`, `@图片2`, and `@视频1`; preserve the token convention accepted by the selected UI/API and do not mix it with Kling's `@Element1` or Seedance's `@Video1`. Use separate requests for depth-versus-skeleton A/B tests unless the endpoint explicitly supports multiple motion videos.

For strict motion transfer, use `enable_prompt_expansion: false`. Use a realism/people LoRA only when the reference image is realistic. If the reference is a flat cartoon, omit this realism LoRA or use a style-compatible adapter.

The tested call used `duration: 11`, `resolution: "768P"`, and `aspect_ratio: "adaptive"`. The returned file was `11.552` seconds, `1344x768`, `24fps`, H.264 with AAC audio. This confirms that requested duration and adaptive aspect ratio must be checked against the actual output rather than assumed. If a silent MP4 is required, remove the audio track after generation with `ffmpeg -an` and validate the resulting file.

## Duration policy

For exact temporal transfer, keep source and output duration equal. When a provider only accepts integer output durations, report the actual source duration and the nearest supported value. Never silently trim or time-stretch the motion reference.
