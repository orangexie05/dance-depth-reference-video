---
name: dance-depth-reference-video
description: Use when a user wants to reproduce dance or gesture motion in a cartoon or stylized character from a local or public video, especially with depth-map or pose-skeleton references, reference-to-video models, duration preservation, Seedance, Kling, MiniMax, or MaybeAI function-call payloads.
---

# Dance Depth Reference Video

Use this skill for the full pipeline:

```text
source dance video -> depth or pose-skeleton reference -> character image + motion reference -> generated MP4 -> QA
```

Do not treat a grayscale filter as depth. A valid depth video must be produced by a depth-estimation model and must preserve the source frame order and timing.

The two motion-reference types are complementary:

| Reference | Memory rule | Preserves best | Main tradeoff |
| --- | --- | --- | --- |
| Depth video | Depth controls space | Body volume, front/back relation, turns, occlusion, and weight shifts | It does not identify joints explicitly; fingers and wrists may be imprecise |
| Pose-skeleton video | Skeleton controls joints | Joint paths, limb angles, action order, and appearance isolation | It loses body volume, clothing motion, and some 3D occlusion |

Use this decision rule:

- If the provider has an explicit pose/keypoint control input, prefer the skeleton for precise joint choreography.
- If the provider has an explicit depth control input, prefer depth for turning, occlusion, and spatial body structure.
- If the provider only has a generic reference-video input, do not claim that either signal is guaranteed to be decoded as control data. Run a short A/B test. For this skill's stylized full-body default, use depth as the first test and skeleton as the precision fallback.
- Do not submit depth and skeleton as two motion videos unless the provider documents independent multi-video conditioning. Two unlabelled motion videos can conflict; submit separate A/B jobs otherwise.

Remember: **depth sees space, skeleton sees joints; depth keeps natural volume, skeleton keeps trajectory accuracy.**

## Provider entry selection

Choose `image_provider` and `video_provider` independently and read [references/provider-routing.md](references/provider-routing.md) before a generation call. Supported entry names are `local-doubao`, `api`, `maybeai`, and `fal`.

Treat `local-doubao` as a configured local/internal adapter, never as a guessed endpoint. Treat `api` as a configured remote adapter. Resolve the exact image/video schema and capability set before mapping character, outfit, motion, depth, or skeleton references. A generic reference-video field must not be labeled as depth or skeleton control without provider evidence.

## MaybeAI Function-Call Handoff

Use this path when `maybeai-video-function-call` is installed and the user needs a validated reference-to-video payload, not a direct provider SDK call.

| Input | MaybeAI field | Controls |
| --- | --- | --- |
| Character reference URL | `image_urls[0]` / `@Image1` | New character appearance only |
| Optional scene reference URL | `image_urls[1]` / `@Image2` | Scene, layout, and lighting only |
| Uploaded depth-video URL | `video_urls[0]` / `@Video1` | Motion, body volume, occlusion, and timing only |

`maybeai-video-function-call` accepts only HTTP(S) URLs or supported Data URIs. Never place a local path such as `/tmp/depth.mp4` in `video_urls`. Use the user's authorized media route first, or use this Skill's explicit `--character-file`, `--scene-file`, and `--motion-video-file` options to encode approved local files as Data URIs. This Skill does not upload media.

Build a Seedance reference payload and role-labelled prompt locally:

```bash
python3 scripts/build_maybeai_payload.py \
  --character-file /absolute/path/character.png \
  --scene-file /absolute/path/scene.png \
  --motion-video-file /absolute/path/depth-segment-01.mp4 \
  --motion-duration-seconds 5 \
  --duration 5 \
  --aspect-ratio 9:16 \
  --task-id "depth-segment-01" \
  --output /absolute/path/maybeai-payload.json
```

Validate and emit the native function-call envelope without generating a video:

```bash
node /absolute/path/to/maybeai-video-function-call/scripts/fal_seedance.mjs \
  call_tool /absolute/path/maybeai-payload.json --pretty
```

The payload builder only creates a documented Seedance reference payload. The MaybeAI Skill selects `maybe_text2video_generation__generate_video_from_reference_image` when it sees `image_urls` or `video_urls`. Do not call the resulting native `maybeai_function_call` until the user explicitly authorizes generation.

For a source or depth video longer than 15 seconds, create labelled motion segments before building payloads. The builder rejects a declared segment longer than 15 seconds. Track each segment's source start, source duration, requested integer model duration, and planned assembly trim explicitly. Never silently pad, loop, speed-change, or trim a final fractional segment.

Required capability checks include image reference, identity lock, image-to-video or reference-to-video, selected motion-control type, 9:16, duration, and audio. Enforce `max_in_flight=1`; submit one shot, inspect it, then continue. Do not silently substitute a prompt-only motion shot when the selected provider lacks motion control.

## Inputs and defaults

Require:

- One local dance video or a public video URL.
- One character reference image, plus an optional scene/background reference image.
- A prompt describing the character, action-reference role, camera, composition, duration, and exclusions.

Default output settings:

- `720p` generation resolution.
- `1:1` aspect ratio unless the user requests another supported ratio.
- No generated audio unless explicitly requested.
- Preserve the source video's FPS and frame count while creating the depth reference.
- Never silently crop, speed up, slow down, loop, or pad the motion reference.

When a scene image is provided, assign references explicitly: the character image controls the character, the scene image controls the environment and composition, and the depth video controls motion. Do not let the scene image become a second character. If the user requests a pure white background, call out the conflict before adding a scene reference.

Before any paid fal.ai request, show the final provider, payload settings, reference-video duration, and any duration mismatch; submit only after explicit user authorization.

## Workflow

### 1. Inspect the source

Run `scripts/inspect_video.py` on a downloaded local copy. Record duration, FPS, frame count, width, height, codec, and file size. Reject unreadable files and variable or missing FPS unless the user accepts a normalized copy.

If the source is longer than the selected provider allows, do not crop it automatically. Ask whether the user wants explicit segment generation, a different provider, or a different source.

For sources longer than 15 seconds, segment only after the user explicitly requests segmentation. Keep each segment's timing independent and label the resulting outputs in order.

### 2. Create the real depth video

Use `scripts/make_depth_video.py` with a depth-estimation model. The script emits a grayscale depth map encoded as MP4 and checks that the output duration is within one source frame of the input. It does not merely desaturate the source.

The depth video is a motion/spatial reference. It is not an explicit skeleton or keypoint track; it may be weaker for fingers and facial expression. If exact joint control is required, state that a keypoint/skeleton pipeline is a separate option instead of claiming that depth alone provides it.

If the local environment lacks the depth runtime, ask before installing `torch`, `transformers`, `pillow`, `opencv-python`, and `numpy` in an isolated Python environment. On Apple Silicon, use a PyTorch build that supports the available MPS runtime when appropriate.

### 3. Create the optional pose-skeleton video

Use `scripts/make_skeleton_video.py` when exact joint paths, action order, or appearance isolation matter. It extracts a full-body pose with MediaPipe, renders an isolated skeleton on a black background, and preserves the source FPS, frame count, dimensions, and duration. It is a pose visualization, not a 3D depth map.

```bash
python3 scripts/make_skeleton_video.py input.mp4 skeleton.mp4 --json-output skeleton.json
```

The script reports `detection_rate`. Do not use a skeleton reference without review when detection is low or when wrists, ankles, or crossed limbs are visibly mis-tracked. Install `mediapipe`, `opencv-python`, and `numpy` in the active environment when the script reports missing dependencies. If the source has camera movement, stabilize or separate the camera motion before treating the skeleton as a body-motion reference.

For the reference prompt, describe a depth input as controlling motion and spatial body structure only. Describe a skeleton input as controlling pose keypoints, joint paths, limb angles, action order, and timing only. In both cases, prohibit copying the source person's identity, face, clothing, background, lighting, and photographic style.

### 4. Select the provider

Use Seedance 2.0 Mini by default for a full reference video between 2 and 15 seconds:

- Model: `bytedance/seedance-2.0/mini/reference-to-video`.
- Image input: `image_urls`.
- Video input: `video_urls`.
- Prompt references: `@Image1` for character, optional `@Image2` for scene, and `@Video1` for motion.
- `duration` accepts integer seconds `4` through `15`, or `auto`.

Use MiniMax H3 LoRA when the user explicitly selects the H3 reference-to-video route or needs LoRA control:

- Endpoint: `fal-ai/minimax_h3/reference-to-video/lora`.
- Image input: `reference_image_urls`.
- Video input: `reference_video_urls`.
- LoRA input: `loras` with a public `.safetensors` path and scale.
- `duration` accepts integer seconds `5` through `15`.
- `resolution` accepts `768P`, `2K`, or `4K`; `aspect_ratio` accepts `adaptive`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, or `9:16`.
- Each reference video must be 2-15 seconds; combined reference video duration is limited to 15 seconds and all reference media is limited to 12 files.

For H3, map `reference_image_urls[0]` to the character and `reference_image_urls[1]` to the scene. Reference them as `@图片1` and `@图片2` in the user's localized prompt convention.

When the user requests a fixed aspect ratio, pass that ratio explicitly. Do not use `adaptive` for a requested `1:1`; the tested adaptive request returned a `16:9` file.

For strict motion replication, set `enable_prompt_expansion` to `false` unless the user explicitly wants automatic prompt expansion. Use the endpoint's documented localized reference tokens consistently. The user's working H3 request uses `@图片1` and `@视频1`; do not mix those with Seedance or Kling tokens.

Choose LoRA by appearance. A realism/people LoRA is appropriate for a realistic human or 3D-realistic character, but conflicts with a flat cartoon character and can pull the result toward realism.

Use Kling O3 only when the reference video is no longer than `10.05` seconds:

- Endpoint: `fal-ai/kling-video/o3/standard/reference-to-video`.
- Image input: `image_urls`.
- Video element: `elements[0].video_url`.
- Prompt references: `@Image1` for character, optional `@Image2` for scene, and `@Element1` for motion.
- `duration` accepts integer seconds, but it does not override the input-video limit.

If the source is `13.47` seconds, Seedance can accept the full reference video, but its integer duration field cannot express exactly `13.47` seconds. Set the closest requested integer only after telling the user that exact frame-for-frame duration equality is unavailable through that field.

### 5. Build the prompt

Read [references/prompt-template.md](references/prompt-template.md). Keep the roles explicit:

- `@Image1` controls character appearance only.
- Optional `@Image2` controls the scene/background only.
- `@Video1` or `@Element1` controls action only, depending on provider.
- Tell the model not to copy the source person's identity, face, clothing, background, lighting, or camera style.
- Specify fixed camera, full-body framing, timing, body-weight transfer, limb paths, and failure exclusions.

Use `@Image1`/`@Image2`/`@Video1` for Seedance, `@Image1`/`@Image2`/`@Element1` for Kling, and `@图片1`/`@图片2`/`@视频1` for the user's MiniMax H3 localized request. Remove empty element objects and unused `end_image_url` fields. For a loop, only provide an end image when it is an intentional matching final pose.

### 6. Submit and monitor

Use the existing `fal-seedance-video` skill and its bundled script for Seedance queue submission, status, and result retrieval. Use `FAL_AI_API_KEY`, `FAL_KEY`, or the user's configured fal key alias without printing the secret. For Kling, use the endpoint schema above and preserve the request ID.

The bundled Seedance helper recognizes `FAL_AI_API_KEY` and `FAL_KEY`. If the user's shell only exports `FAL_AI_KEY`, map it to `FAL_AI_API_KEY` in the current command environment; do not write, echo, or log the secret.

Use the payload patterns in [references/provider-constraints.md](references/provider-constraints.md). Run a dry-run or local schema validation first. If the provider returns `video_duration_too_long`, do not retry unchanged; report the exact limit and ask for a provider/source decision.

MiniMax H3 does not expose the same `generate_audio` switch as Seedance in the observed schema. If the returned H3 MP4 contains AAC audio and the user requested a silent result, remove the audio track with `ffmpeg -an` after generation and re-run output QA.

### 7. Validate the output

Use `ffprobe` or `scripts/inspect_video.py` to check the returned MP4. Report actual duration, dimensions, FPS, codec, and URL. Visually inspect representative first, middle, and last frames when available. Check:

- Stable face, costume, proportions, and line style.
- No limb twisting, hand/foot disappearance, or body penetration.
- Motion timing and weight transfer follow the reference.
- No unwanted identity, clothing, background, or lighting transfer.
- Scene composition follows the scene reference without importing extra people, text, logos, or unrelated objects.
- Loop endpoints have compatible poses if looping was requested.
- For a skeleton reference, check `detection_rate`, wrist/ankle continuity, foot contact, and crossed-limb tracking before generation.
- For a depth reference, check that the result is a model-estimated depth map rather than a desaturated copy, and verify the near/far convention with a representative frame.

## Failure handling

- A black-and-white video made by desaturation is not an acceptable depth reference.
- A depth reference over Kling's `10.05`-second limit cannot be made valid by changing output `duration`.
- An exact non-integer source duration cannot be represented by providers that accept only integer `duration` values; report the mismatch instead of hiding it.
- Provider `duration` is a target, not proof of the returned file's duration. Always inspect the returned MP4; the tested H3 request with `duration: 11` returned an `11.552`-second file.
- Do not describe an output as a frog, cartoon, or other character unless the actual reference image shows that character. In the tested H3 asset, the image was a white-robed 3D martial-arts character, so the output followed that appearance despite the prompt mentioning a green frog.
- If the depth model dependencies are missing, stop and provide the required installation or model choice. Do not silently fall back to grayscale conversion.
- A skeleton reference with missing or unstable keypoints is not a reliable motion reference; fix tracking or use the depth branch instead.
- If a provider accepts only a generic reference video, label the result as motion/style reference until an A/B test confirms that depth or skeleton conditioning is followed.
- Use only source videos and character assets that the user owns or is authorized to transform, especially for commercial publishing.

## Bundled scripts

- `scripts/inspect_video.py`: read and validate local video metadata.
- `scripts/make_depth_video.py`: estimate per-frame depth and encode a timing-preserving grayscale depth MP4.
- `scripts/make_skeleton_video.py`: extract a full-body pose and encode an isolated, timing-preserving skeleton MP4.
