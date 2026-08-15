# README Design

## Goal

Create a Chinese technical README that explains how to use the dance-depth-reference-video skill safely and accurately, without triggering local depth generation or paid video generation.

## Audience

- Codex and SkillHub users who need to transfer dance or gesture motion to a character.
- Engineers who need the local preprocessing and MaybeAI payload contracts.

## Content Structure

1. Project overview and non-goals, including that grayscale conversion is not depth estimation.
2. Workflow: source motion video, depth or pose-skeleton reference, character and optional scene references, validated payload, explicitly authorized generation, and QA.
3. Depth-versus-skeleton decision table and the generic-reference A/B-test requirement.
4. Prerequisites, installation, source-asset authorization, and secret handling.
5. Quick-start commands for inspecting a video, creating a depth reference, creating a skeleton reference, and building a local MaybeAI payload.
6. Provider constraints for Seedance 2.0 Mini, Kling O3, and MiniMax H3, including motion-video duration limits and reference tokens.
7. QA checklist, common failures, repository layout, and tests.

## Accuracy Rules

- State only provider limits and defaults documented in SKILL.md and references/.
- Distinguish local payload construction from external generation.
- Do not include API tokens, working credentials, or an unverified provider endpoint.
- Explain that reference assets must be owned or authorized for transformation.

## Verification

- Add a README layout test that checks for the main sections and representative script commands.
- Run the repository's unittest suite and compile the four Python scripts.
- Commit and push the README changes on codex/add-dance-depth-reference-video.
