import unittest

from app.services import behavior_overlay_service


class BehaviorOverlayServiceTests(unittest.TestCase):
    def test_multiple_people_receive_left_to_right_per_frame_labels(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "frame_quality_label": "good",
                "detections": [
                    {"label": "person", "confidence": 0.73, "box": [220, 0, 300, 180]},
                    {"label": "person", "confidence": 0.91, "box": [10, 0, 90, 180]},
                    {"label": "person", "confidence": 0.82, "box": [110, 0, 190, 180]},
                ],
            }
        )

        candidates = result["student_candidates"]
        self.assertEqual(
            [candidate["student_label"] for candidate in candidates],
            ["Student 1", "Student 2", "Student 3"],
        )
        self.assertEqual([candidate["box"][0] for candidate in candidates], [10.0, 110.0, 220.0])
        self.assertEqual(result["detections"][0]["student_label"], "Student 3")
        self.assertIn("Student 1 · Person candidate 91%", result["detections"][1]["overlay_label"])

    def test_phone_overlap_marks_only_the_matching_student(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "frame_quality_label": "low_light",
                "detections": [
                    {"label": "person", "confidence": 0.88, "box": [0, 0, 80, 200]},
                    {"label": "person", "confidence": 0.86, "box": [100, 0, 180, 200]},
                    {"label": "cell phone", "confidence": 0.61, "box": [120, 50, 145, 90]},
                ],
            }
        )

        first, second = result["student_candidates"]
        self.assertFalse(first["phone_candidate"])
        self.assertTrue(second["phone_candidate"])
        self.assertEqual(second["phone_confidence"], 0.61)
        self.assertEqual(second["candidate_label"], "Phone-use candidate")
        self.assertEqual(second["frame_quality_label"], "low_light")
        self.assertIn(
            "Student 2 · Phone-use candidate 61%",
            result["detections"][1]["overlay_label"],
        )

    def test_person_box_alone_does_not_create_attention_candidate(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "frame_quality_label": "good",
                "behavior_signals": {
                    "head_orientation_available": True,
                    "possible_inattentive": True,
                    "inattentive_confidence": 0.9,
                },
                "detections": [
                    {"label": "person", "confidence": 0.94, "box": [0, 0, 100, 200]},
                ],
            }
        )

        candidate = result["student_candidates"][0]
        self.assertEqual(candidate["attention_candidate"], "model_required")
        self.assertIsNone(candidate["attention_confidence"])
        self.assertEqual(candidate["candidate_label"], "Person candidate")
        self.assertIn("person box alone", candidate["reason"])
        self.assertEqual(result["detections"][0]["attention_label"], "Attention model required")

    def test_validated_per_student_signal_can_create_review_candidate(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "frame_quality_label": "good",
                "student_attention_signals": [
                    {
                        "track_id": 1,
                        "head_orientation_available": True,
                        "attention_candidate": True,
                        "attention_confidence": 0.78,
                    }
                ],
                "detections": [
                    {"label": "person", "confidence": 0.93, "box": [0, 0, 100, 200]},
                ],
            }
        )

        candidate = result["student_candidates"][0]
        self.assertEqual(candidate["attention_candidate"], "candidate")
        self.assertEqual(candidate["attention_confidence"], 0.78)
        self.assertEqual(candidate["candidate_label"], "Attention candidate · teacher review")
        self.assertIn("teacher review required", candidate["reason"])
        self.assertIn(
            "Student 1 · Attention candidate · teacher review 78%",
            result["detections"][0]["overlay_label"],
        )

    def test_face_only_signal_supplies_safe_close_up_overlay_candidate(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "frame_quality_label": "good",
                "detections": [],
                "student_attention_signals": {
                    "1": {
                        "track_id": 1,
                        "student_label": "Student 1",
                        "face_only": True,
                        "attention_candidate": False,
                        "attention_confidence": 0.42,
                        "box": [25, 30, 125, 170],
                        "reason": "Face/upper-body candidate; teacher review required.",
                    }
                },
            }
        )

        self.assertEqual(result["detections"], [])
        self.assertEqual(len(result["student_candidates"]), 1)
        candidate = result["student_candidates"][0]
        self.assertEqual(candidate["box"], [25.0, 30.0, 125.0, 170.0])
        self.assertEqual(candidate["candidate_label"], "Face/upper-body candidate")
        self.assertEqual(candidate["attention_candidate"], "none")

    def test_face_only_attention_signal_remains_candidate_only(self):
        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            {
                "available": True,
                "detections": [],
                "student_attention_signals": {
                    "1": {
                        "face_only": True,
                        "attention_candidate": True,
                        "attention_confidence": 0.81,
                        "box": [10, 20, 110, 160],
                    }
                },
            }
        )

        candidate = result["student_candidates"][0]
        self.assertEqual(candidate["candidate_label"], "Attention candidate")
        self.assertEqual(candidate["attention_candidate"], "candidate")
        self.assertEqual(candidate["attention_confidence"], 0.81)


if __name__ == "__main__":
    unittest.main()
