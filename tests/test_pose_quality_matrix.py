import tempfile
import unittest
from pathlib import Path

from tools import pose_quality_matrix


class PoseQualityMatrixTests(unittest.TestCase):
    def test_quality_label(self):
        self.assertEqual(pose_quality_matrix.quality_label(0, None), "not_detected")
        self.assertEqual(pose_quality_matrix.quality_label(1, None), "unknown_visibility")
        self.assertEqual(pose_quality_matrix.quality_label(1, 0.55), "good")
        self.assertEqual(pose_quality_matrix.quality_label(1, 0.44), "weak")
        self.assertEqual(pose_quality_matrix.quality_label(1, 0.20), "poor")

    def test_discover_images_uses_supported_suffixes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            image = folder / "demo.jpg"
            text = folder / "notes.txt"
            image.write_bytes(b"fake-image")
            text.write_text("not an image", encoding="utf-8")

            result = pose_quality_matrix.discover_images([str(folder)], limit=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "demo.jpg")

    def test_summarize_matrix_result_without_pose(self):
        result = pose_quality_matrix.summarize_matrix_result(
            "demo.jpg",
            {
                "ok": True,
                "pose_status": "completed",
                "pose_count": 0,
                "candidate_result": {
                    "status": "pose_not_detected",
                    "posture_candidates": [],
                },
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["phase"], "30E")
        self.assertEqual(result["quality_label"], "not_detected")
        self.assertEqual(result["candidate_label"], "none")
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_summarize_matrix_result_with_candidate(self):
        result = pose_quality_matrix.summarize_matrix_result(
            "demo.jpg",
            {
                "ok": True,
                "pose_status": "completed",
                "pose_count": 1,
                "candidate_result": {
                    "status": "completed",
                    "posture_candidates": [
                        {
                            "label": "possible_head_low_candidate",
                            "confidence": 0.55,
                            "nose_to_shoulder_delta": -0.05,
                        }
                    ],
                },
            },
        )

        self.assertEqual(result["quality_label"], "unknown_visibility")
        self.assertEqual(result["candidate_label"], "possible_head_low_candidate")
        self.assertEqual(result["candidate_confidence"], 0.55)
        self.assertEqual(result["nose_to_shoulder_delta"], -0.05)

    def test_write_csv_creates_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "matrix.csv"
            pose_quality_matrix.write_csv(
                [
                    {
                        "image_path": "demo.jpg",
                        "ok": True,
                        "phase": "30E",
                        "pose_status": "completed",
                        "pose_count": 1,
                        "quality_label": "unknown_visibility",
                        "average_visibility": None,
                        "candidate_label": "normal_upright_candidate",
                        "candidate_confidence": 0.60,
                        "nose_to_shoulder_delta": -0.2,
                        "safe_mode": True,
                    }
                ],
                csv_path,
            )

            self.assertTrue(csv_path.exists())
            self.assertIn("normal_upright_candidate", csv_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
