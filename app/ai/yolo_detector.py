"""YOLOv8 detector wrapper with graceful dependency/model fallback."""

from __future__ import annotations

from functools import lru_cache


TARGET_LABELS = {"person", "cell phone", "book"}


class YoloDetector:
    def __init__(self) -> None:
        self.model = None
        self.error: str | None = None
        self._cv2 = None
        self._np = None
        self._load()

    @property
    def available(self) -> bool:
        return self.model is not None and self._cv2 is not None and self._np is not None

    def _load(self) -> None:
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            from ultralytics import YOLO  # type: ignore
        except ImportError:
            self.error = "Backend YOLO/OpenCV dependencies are not installed."
            return

        self._cv2 = cv2
        self._np = np

        try:
            self.model = YOLO("yolov8n.pt")
            self.error = None
        except Exception:
            self.model = None
            self.error = "YOLOv8n model is unavailable. Install weights or allow model download."

    def analyze(self, image_bytes: bytes) -> dict:
        if not self.available:
            return self.unavailable_result()

        image_array = self._np.frombuffer(image_bytes, dtype=self._np.uint8)
        frame = self._cv2.imdecode(image_array, self._cv2.IMREAD_COLOR)

        if frame is None:
            return {
                "available": False,
                "person_count": 0,
                "phone_count": 0,
                "detections": [],
                "image_width": 0,
                "image_height": 0,
                "message": "Frame could not be decoded. Try restarting the camera.",
            }

        image_height, image_width = frame.shape[:2]

        results = self.model(frame, verbose=False)
        detections = []
        person_count = 0
        phone_count = 0

        for result in results:
            names = result.names or {}

            for box in result.boxes:
                label = names.get(int(box.cls[0]), "unknown")

                if label not in TARGET_LABELS:
                    continue

                confidence = float(box.conf[0])
                x1, y1, x2, y2 = [
                    round(float(value), 2) for value in box.xyxy[0].tolist()
                ]

                detections.append(
                    {
                        "label": label,
                        "confidence": round(confidence, 3),
                        "box": [x1, y1, x2, y2],
                    }
                )

                if label == "person":
                    person_count += 1
                elif label == "cell phone":
                    phone_count += 1

        return {
            "available": True,
            "person_count": person_count,
            "phone_count": phone_count,
            "detections": detections,
            "image_width": image_width,
            "image_height": image_height,
            "message": "Backend AI analysis completed.",
        }

    def unavailable_result(self) -> dict:
        return {
            "available": False,
            "person_count": 0,
            "phone_count": 0,
            "detections": [],
            "image_width": 0,
            "image_height": 0,
            "message": self.error or "Backend AI Engine is unavailable.",
        }


@lru_cache(maxsize=1)
def get_yolo_detector() -> YoloDetector:
    return YoloDetector()