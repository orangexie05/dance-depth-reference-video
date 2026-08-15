from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class DanceDepthReferenceVideoLayoutTest(unittest.TestCase):
    def test_skill_package_includes_documentation_scripts_and_references(self):
        self.assertTrue((REPO_ROOT / "SKILL.md").is_file())
        self.assertTrue((REPO_ROOT / "agents" / "openai.yaml").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "build_maybeai_payload.py").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "inspect_video.py").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "make_depth_video.py").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "make_skeleton_video.py").is_file())
        self.assertTrue((REPO_ROOT / "references" / "provider-routing.md").is_file())

    def test_readme_contains_user_facing_workflow_and_quick_start_contract(self):
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


if __name__ == "__main__":
    unittest.main()
