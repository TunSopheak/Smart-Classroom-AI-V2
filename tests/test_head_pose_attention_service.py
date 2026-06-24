import unittest
from unittest.mock import patch

from app.services import head_pose_attention_service


class HeadPoseAttentionServiceTests(unittest.TestCase):
    def setUp(self):
        head_pose_attention_service._STATE.clear()

    @patch("app.services.head_pose_attention_service.detect_faces")
    def test_close_up_face_without_person_supplies_candidate_box(self, detect_faces):
        detect_faces.return_value = {
            "available": True,
            "status": "landmarks_available",
            "faces": [
                {
                    "box": [20, 30, 120, 170],
                    "raw_signal": False,
                    "attention_confidence": 0.0,
                    "head_yaw_estimate": 0.1,
                    "head_pitch_estimate": 0.2,
                }
            ],
        }

        result = head_pose_attention_service.analyze_student_attention_candidates(
            b"sample", [], "close-up"
        )

        signal = result["student_attention_signals"]["1"]
        self.assertTrue(signal["face_only"])
        self.assertEqual(signal["box"], [20, 30, 120, 170])
        self.assertFalse(signal["attention_candidate"])
        self.assertIn("teacher review required", signal["reason"])

    @patch("app.services.head_pose_attention_service.detect_faces")
    def test_close_up_attention_requires_consecutive_samples(self, detect_faces):
        detect_faces.return_value = {
            "available": True,
            "status": "landmarks_available",
            "faces": [
                {
                    "box": [20, 30, 120, 170],
                    "raw_signal": True,
                    "attention_confidence": 0.76,
                }
            ],
        }

        candidate_states = []
        for _ in range(head_pose_attention_service.REQUIRED_SAMPLES):
            result = head_pose_attention_service.analyze_student_attention_candidates(
                b"sample", [], "close-up"
            )
            candidate_states.append(
                result["student_attention_signals"]["1"]["attention_candidate"]
            )

        self.assertFalse(candidate_states[0])
        self.assertTrue(candidate_states[-1])


if __name__ == "__main__":
    unittest.main()
