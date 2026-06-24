import tempfile
import unittest
from pathlib import Path

from app.services.camera_quality_service import (
    LOW_QUALITY_WARNING,
    classify_camera_quality,
    classify_live_frame_quality,
    summarize_camera_quality,
)
from tools import camera_quality_check


class CameraQualityServiceTests(unittest.TestCase):
    def test_live_frame_quality_labels_good_frame(self):
        result = classify_live_frame_quality(115, 120)

        self.assertEqual(result["frame_quality_label"], "good")
        self.assertEqual(result["brightness_score"], 115.0)
        self.assertEqual(result["blur_score"], 120.0)
        self.assertEqual(result["frame_quality_warning"], "")

    def test_live_frame_quality_labels_dark_and_blurry_frame(self):
        result = classify_live_frame_quality(25, 20)

        self.assertEqual(result["frame_quality_label"], "low_quality_frame")
        self.assertEqual(result["frame_quality_warning"], LOW_QUALITY_WARNING)

    def test_live_frame_quality_distinguishes_low_light_and_blur(self):
        low_light = classify_live_frame_quality(30, 100)
        blurry = classify_live_frame_quality(100, 25)

        self.assertEqual(low_light["frame_quality_label"], "low_light")
        self.assertEqual(blurry["frame_quality_label"], "blurry")

    def test_good_quality_classification(self):
        result = classify_camera_quality(
            {
                "width": 1280,
                "height": 720,
                "brightness_mean": 120,
                "contrast_std": 45,
                "sharpness_laplacian_var": 120,
            }
        )

        self.assertEqual(result["quality_label"], "good")
        self.assertEqual(result["issues"], [])

    def test_low_light_classification(self):
        result = classify_camera_quality(
            {
                "width": 640,
                "height": 480,
                "brightness_mean": 30,
                "contrast_std": 20,
                "sharpness_laplacian_var": 40,
            }
        )

        self.assertEqual(result["quality_label"], "needs_improvement")
        self.assertIn("too_dark", result["issues"])
        self.assertIn("low_contrast", result["issues"])
        self.assertIn("blurry_or_soft", result["issues"])

    def test_summary_counts_issues(self):
        summary = summarize_camera_quality(
            [
                {"status": "completed", "quality_label": "good", "issues": []},
                {"status": "completed", "quality_label": "needs_improvement", "issues": ["too_dark"]},
            ]
        )

        self.assertEqual(summary["total_images"], 2)
        self.assertEqual(summary["good_quality_images"], 1)
        self.assertEqual(summary["needs_improvement_images"], 1)
        self.assertEqual(summary["issue_counts"], {"too_dark": 1})
        self.assertEqual(summary["generated_behavior_labels"], [])

    def test_discover_images_filters_supported_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image = folder / "snapshot.jpg"
            text = folder / "notes.txt"
            image.write_bytes(b"image")
            text.write_text("ignore", encoding="utf-8")

            result = camera_quality_check.discover_images([str(folder)], limit=10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "snapshot.jpg")

    def test_write_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "camera_quality.csv"
            camera_quality_check.write_csv(
                [
                    {
                        "image_path": "demo.jpg",
                        "status": "completed",
                        "quality_label": "good",
                        "metrics": {
                            "width": 1280,
                            "height": 720,
                            "brightness_mean": 120,
                            "contrast_std": 45,
                            "sharpness_laplacian_var": 120,
                        },
                        "issues": [],
                        "recommendations": [],
                    }
                ],
                csv_path,
            )

            self.assertTrue(csv_path.exists())
            self.assertIn("demo.jpg", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
