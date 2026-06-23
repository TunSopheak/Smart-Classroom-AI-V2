import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import download_pose_model


class DownloadPoseModelTests(unittest.TestCase):
    def test_model_destination_uses_expected_filename(self):
        destination = download_pose_model.model_destination("lite", "models")

        self.assertEqual(destination, Path("models") / "pose_landmarker_lite.task")

    def test_unsupported_variant_is_safe(self):
        result = download_pose_model.download_pose_model("unknown")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "unsupported_variant")
        self.assertIn("lite", result["supported_variants"])

    def test_existing_file_without_overwrite_is_not_downloaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "pose_landmarker_lite.task"
            destination.write_bytes(b"existing-model")

            result = download_pose_model.download_pose_model(
                "lite",
                output_dir=temp_dir,
                overwrite=False,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "already_exists")
        self.assertEqual(result["size_bytes"], len(b"existing-model"))

    def test_download_writes_model_bytes(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"fake-task-model"

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("urllib.request.urlopen", return_value=FakeResponse()):
                result = download_pose_model.download_pose_model(
                    "lite",
                    output_dir=temp_dir,
                    overwrite=True,
                )
            destination = Path(result["path"])

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "downloaded")
            self.assertEqual(destination.read_bytes(), b"fake-task-model")


if __name__ == "__main__":
    unittest.main()
