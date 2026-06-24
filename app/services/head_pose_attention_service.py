"""Optional computer-camera head-pose candidate service.

The service is intentionally conservative. It only returns candidate signals for
sampled frames and keeps the app working when optional packages are unavailable.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

YAW_THRESHOLD = 0.32
PITCH_THRESHOLD = 0.62
REQUIRED_SAMPLES = 3
_STATE: dict[str, int] = {}
_LOCK = Lock()


def safe_box(detection: dict) -> list[float] | None:
    box = detection.get("box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        x1, y1, x2, y2 = [float(value) for value in box]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return [x1, y1, x2, y2]


def normalize_label(label: object) -> str:
    return " ".join(str(label or "").strip().lower().replace("_", " ").replace("-", " ").split())


def center_inside(center: list[float], box: list[float]) -> bool:
    return box[0] <= center[0] <= box[2] and box[1] <= center[1] <= box[3]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def optional_imports():
    try:
        import cv2  # type: ignore
        import mediapipe as mp  # type: ignore
        import numpy as np  # type: ignore
    except Exception as error:  # pragma: no cover
        return None, None, None, str(error)
    return cv2, mp, np, None


def estimate_face(landmarks, width: int, height: int) -> dict[str, Any]:
    xs = [float(point.x * width) for point in landmarks]
    ys = [float(point.y * height) for point in landmarks]
    box = [max(0.0, min(xs)), max(0.0, min(ys)), min(float(width), max(xs)), min(float(height), max(ys))]
    center = [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]

    left_face = landmarks[234].x * width
    right_face = landmarks[454].x * width
    nose_x = landmarks[1].x * width
    nose_y = landmarks[1].y * height
    eye_y = ((landmarks[33].y + landmarks[263].y) / 2) * height
    chin_y = landmarks[152].y * height
    face_width = max(1.0, abs(right_face - left_face))
    face_height = max(1.0, abs(chin_y - eye_y))
    yaw = clamp((((nose_x - left_face) / face_width) - 0.5) * 2.0, -1.0, 1.0)
    pitch = clamp((nose_y - eye_y) / face_height, -1.0, 1.0)
    raw_signal = abs(yaw) >= YAW_THRESHOLD or pitch >= PITCH_THRESHOLD
    confidence = clamp(max(abs(yaw), pitch), 0.0, 1.0) if raw_signal else 0.0
    return {
        "box": [round(value, 2) for value in box],
        "center": [round(value, 2) for value in center],
        "head_yaw_estimate": round(float(yaw), 4),
        "head_pitch_estimate": round(float(pitch), 4),
        "attention_confidence": round(float(confidence), 4),
        "raw_signal": bool(raw_signal),
    }


def detect_faces(image_bytes: bytes) -> dict[str, Any]:
    cv2, mp, np, error = optional_imports()
    if error:
        return {"available": False, "status": "optional_dependency_unavailable", "faces": [], "reason": error}
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None:
        return {"available": False, "status": "decode_failed", "faces": [], "reason": "Frame decode failed."}
    height, width = image.shape[:2]
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=8,
        refine_landmarks=True,
        min_detection_confidence=0.45,
    )
    try:
        output = face_mesh.process(rgb_image)
    finally:
        face_mesh.close()
    if not output.multi_face_landmarks:
        return {"available": True, "status": "no_face_landmarks", "faces": [], "reason": "No face/head landmarks available."}
    faces = [estimate_face(face.landmark, width, height) for face in output.multi_face_landmarks]
    return {"available": True, "status": "landmarks_available", "faces": faces, "face_count": len(faces)}


def analyze_student_attention_candidates(
    image_bytes: bytes,
    detections: list[dict],
    session_id: str = "browser-camera",
) -> dict[str, Any]:
    head_pose = detect_faces(image_bytes)
    faces = head_pose.get("faces") if isinstance(head_pose.get("faces"), list) else []
    people = []
    for index, detection in enumerate(detections):
        if isinstance(detection, dict) and normalize_label(detection.get("label")) == "person":
            box = safe_box(detection)
            if box:
                people.append((box[0], index, box))
    people.sort(key=lambda item: item[0])

    signals: dict[str, dict[str, Any]] = {}
    used_faces: set[int] = set()
    with _LOCK:
        for track_id, (_left, _index, person_box) in enumerate(people, start=1):
            matched_face = None
            for face_index, face in enumerate(faces):
                if face_index in used_faces or not isinstance(face, dict):
                    continue
                center = face.get("center")
                if isinstance(center, list) and len(center) >= 2 and center_inside(center, person_box):
                    matched_face = face
                    used_faces.add(face_index)
                    break
            key = f"{session_id}:{track_id}"
            raw_signal = bool(matched_face and matched_face.get("raw_signal"))
            count = _STATE.get(key, 0) + 1 if raw_signal else 0
            _STATE[key] = count
            if matched_face:
                ready = raw_signal and count >= REQUIRED_SAMPLES
                signals[str(track_id)] = {
                    "track_id": track_id,
                    "student_label": f"Student {track_id}",
                    "validated": True,
                    "head_orientation_available": True,
                    "attention_candidate": ready,
                    "possible_inattentive": ready,
                    "attention_confidence": matched_face.get("attention_confidence"),
                    "box": matched_face.get("box"),
                    "head_yaw_estimate": matched_face.get("head_yaw_estimate"),
                    "head_pitch_estimate": matched_face.get("head_pitch_estimate"),
                    "consecutive_samples": count,
                    "required_samples": REQUIRED_SAMPLES,
                    "reason": "Head-pose candidate uses sampled face landmarks and requires teacher review.",
                }
            else:
                _STATE[key] = 0
                signals[str(track_id)] = {
                    "track_id": track_id,
                    "student_label": f"Student {track_id}",
                    "validated": False,
                    "head_orientation_available": False,
                    "attention_candidate": False,
                    "possible_inattentive": False,
                    "attention_confidence": None,
                    "reason": "Face/head landmarks were not available for this student candidate.",
                }

        # A close-up camera view can contain reliable face landmarks while the
        # object detector does not return a full person box. Keep this as a
        # candidate-only signal so the UI still has a review frame to draw.
        if not people:
            for face_index, face in enumerate(faces, start=1):
                if not isinstance(face, dict):
                    continue
                key = f"{session_id}:face:{face_index}"
                raw_signal = bool(face.get("raw_signal"))
                count = _STATE.get(key, 0) + 1 if raw_signal else 0
                _STATE[key] = count
                ready = raw_signal and count >= REQUIRED_SAMPLES
                signals[str(face_index)] = {
                    "track_id": face_index,
                    "student_label": f"Student {face_index}",
                    "validated": True,
                    "face_only": True,
                    "head_orientation_available": True,
                    "attention_candidate": ready,
                    "possible_inattentive": ready,
                    "attention_confidence": face.get("attention_confidence"),
                    "box": face.get("box"),
                    "head_yaw_estimate": face.get("head_yaw_estimate"),
                    "head_pitch_estimate": face.get("head_pitch_estimate"),
                    "consecutive_samples": count,
                    "required_samples": REQUIRED_SAMPLES,
                    "reason": (
                        "Face/upper-body candidate from sampled face landmarks; "
                        "teacher review required."
                    ),
                }
    head_pose["student_attention_signals"] = signals
    return head_pose
