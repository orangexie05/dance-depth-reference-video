# Prompt Template

Replace the bracketed values and use the provider-specific motion token.

```text
@Image1 is the only character appearance reference. Preserve the character's [face shape], [hair], [costume], [colors], [line or rendering style], body proportions, and identity consistently throughout the video.

@Image2 is an optional scene reference only. Use it for [background], [spatial layout], [lighting], and [color palette]. Do not turn objects in the scene into additional characters, and do not use it to change the character's appearance.

@MOTION_REF is only a motion and timing reference. If it is a depth video, follow its body-weight shifts, torso orientation, front/back spatial structure, occlusion, head movement, arm and wrist paths, elbow opening, hip rhythm, footwork, action order, and beat timing. If it is a pose-skeleton video, follow its keypoint positions, joint paths, limb angles, body-weight shifts, action order, and beat timing; reconstruct natural body volume and clothing from the character reference. In both cases, do not copy the source person's identity, face, hairstyle, clothing, background, lighting, camera style, or photographic appearance.

Generate a [duration]-second [aspect ratio] video at [resolution]. Keep a [camera description] and show the full character [composition]. Follow the reference movement without adding unrelated dance steps. Keep the character's face, costume, proportions, hands, feet, and line or rendering style stable. Avoid deformation, body penetration, missing limbs, flicker, camera drift, extra people, text, logos, and watermarks.
```

Use:

- `@MOTION_REF = @Video1` for Seedance 2.0 Mini.
- `@MOTION_REF = @Element1` for Kling O3.
- `@MOTION_REF = @视频1` for the user's MiniMax H3 localized API request; use `@图片1` for the character and `@图片2` for the scene.

For a loop, describe a final pose that transitions into the opening pose. Do not force an `end_image_url` unless the supplied image is an intentional final pose. If the motion input is a depth map, say that it controls motion and spatial body structure only; it does not control appearance. If it is a pose-skeleton video, say that it controls keypoints and timing only; it does not control appearance, body design, or scene design.
