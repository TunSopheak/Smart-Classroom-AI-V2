import unittest
from datetime import datetime
from unittest.mock import patch

from app.services import behavior_detection_service


class BehaviorDetectionServiceTests(unittest.TestCase):
    def test_person_detection_without_landmarks_is_safe(self):
        analysis = {
            "available": True,
            "person_count": 2,
            "detections": [
                {"label": "person", "confidence": 0.92, "box": [1, 2, 3, 4]},
            ],
        }

        status = behavior_detection_service.analyze_behavior_from_ai_result(
            analysis
        )
        evaluation = behavior_detection_service.evaluate_behavior_event(
            snapshot={"filename": "sample.jpg"},
            image_bytes=b"sample",
            analysis=analysis,
        )

        self.assertFalse(status["behavior_supported"])
        self.assertFalse(status["possible_head_down"])
        self.assertFalse(status["possible_inattentive"])
        self.assertIsNone(status["confidence"])
        self.assertIn("person candidate alone", status["message"])
        self.assertEqual(status["current_consecutive_count"], 0)
        self.assertIsNone(evaluation["event"])
        self.assertEqual(evaluation["state"]["head_down_consecutive_count"], 0)

    def test_behavior_alerts_are_disabled_by_default(self):
        analysis = self.landmark_backed_head_down_analysis()
        state = None

        with patch.object(
            behavior_detection_service,
            "BEHAVIOR_ALERTS_ENABLED",
            False,
        ):
            for _ in range(3):
                evaluation = behavior_detection_service.evaluate_behavior_event(
                    snapshot={"filename": "sample.jpg"},
                    image_bytes=b"sample",
                    analysis=analysis,
                    previous_state=state,
                )
                state = evaluation["state"]

        self.assertEqual(state["head_down_consecutive_count"], 3)
        self.assertIsNone(evaluation["event"])

    def test_landmark_backed_prototype_requires_three_samples(self):
        analysis = self.landmark_backed_head_down_analysis()
        state = None
        events = []
        now = datetime(2026, 6, 23, 12, 0, 0)

        with (
            patch.object(
                behavior_detection_service,
                "BEHAVIOR_ALERTS_ENABLED",
                True,
            ),
            patch.object(
                behavior_detection_service,
                "BEHAVIOR_REQUIRED_SAMPLES",
                3,
            ),
        ):
            for _ in range(3):
                evaluation = behavior_detection_service.evaluate_behavior_event(
                    snapshot={"filename": "sample.jpg"},
                    image_bytes=b"sample",
                    analysis=analysis,
                    previous_state=state,
                    now=now,
                )
                state = evaluation["state"]
                events.append(evaluation["event"])

        self.assertIsNone(events[0])
        self.assertIsNone(events[1])
        self.assertEqual(events[2]["event_type"], "possible_head_down")
        self.assertEqual(
            events[2]["title"],
            "Head-down candidate for review",
        )

    @staticmethod
    def landmark_backed_head_down_analysis():
        return {
            "available": True,
            "person_count": 1,
            "behavior_signals": {
                "pose_landmarks_available": True,
                "head_orientation_available": False,
                "possible_head_down": True,
                "head_down_confidence": 0.88,
                "possible_inattentive": False,
                "reason": "Prototype pose signal remained above its threshold.",
            },
        }


if __name__ == "__main__":
    unittest.main()
