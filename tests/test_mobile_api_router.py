import unittest

from app.routers import mobile_api


class MobileApiRouterTests(unittest.TestCase):
    def test_health_payload(self):
        # Route registration smoke test: the router should expose the MVP health path.
        paths = {route.path for route in mobile_api.router.routes}

        self.assertIn("/api/mobile/health", paths)
        self.assertIn("/api/mobile/summary", paths)
        self.assertIn("/api/mobile/students", paths)
        self.assertIn("/api/mobile/sessions/today", paths)
        self.assertIn("/api/mobile/iot/status", paths)

    def test_time_and_date_helpers(self):
        self.assertIsNone(mobile_api.iso_date(None))
        self.assertIsNone(mobile_api.time_label(None))

    def test_class_group_payload_none(self):
        self.assertIsNone(mobile_api.class_group_payload(None))


if __name__ == "__main__":
    unittest.main()
