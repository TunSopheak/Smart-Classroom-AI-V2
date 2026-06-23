import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services import iot_service


class IotDeviceStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 6, 23, 12, 0, 0)

    def test_no_heartbeat_and_no_snapshot_is_offline(self):
        status = iot_service.build_device_status({}, {}, self.now)

        self.assertFalse(status["online"])
        self.assertEqual(status["status_label"], "Offline")
        self.assertEqual(status["status_source"], "No Fresh Signal")
        self.assertFalse(status["heartbeat_online"])
        self.assertFalse(status["snapshot_upload_online"])

    def test_fresh_snapshot_without_heartbeat_is_online(self):
        snapshot = {
            "available": True,
            "url": "/static/uploads/iot_snapshots/fresh.jpg",
            "uploaded_at": self.now - timedelta(seconds=10),
            "device_name": "Classroom Pi",
            "ip_address": "10.0.0.25",
        }

        status = iot_service.build_device_status({}, snapshot, self.now)

        self.assertTrue(status["online"])
        self.assertEqual(status["status_source"], "Snapshot Upload")
        self.assertEqual(status["latest_snapshot_age_seconds"], 10)
        self.assertEqual(status["device_name"], "Classroom Pi")
        self.assertEqual(status["ip_address"], "10.0.0.25")
        self.assertEqual(
            status["message"],
            "Raspberry Pi is online from recent snapshot uploads.",
        )

    def test_fresh_heartbeat_without_snapshot_is_online(self):
        device = {
            "last_seen_at": self.now - timedelta(seconds=5),
            "device_name": "Heartbeat Pi",
            "ip_address": "10.0.0.30",
        }

        status = iot_service.build_device_status(device, {}, self.now)

        self.assertTrue(status["online"])
        self.assertEqual(status["status_source"], "Heartbeat")
        self.assertTrue(status["heartbeat_online"])
        self.assertFalse(status["snapshot_upload_online"])

    def test_fresh_heartbeat_and_snapshot_use_both_sources(self):
        device = {"last_seen_at": self.now - timedelta(seconds=5)}
        snapshot = {
            "available": True,
            "uploaded_at": self.now - timedelta(seconds=10),
        }

        status = iot_service.build_device_status(device, snapshot, self.now)

        self.assertTrue(status["online"])
        self.assertEqual(
            status["status_source"],
            "Heartbeat + Snapshot Upload",
        )
        self.assertTrue(status["heartbeat_online"])
        self.assertTrue(status["snapshot_upload_online"])

    def test_old_snapshot_is_stale_and_offline(self):
        snapshot = {
            "available": True,
            "uploaded_at": self.now - timedelta(seconds=60),
        }

        status = iot_service.build_device_status({}, snapshot, self.now)

        self.assertFalse(status["online"])
        self.assertEqual(status["status_label"], "Stale")
        self.assertFalse(status["snapshot_upload_online"])
        self.assertEqual(status["latest_snapshot_age_seconds"], 60)
        self.assertIn("snapshot is stale", status["message"])

    def test_future_snapshot_clock_skew_clamps_age_to_zero(self):
        age = iot_service.compute_snapshot_age_seconds(
            self.now + timedelta(seconds=5),
            self.now,
        )

        self.assertEqual(age, 0)

    def test_device_status_response_keeps_compatibility_and_new_fields(self):
        snapshot_state = {
            "filename": "fresh.jpg",
            "url": "/static/uploads/iot_snapshots/fresh.jpg",
            "uploaded_at": self.now - timedelta(seconds=10),
            "device_name": "Classroom Pi",
            "ip_address": "10.86.94.200",
            "size_bytes": 1234,
            "session_id": None,
        }
        with (
            patch.dict(
                iot_service._device_state,
                {
                    "device_name": iot_service.DEVICE_NAME_DEFAULT,
                    "last_seen_at": None,
                    "ip_address": None,
                },
                clear=True,
            ),
            patch.dict(
                iot_service._camera_snapshot_state,
                snapshot_state,
                clear=True,
            ),
        ):
            status = iot_service.device_status(self.now)

        new_fields = {
            "online",
            "status_label",
            "status_source",
            "heartbeat_online",
            "snapshot_upload_online",
            "latest_snapshot_age_seconds",
            "last_snapshot_uploaded_at",
            "ip_address",
            "device_name",
            "message",
        }
        compatibility_fields = {
            "status",
            "last_seen_at",
            "seconds_since_last_seen",
            "heartbeat_timeout_seconds",
            "light_1",
            "light_2",
            "light_1_label",
            "light_2_label",
            "snapshot",
            "analysis",
            "snapshot_storage",
        }

        self.assertTrue(new_fields.issubset(status))
        self.assertTrue(compatibility_fields.issubset(status))
        self.assertTrue(status["snapshot"]["available"])
        self.assertTrue(status["online"])
        self.assertEqual(status["status"], "Online")
        self.assertEqual(status["status_source"], "Snapshot Upload")
        self.assertEqual(status["ip_address"], "10.86.94.200")

    def test_stale_session_skips_sync_without_failing_analysis(self):
        try:
            state = iot_service.save_camera_analysis(
                analysis={
                    "available": True,
                    "person_count": 1,
                    "phone_count": 0,
                    "detections": [],
                },
                occupancy=None,
                occupancy_synced=False,
                occupancy_error="Selected session is no longer active.",
                session_id="11",
            )

            self.assertTrue(state["available"])
            self.assertFalse(state["occupancy_synced"])
            self.assertEqual(state["session_sync_status"], "not_active")
            self.assertIn("AI analysis completed", state["session_sync_message"])
            self.assertIn("no longer active", state["session_sync_message"])
        finally:
            iot_service.reset_camera_analysis()


if __name__ == "__main__":
    unittest.main()
