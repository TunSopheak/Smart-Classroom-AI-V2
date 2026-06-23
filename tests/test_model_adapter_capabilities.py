import unittest

from app.services import (
    behavior_decision_engine,
    behavior_overlay_service,
    multibehavior_model_service,
)
from app.services.model_adapters import (
    FaceEmotionAdapter,
    HeadOrientationAdapter,
    PoseAdapter,
)


class ModelAdapterCapabilityTests(unittest.TestCase):
    def test_placeholder_adapters_are_unavailable_and_safe(self):
        for adapter in (
            PoseAdapter(),
            HeadOrientationAdapter(),
            FaceEmotionAdapter(),
        ):
            with self.subTest(adapter=adapter.adapter_name):
                self.assertFalse(adapter.is_available())
                status = adapter.capability_status()
                result = adapter.analyze(
                    b"image-bytes",
                    [{"label": "person", "box": [0, 0, 10, 10]}],
                )

                self.assertFalse(status["available"])
                self.assertEqual(status["status"], "model_required")
                self.assertTrue(status["safe_mode"])
                self.assertEqual(result["predictions"], [])
                self.assertEqual(result["generated_behavior_labels"], [])

    def test_capability_status_lists_all_planned_adapters(self):
        capabilities = multibehavior_model_service.model_capability_status()
        adapter_capabilities = {
            item["capability"] for item in capabilities["adapter_status"]
        }

        self.assertTrue(capabilities["object_detector_active"])
        self.assertFalse(capabilities["pose_model_active"])
        self.assertFalse(capabilities["emotion_model_active"])
        self.assertFalse(capabilities["head_orientation_model_active"])
        self.assertFalse(capabilities["temporal_smoothing_active"])
        self.assertTrue(capabilities["safe_mode"])
        self.assertEqual(
            adapter_capabilities,
            {"pose_model", "head_orientation_model", "face_emotion_model"},
        )

    def test_decision_engine_does_not_fake_behavior_labels(self):
        analysis = {
            "available": True,
            "person_count": 1,
            "phone_count": 0,
            "detections": [
                {
                    "label": "person",
                    "confidence": 0.94,
                    "box": [0, 0, 100, 100],
                }
            ],
        }

        result = behavior_decision_engine.analyze_with_model_adapters(
            b"image-bytes",
            analysis,
        )

        self.assertNotIn("behavior", result["detections"][0])
        self.assertEqual(
            result["behavior_decision"]["adapter_generated_behavior_labels"],
            [],
        )
        self.assertEqual(len(result["adapter_results"]), 3)
        self.assertTrue(result["behavior_decision"]["safe_mode"])

    def test_existing_phone_overlay_is_preserved(self):
        analysis = {
            "available": True,
            "person_count": 1,
            "phone_count": 1,
            "detections": [
                {
                    "label": "person",
                    "confidence": 0.95,
                    "box": [0, 0, 100, 100],
                },
                {
                    "label": "cell phone",
                    "confidence": 0.82,
                    "box": [20, 20, 45, 60],
                },
            ],
        }

        result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
            analysis
        )

        self.assertEqual(
            result["detections"][0]["behavior"],
            "possible_phone_usage",
        )
        self.assertEqual(result["detections"][1]["behavior"], "phone_object")
        self.assertEqual(
            result["behavior_decision"]["object_based_behaviors_preserved"],
            ["phone_object", "possible_phone_usage"],
        )
        self.assertEqual(
            result["behavior_decision"]["adapter_generated_behavior_labels"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
