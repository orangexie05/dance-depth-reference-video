# README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an accurate Chinese README that makes the dance-depth-reference-video skill usable from a fresh clone without exposing credentials or implying unauthorized generation.

**Architecture:** Keep the README as the public entry point at the repository root. It will link to existing scripts and references rather than duplicate provider schemas, while a focused unittest confirms the important sections and commands remain discoverable.

**Tech Stack:** Markdown, Python unittest, existing Python CLI scripts.

---

### Task 1: Define README completion criteria

**Files:**
- Modify: `tests/test_skill_layout.py`

- [ ] **Step 1: Write the failing test**

```python
def test_readme_documents_workflow_safety_and_local_commands(self):
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for heading in (
        "# Dance Depth Reference Video",
        "## Quick Start",
        "## Depth or Skeleton?",
        "## Provider Constraints",
        "## QA Checklist",
        "## Safety and Rights",
    ):
        self.assertIn(heading, readme)
    for command in (
        "python3 scripts/inspect_video.py",
        "python3 scripts/make_depth_video.py",
        "python3 scripts/make_skeleton_video.py",
        "python3 scripts/build_maybeai_payload.py",
    ):
        self.assertIn(command, readme)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_skill_layout.DanceDepthReferenceVideoLayoutTest.test_readme_documents_workflow_safety_and_local_commands -v`

Expected: FAIL because `README.md` does not exist.

### Task 2: Write the public README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Add the concise Chinese README**

Include these sections, using only documented facts:

```markdown
# Dance Depth Reference Video

源动作视频 -> 深度或骨架参考 -> 角色与场景参考 -> 已验证的 payload -> 经授权的生成 -> QA

## Quick Start
## Depth or Skeleton?
## Provider Constraints
## QA Checklist
## Safety and Rights
```

The quick-start examples must run only local inspection, local preprocessing, or local payload construction. State explicitly that building a payload does not generate a video.

- [ ] **Step 2: Run the README layout test to verify it passes**

Run: `python3 -m unittest tests.test_skill_layout.DanceDepthReferenceVideoLayoutTest.test_readme_documents_workflow_safety_and_local_commands -v`

Expected: PASS.

### Task 3: Verify documentation and package behavior

**Files:**
- Verify: `README.md`
- Verify: `tests/test_build_maybeai_payload.py`
- Verify: `tests/test_skill_layout.py`
- Verify: `scripts/build_maybeai_payload.py`
- Verify: `scripts/inspect_video.py`
- Verify: `scripts/make_depth_video.py`
- Verify: `scripts/make_skeleton_video.py`

- [ ] **Step 1: Run the full unittest suite**

Run: `python3 -m unittest discover -s tests -v`

Expected: all existing payload, package-layout, and README-layout tests pass.

- [ ] **Step 2: Compile every bundled script**

Run: `python3 -m py_compile scripts/build_maybeai_payload.py scripts/inspect_video.py scripts/make_depth_video.py scripts/make_skeleton_video.py`

Expected: exit status 0.

- [ ] **Step 3: Check the staged diff and commit**

Run:

```bash
git add README.md tests/test_skill_layout.py docs/superpowers/specs/2026-08-15-readme-design.md docs/superpowers/plans/2026-08-15-readme-implementation.md
git diff --cached --check
git commit -m "Add dance depth skill README"
git push
```

Expected: a clean staged diff, then a pushed commit on `codex/add-dance-depth-reference-video`.
