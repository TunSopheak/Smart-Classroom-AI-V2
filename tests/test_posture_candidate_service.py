import unittest

from app.services import posture_candidate_service


class PostureCandidateServiceTests(unittest.TestCase):
    def test_completed_pose_result_without_pose_is_not_detected(self):
        result = posture_candidate_service.evaluate_pose_result(
            {"ok": True, "status": "completed", "pose_summaries": []}
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "pose_not_detected")
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_model_required_stays_safe(self):
        result = posture_candidate_service.evaluate_pose_result(
            {"ok": True, "status": "model_required"}
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "model_required")
        self.assertTrue(result["safe_mode"])
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_normal_upright_candidate_from_nose_above_shoulders(self):
        pose_summary = {
            "average_visibility": 0.44,
            "key_landmarks": {
                "nose": {"x": 0.51, "y": 0.43, "visibility": 0.99},
                "left_shoulder": {"x": 0.69, "y": 0.80, "visibility": 0.99},
                "right_shoulder": {"x": 0.34, "y": 0.80, "visibility": 0.99},
            },
        }

        result = posture_candidate_service.evaluate_posture_candidate(pose_summary)

        self.assertEqual(result["label"], "normal_upright_candidate")
        self.assertTrue(result["safe_mode"])
        self.assertLess(result["nose_to_shoulder_delta"], -0.08)
        self.assertEqual(result["generated_behavior_labels"], [])
        self.assertIsNotNone(result["lower_body_quality_note"])

    def test_possible_head_low_candidate_when_nose_close_to_shoulders(self):
        pose_summary = {
            "average_visibility": 0.80,
            "key_landmarks": {
                "nose": {"x": 0.50, "y": 0.74, "visibility": 0.95},
                "left_shoulder": {"x": 0.66, "y": 0.80, "visibility": 0.95},
                "right_shoulder": {"x": 0.34, "y": 0.80, "visibility": 0.95},
            },
        }

        result = posture_candidate_service.evaluate_posture_candidate(pose_summary)

        self.assertEqual(result["label"], "possible_head_low_candidate")
        self.assertGreaterEqual(result["nose_to_shoulder_delta"], -0.08)
        self.assertEqual(result["generated_behavior_labels"], [])

    def test_insufficient_pose_quality_when_keypoint_missing(self):
        pose_summary = {
            "average_visibility": 0.80,
            "key_landmarks": {
                "nose": {"x": 0.50, "y": 0.40, "visibility": 0.95},
                "left_shoulder": None,
                "right_shoulder": {"x": 0.34, "y": 0.80, "visibility": 0.95},
            },
        }

        result = posture_candidate_service.evaluate_posture_candidate(pose_summary)

        self.assertEqual(result["label"], "insufficient_pose_quality")
        self.assertFalse(result["ready_keypoints"]["left_shoulder"])
        self.assertEqual(result["generated_behavior_labels"], [])


if __name__ == "__main__":
    unittest.main()
