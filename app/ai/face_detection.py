import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.core.config import FACE_CONFIDENCE_THRESHOLD, FACE_DATASET_DIR, FACE_MODEL_PATH


FACE_SIZE = (160, 160)
LABELS_SUFFIX = ".labels.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


@dataclass
class FacePrediction:
    label: str | None
    confidence: float
    distance: float | None
    bbox: dict
    recognized: bool

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "student_code": self.label,
            "confidence": round(self.confidence, 2),
            "distance": round(self.distance, 2) if self.distance is not None else None,
            "bbox": self.bbox,
            "recognized": self.recognized,
            "status": "recognized" if self.recognized else "unknown",
        }


class OpenCVFaceRecognizer:
    def __init__(
        self,
        dataset_dir: Path = FACE_DATASET_DIR,
        model_path: Path = FACE_MODEL_PATH,
        threshold: float = FACE_CONFIDENCE_THRESHOLD,
    ):
        self.dataset_dir = Path(dataset_dir)
        self.model_path = Path(model_path)
        self.labels_path = self.model_path.with_suffix(self.model_path.suffix + LABELS_SUFFIX)
        self.threshold = threshold
        self.face_cascade = cv2.CascadeClassifier(
            str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        )
        self.model = None
        self.labels: dict[int, str] = {}
        self._loaded = False

    @property
    def lbph_available(self) -> bool:
        return hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create")

    def create_model(self):
        if not self.lbph_available:
            return None
        return cv2.face.LBPHFaceRecognizer_create()

    def decode_image(self, image_bytes: bytes):
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    def prepare_gray(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.equalizeHist(gray)

    def detect_faces(self, gray_image) -> list[tuple[int, int, int, int]]:
        faces = self.face_cascade.detectMultiScale(
            gray_image,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
        )
        return sorted(faces, key=lambda box: box[0])

    def crop_face(self, gray_image, bbox: tuple[int, int, int, int]):
        x, y, width, height = bbox
        face = gray_image[y : y + height, x : x + width]
        if face.size == 0:
            return None
        return cv2.resize(face, FACE_SIZE)

    def scan_dataset(self) -> tuple[list, list[int], dict[int, str]]:
        images = []
        numeric_labels = []
        label_names: dict[int, str] = {}

        if not self.dataset_dir.exists():
            print(f"[face] Dataset directory not found: {self.dataset_dir}")
            return images, numeric_labels, label_names

        label_id = 0
        for student_dir in sorted(path for path in self.dataset_dir.iterdir() if path.is_dir()):
            label = student_dir.name.strip()
            if not label:
                continue

            sample_count = 0
            for image_path in sorted(student_dir.iterdir()):
                if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                image = cv2.imread(str(image_path))
                if image is None:
                    continue

                gray = self.prepare_gray(image)
                faces = self.detect_faces(gray)
                if not faces:
                    continue

                largest = max(faces, key=lambda box: box[2] * box[3])
                face = self.crop_face(gray, largest)
                if face is None:
                    continue

                images.append(face)
                numeric_labels.append(label_id)
                sample_count += 1

            if sample_count:
                label_names[label_id] = label
                print(f"[face] Dataset scanned: {label} ({sample_count} usable image(s))")
                label_id += 1
            else:
                print(f"[face] Dataset skipped: {label} (no usable face images)")

        print(f"[face] Dataset scan complete: {len(label_names)} student label(s), {len(images)} face sample(s)")
        return images, numeric_labels, label_names

    def train_from_dataset(self) -> bool:
        if not self.lbph_available:
            print("[face] LBPH unavailable. Install opencv-contrib-python to enable face recognition.")
            return False

        images, numeric_labels, label_names = self.scan_dataset()
        if not images or not numeric_labels:
            print("[face] Model training skipped: no usable dataset images.")
            return False

        model = self.create_model()
        if model is None:
            return False

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        model.train(images, np.array(numeric_labels))
        model.write(str(self.model_path))
        self.labels_path.write_text(json.dumps(label_names, indent=2), encoding="utf-8")
        self.model = model
        self.labels = label_names
        self._loaded = True
        print(f"[face] Model trained and saved: {self.model_path}")
        return True

    def load_model(self) -> bool:
        if self._loaded and self.model is not None:
            return True

        if not self.lbph_available:
            print("[face] LBPH unavailable. Install opencv-contrib-python to enable face recognition.")
            return False

        if not self.model_path.exists() or not self.labels_path.exists():
            return self.train_from_dataset()

        model = self.create_model()
        if model is None:
            return False

        try:
            model.read(str(self.model_path))
            raw_labels = json.loads(self.labels_path.read_text(encoding="utf-8"))
        except (cv2.error, OSError, json.JSONDecodeError) as error:
            print(f"[face] Model load failed, retraining from dataset: {error}")
            return self.train_from_dataset()

        self.model = model
        self.labels = {int(key): value for key, value in raw_labels.items()}
        self._loaded = True
        print(f"[face] Model loaded: {self.model_path} ({len(self.labels)} label(s))")
        return True

    def recognize(self, image_bytes: bytes) -> dict:
        image = self.decode_image(image_bytes)
        if image is None:
            return {
                "available": False,
                "message": "Face frame could not be decoded.",
                "faces": [],
                "unknown_face_count": 0,
            }

        gray = self.prepare_gray(image)
        detected_faces = self.detect_faces(gray)
        if not detected_faces:
            return {
                "available": True,
                "message": "No faces detected.",
                "faces": [],
                "unknown_face_count": 0,
            }

        model_ready = self.load_model()
        unavailable_message = (
            "LBPH face recognition is unavailable. Install opencv-contrib-python and restart the app."
            if not self.lbph_available
            else "Face model is not trained yet."
        )
        predictions = []
        unknown_count = 0

        for bbox_tuple in detected_faces:
            x, y, width, height = [int(value) for value in bbox_tuple]
            bbox = {"x": x, "y": y, "width": width, "height": height}
            face = self.crop_face(gray, bbox_tuple)

            if face is None or not model_ready or self.model is None:
                unknown_count += 1
                print("[face] Unknown face detected.")
                predictions.append(FacePrediction(None, 0.0, None, bbox, False).as_dict())
                continue

            numeric_label, distance = self.model.predict(face)
            label = self.labels.get(int(numeric_label))
            recognized = bool(label) and distance <= self.threshold
            confidence = max(0.0, min(100.0, 100.0 - float(distance)))

            if recognized:
                print(f"[face] Student recognized: {label} (distance={distance:.2f})")
            else:
                unknown_count += 1
                print(f"[face] Unknown face detected. Best match={label}, distance={distance:.2f}")

            predictions.append(
                FacePrediction(
                    label=label if recognized else None,
                    confidence=confidence,
                    distance=float(distance),
                    bbox=bbox,
                    recognized=recognized,
                ).as_dict()
            )

        return {
            "available": model_ready,
            "message": "Face recognition completed." if model_ready else unavailable_message,
            "faces": predictions,
            "unknown_face_count": unknown_count,
        }


_recognizer: OpenCVFaceRecognizer | None = None


def get_face_recognizer() -> OpenCVFaceRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = OpenCVFaceRecognizer()
    return _recognizer


def recognize_faces(image_bytes: bytes) -> dict:
    return get_face_recognizer().recognize(image_bytes)


def train_face_model() -> bool:
    return get_face_recognizer().train_from_dataset()
