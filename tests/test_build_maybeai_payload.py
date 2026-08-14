import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_maybeai_payload.py"


class MaybeAIPayloadContractTests(unittest.TestCase):
    def test_builder_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_builds_role_labelled_seedance_reference_payload(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--character-url", "https://cdn.example.com/character.png",
                "--motion-video-url", "https://cdn.example.com/depth.mp4",
                "--scene-url", "https://cdn.example.com/scene.png",
                "--duration", "5", "--aspect-ratio", "9:16", "--task-id", "depth-plan-1",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["task_id"], "depth-plan-1")
        self.assertEqual(payload["model"], "bytedance/seedance-2.0/fast/reference-to-video")
        self.assertEqual(payload["image_urls"], ["https://cdn.example.com/character.png", "https://cdn.example.com/scene.png"])
        self.assertEqual(payload["video_urls"], ["https://cdn.example.com/depth.mp4"])
        self.assertEqual(payload["duration"], "5")
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertFalse(payload["generate_audio"])
        self.assertIn("@Image1", payload["prompt"])
        self.assertIn("@Image2", payload["prompt"])
        self.assertIn("@Video1", payload["prompt"])

    def test_rejects_local_reference_paths(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--character-url", "/tmp/character.png",
                "--motion-video-url", "https://cdn.example.com/depth.mp4",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTTP(S) URL", result.stderr)

    def test_rejects_motion_longer_than_reference_limit(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--character-url", "https://cdn.example.com/character.png",
                "--motion-video-url", "https://cdn.example.com/depth.mp4",
                "--motion-duration-seconds", "19.533333",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be segmented", result.stderr)

    def test_accepts_explicit_local_media_files_by_encoding_data_uris(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            character = root / "character.png"
            motion = root / "depth.mp4"
            character.write_bytes(b"PNG")
            motion.write_bytes(b"MP4")
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--character-file", str(character),
                    "--motion-video-file", str(motion),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["image_urls"][0].startswith("data:image/png;base64,"))
        self.assertTrue(payload["video_urls"][0].startswith("data:video/mp4;base64,"))


if __name__ == "__main__":
    unittest.main()
