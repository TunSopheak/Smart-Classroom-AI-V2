"""Unified behavior-overlay helpers for Pi and browser camera analysis.

This module does not claim to solve sleeping/head-down or emotion detection yet.
It prepares one response format that the frontend can draw consistently for
Raspberry Pi and computer-camera frames, while making future model requirements
explicit.
"""

from __future__ import annotations

from copy import deepcopy

from app.services import behavior_decision_engine, multibehavior_model_service


BEHAVIOR_STYLES: dict[str, dict[str, str]] = {
    "normal_monitoring": {
        "label": "Monitoring Person",
        "risk": "low",
        "color": "#2dd4bf",
        "reason": "Person detected; no behavior-specific signal is available yet.",
    },
    "possible_phone_usage": {
        "label": "Possible Phone Usage",
        "risk": "high",
        "color": "#ef4444",
        "reason": "Phone-like object detected near or inside this person region.",
    },
    "phone_object": {
        "label": "Phone Object",
        "risk": "warning",
        "color": "#f59e0b",
        "reason": "Phone-like object detected by the object model.",
    },
    "possible_head_down": {
        "label": "Possible Head Down",
        "risk": "high",
        "color": "#ef4444",
        "reason": "Reserved for validated pose/head-landmark behavior signals.",
    },
    "looking_around": {
        "label": "Looking Around",
        "risk": "warning",
        "color": "#a855f7",
        "reason": "Reserved for validated face/head-orientation behavior signals.",
    },
    "possible_inattentive": {
        "label": "Possible Inattentive",
        "risk": "warning",
        "color": "#a855f7",
        "reason": "Reserved for validated head-orientation behavior signals.",
    },
    "sleepy_drowsy": {
        "label": "Sleepy / Drowsy",
        "risk": "warning",
        "color": "#f97316",
        "reason": "Reserved for validated eye/head landmark signals over time.",
    },
    "happy_smile": {
        "label": "Happy / Smile",
        "risk": "low",
        "color": "#22c55e",
        "reason": "Reserved for a validated face-emotion model.",
    },
    "laughing": {
        "label": "Laughing",
        "risk": "low",
        "color": "#22c55e",
        "reason": "Reserved for a validated face-emotion model.",
    },
    "sad_tired": {
        "label": "Sad / Tired",
        "risk": "warning",
        "color": "#64748b",
        "reason": "Reserved for a validated face-emotion model and careful interpretation.",
    },
    "object_detected": {
        "label": "Object Detected",
        "risk": "info",
        "color": "#60a5fa",
        "reason": "Object detected by the model.",
    },
}

PHONE_LABELS = {"phone", "cell phone", "mobile phone", "smartphone", "telephone"}


def normalize_label(label: object) -> str:
    return " ".join(
        str(label or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def is_phone_label(label: object) -> bool:
    normalized = normalize_label(label)
    compact = normalized.replace(" ", "")
    return normalized in PHONE_LABELS or "phone" in normalized or compact in {"cellphone", "mobilephone"}


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


def box_area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def intersection_area(a: list[float], b: list[float]) -> float:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    return max(0.0, right - left) * max(0.0, bottom - top)


def phone_overlaps_person(phone_box: list[float], person_box: list[float]) -> bool:
    phone_area = box_area(phone_box)
    if phone_area <= 0:
        return False
    overlap = intersection_area(phone_box, person_box)
    if overlap / phone_area >= 0.15:
        return True

    phone_center_x = (phone_box[0] + phone_box[2]) / 2
    phone_center_y = (phone_box[1] + phone_box[3]) / 2
    return person_box[0] <= phone_center_x <= person_box[2] and person_box[1] <= phone_center_y <= person_box[3]


def style_for(behavior: str) -> dict[str, str]:
    return BEHAVIOR_STYLES.get(behavior, BEHAVIOR_STYLES["object_detected"])


def confidence_percent(value) -> int:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0
    if confidence <= 1:
        confidence *= 100
    return max(0, min(100, round(confidence)))


def apply_overlay_fields(
    detection: dict,
    behavior: str,
    track_id: int | None = None,
    reason: str | None = None,
) -> dict:
    style = style_for(behavior)
    confidence = confidence_percent(detection.get("confidence"))
    behavior_label = style["label"]
    detection["behavior"] = behavior
    detection["behavior_label"] = behavior_label
    detection["risk"] = style["risk"]
    detection["overlay_color"] = style["color"]
    detection["behavior_reason"] = reason or style["reason"]
    detection["overlay_label"] = f"{behavior_label} {confidence}%" if confidence else behavior_label
    detection.setdefault("attention_label", "Monitoring")
    detection.setdefault("emotion_label", "Model Required")
    detection.setdefault("posture_label", "Model Required")
    detection.setdefault("model_status", "object_model_only")
    if track_id is not None:
        detection["track_id"] = track_id
        detection["student_label"] = f"Student {track_id}"
    return detection


def enrich_analysis_for_behavior_overlay(analysis: dict | None) -> dict:
    """Add behavior-overlay fields while keeping the original YOLO data intact."""

    if not isinstance(analysis, dict):
        return {}

    enriched = deepcopy(analysis)
    raw_detections = enriched.get("detections")
    detections = raw_detections if isinstance(raw_detections, list) else []

    person_indexes: list[int] = []
    phone_indexes: list[int] = []
    boxes: dict[int, list[float]] = {}

    for index, detection in enumerate(detections):
        if not isinstance(detection, dict):
            continue
        box = safe_box(detection)
        if box is not None:
            boxes[index] = box
        label = normalize_label(detection.get("label"))
        if label == "person":
            person_indexes.append(index)
        elif is_phone_label(label):
            phone_indexes.append(index)

    sorted_person_indexes = sorted(
        person_indexes,
        key=lambda item: boxes.get(item, [0.0, 0.0, 0.0, 0.0])[0],
    )
    track_ids = {person_index: order + 1 for order, person_index in enumerate(sorted_person_indexes)}

    person_phone_match: dict[int, int] = {}
    for person_index in person_indexes:
        person_box = boxes.get(person_index)
        if not person_box:
            continue
        for phone_index in phone_indexes:
            phone_box = boxes.get(phone_index)
            if phone_box and phone_overlaps_person(phone_box, person_box):
                person_phone_match[person_index] = phone_index
                break

    behavior_counts = {
        "normal_monitoring": 0,
        "possible_phone_usage": 0,
        "phone_object": 0,
        "possible_head_down": 0,
        "possible_inattentive": 0,
        "looking_around": 0,
        "sleepy_drowsy": 0,
        "happy_smile": 0,
        "laughing": 0,
        "sad_tired": 0,
    }

    for index, detection in enumerate(detections):
        if not isinstance(detection, dict):
            continue
        label = normalize_label(detection.get("label"))
        if index in person_phone_match:
            phone_detection = detections[person_phone_match[index]]
            apply_overlay_fields(
                detection,
                "possible_phone_usage",
                track_id=track_ids.get(index),
                reason=f"Phone-like object '{phone_detection.get('label', 'phone')}' detected near this person.",
            )
            behavior_counts["possible_phone_usage"] += 1
        elif label == "person":
            apply_overlay_fields(detection, "normal_monitoring", track_id=track_ids.get(index))
            behavior_counts["normal_monitoring"] += 1
        elif is_phone_label(label):
            apply_overlay_fields(detection, "phone_object")
            behavior_counts["phone_object"] += 1
        else:
            apply_overlay_fields(detection, "object_detected")

    enriched["detections"] = detections
    enriched = multibehavior_model_service.attach_candidate_model_fields(enriched)
    enriched["behavior_summary"] = {
        "schema_version": "behavior-overlay-v2",
        "tracking_mode": "left_to_right_frame_index",
        "tracking_note": "Track IDs are stable only within the latest sampled frame; cross-frame tracking is planned.",
        "supported_sources": ["raspberry_pi_camera", "computer_camera"],
        "behavior_model_status": "object_model_active_pose_emotion_planned",
        "counts": behavior_counts,
        "capabilities": multibehavior_model_service.model_capability_status(),
        "limitations": [
            "Sleepy/head-down behavior needs a validated pose or head-landmark model.",
            "Smile, laugh, sad, and tired labels need a validated face-emotion model.",
            "Person box alone is not enough to claim emotional state or attention state.",
        ],
    }
    return behavior_decision_engine.analyze_with_model_adapters(b"", enriched)
