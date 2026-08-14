# Provider Routing Contract

Select `image_provider` and `video_provider` independently:

```json
{
  "image_provider": "local-doubao",
  "video_provider": "api",
  "max_in_flight": 1
}
```

Supported entries are `local-doubao`, `api`, `maybeai`, and `fal`.

`local-doubao` is a configured local/internal Doubao adapter, not a guessed endpoint or proof of offline inference. `api` is a configured remote adapter. Resolve the exact model, endpoint, auth, reference fields, and prompt tokens from the adapter contract. Do not pass depth or skeleton media through a generic video field and call it controlled motion.

Suggested configuration conventions:

| Entry | Base URL | Credential | Image | Video |
|---|---|---|---|---|
| `local-doubao` | `REMIX_DOUBAO_BASE_URL` | `REMIX_DOUBAO_API_KEY` | `REMIX_DOUBAO_IMAGE_ENDPOINT` / `REMIX_DOUBAO_IMAGE_MODEL` | `REMIX_DOUBAO_VIDEO_ENDPOINT` / `REMIX_DOUBAO_VIDEO_MODEL` |
| `api` | `REMIX_API_BASE_URL` | `REMIX_API_KEY` | `REMIX_API_IMAGE_ENDPOINT` / `REMIX_API_IMAGE_MODEL` | `REMIX_API_VIDEO_ENDPOINT` / `REMIX_API_VIDEO_MODEL` |

Use equivalent documented names when supplied by the adapter. Never write keys to skill files or logs.

Probe `image_reference`, `identity_lock`, `image_to_video`, `reference_video_to_video`, selected `motion_reference` type, `depth_control`, `skeleton_control`, `aspect_ratio_9_16`, duration, FPS, audio, and output retrieval before generation. Unknown means unsupported until proven.

Set `max_in_flight=1`. Submit one shot, wait for completion, download, inspect motion and body continuity, then continue. Never use parallel jobs, concurrent retries, or silent fallback. If motion control is unavailable, report that a prompt-only animation is a materially different result and wait for an explicit choice.
