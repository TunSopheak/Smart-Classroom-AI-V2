import tempfile
import unittest
from pathlib import Path

from tools import pose_sandbox


class PoseSandboxTests(unittest.TestCase):
    def test_missing_image_returns_image_not_found(self):
        result = pose_sandbox.run_pose_landmarker(
            "missing_snapshot.jpg",
            "models/pose_landmarker.task",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "image_not_found")

    def test_existing_image_without_model_returns_model_required(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image_file.write(b"not-a-real-image-but-exists")
            image_file.flush()

            result = pose_sandbox.run_pose_landmarker(
                image_file.name,
                "missing_pose_landmarker.task",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["phase"], "30B")
        self.assertEqual(result["status"], "model_required")
        self.assertTrue(result["safe_mode"])
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_image_status_reports_file_metadata(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image_file.write(b"demo")
            image_file.flush()

            status = pose_sandbox.build_image_status(Path(image_file.name))

        self.assertTrue(status.exists)
        self.assertEqual(status.suffix, ".jpg")
        self.assertGreaterEqual(status.size_bytes or 0, 4)


if __name__ == "__main__":
    unittest.main()
