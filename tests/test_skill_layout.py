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


if __name__ == "__main__":
    unittest.main()
