import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from app.services import iot_event_service


class PhoneEventPolicyTests(unittest.TestCase):
    def setUp(self):
        iot_event_service._last_event_at.clear()
        iot_event_service._recent_events.clear()
        iot_event_service._saved_source_files.clear()

    def tearDown(self):
        iot_event_service._last_event_at.clear()
        iot_event_service._recent_events.clear()
        iot_event_service._saved_source_files.clear()

    def test_phone_label_matching_is_robust(self):
        for label in (
            "cell phone",
            "Phone",
            "mobile_phone",
            "smartphone",
            "cell-phone",
            "telephone",
        ):
            with self.subTest(label=label):
                self.assertTrue(iot_event_service.is_phone_label(label))

        for label in ("person", "book", "headphones", "microphone"):
            with self.subTest(label=label):
                self.assertFalse(iot_event_service.is_phone_label(label))

    def test_phone_threshold_selects_strongest_matching_detection(self):
        analysis = {
            "detections": [
                {"label": "phone", "confidence": 0.58, "box": [1, 2, 3, 4]},
                {"label": "mobile phone", "confidence": 0.81, "box": [5, 6, 7, 8]},
                {"label": "person", "confidence": 0.99, "box": [0, 0, 9, 9]},
            ]
        }

        selected = iot_event_service.qualifying_phone_detection(
            analysis,
            threshold=0.60,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected["label"], "mobile phone")
        self.assertEqual(selected["confidence"], 0.81)
        self.assertIsNone(
            iot_event_service.qualifying_phone_detection(
                analysis,
                threshold=0.90,
            )
        )

    def test_image_without_metadata_remains_generic_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            evidence_directory = Path(temporary_directory)
            image_path = evidence_directory / "light_auto_off_20260622_122558_097459_deadbeef.jpg"
            image_path.write_bytes(b"legacy-image")
            with patch.object(
                iot_event_service,
                "EVENT_SNAPSHOT_DIR",
                evidence_directory,
            ):
                evidence = iot_event_service.recent_event_files()[0]

        self.assertEqual(evidence["event_type"], "ai_evidence")
        self.assertEqual(evidence["event_type_label"], "AI Evidence")
        self.assertIsNone(evidence["confidence"])

    def test_phone_evidence_writes_and_reloads_json_metadata(self):
        now = iot_event_service.utc_now()
        analysis = {
            "available": True,
            "person_count": 1,
            "phone_count": 1,
            "detections": [
                {"label": "cell phone", "confidence": 0.84, "box": [1, 2, 3, 4]},
            ],
        }
        snapshot = {
            "filename": "pi_sample.jpg",
            "session_id": None,
            "device_name": "classroom-pi",
        }
        events = iot_event_service.qualifying_events(
            analysis,
            session_id=None,
            device_name="classroom-pi",
            previous_light={},
            current_light={},
            now=now,
        )

        self.assertEqual(events[0]["event_type"], "phone_usage")
        self.assertEqual(events[0]["title"], "Possible phone usage detected")

        with tempfile.TemporaryDirectory() as temporary_directory:
            evidence_directory = Path(temporary_directory)
            with (
                patch.object(
                    iot_event_service,
                    "EVENT_SNAPSHOT_DIR",
                    evidence_directory,
                ),
                patch.object(
                    iot_event_service,
                    "EVENT_SNAPSHOTS_ENABLED",
                    True,
                ),
            ):
                saved = iot_event_service.save_event_evidence(
                    source_filename="pi_sample.jpg",
                    image_bytes=b"test-image-bytes",
                    snapshot=snapshot,
                    analysis=analysis,
                    events=events,
                    now=now,
                )

                self.assertIsNotNone(saved)
                image_path = evidence_directory / saved["filename"]
                metadata_path = image_path.with_suffix(".json")
                self.assertTrue(image_path.exists())
                self.assertTrue(metadata_path.exists())

                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["event_type"], "phone_usage")
                self.assertEqual(metadata["confidence"], 0.84)
                self.assertEqual(metadata["label"], "cell phone")
                self.assertEqual(metadata["source_snapshot_filename"], "pi_sample.jpg")

                iot_event_service._recent_events.clear()
                reloaded = iot_event_service.recent_event_files()
                self.assertEqual(reloaded[0]["title"], "Possible phone usage detected")
                self.assertEqual(reloaded[0]["event_type_label"], "Phone Usage")
                self.assertEqual(reloaded[0]["confidence"], 0.84)

                later_events = iot_event_service.qualifying_events(
                    analysis,
                    session_id=None,
                    device_name="classroom-pi",
                    previous_light={},
                    current_light={},
                    now=now + timedelta(seconds=1),
                )
                self.assertEqual(later_events, [])


if __name__ == "__main__":
    unittest.main()
