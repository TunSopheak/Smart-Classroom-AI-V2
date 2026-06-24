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
        "label": "Person candidate",
        "risk": "low",
        "color": "#2dd4bf",
        "reason": "Person candidate from a sampled frame; no behavior judgment is made.",
    },
    "possible_phone_usage": {
        "label": "Phone-use candidate",
        "risk": "high",
        "color": "#ef4444",
        "reason": "A sampled frame contains a phone-like object near this person candidate; teacher review required.",
    },
    "phone_object": {
        "label": "Phone object candidate",
        "risk": "warning",
        "color": "#f59e0b",
        "reason": "Phone-like object candidate from sampled analysis; teacher review required.",
    },
    "possible_head_down": {
        "label": "Head-down candidate",
        "risk": "high",
        "color": "#ef4444",
        "reason": "Model required; any future sampled result must remain a candidate for teacher review.",
    },
    "looking_around": {
        "label": "Looking-around candidate",
        "risk": "warning",
        "color": "#a855f7",
        "reason": "Model required; camera angle and frame quality can affect this candidate.",
    },
    "possible_inattentive": {
        "label": "Attention candidate",
        "risk": "warning",
        "color": "#a855f7",
        "reason": "Model required; this candidate cannot establish a person's attention state.",
    },
    "sleepy_drowsy": {
        "label": "Drowsiness candidate (planned)",
        "risk": "warning",
        "color": "#f97316",
        "reason": "Model required; no drowsiness judgment is available.",
    },
    "happy_smile": {
        "label": "Expression candidate (planned)",
        "risk": "low",
        "color": "#22c55e",
        "reason": "Model required; no emotion judgment is available.",
    },
    "laughing": {
        "label": "Expression candidate (planned)",
        "risk": "low",
        "color": "#22c55e",
        "reason": "Model required; no emotion judgment is available.",
    },
    "sad_tired": {
        "label": "Expression candidate (planned)",
        "risk": "warning",
        "color": "#64748b",
        "reason": "Model required; no emotion or tiredness judgment is available.",
    },
    "object_detected": {
        "label": "Object candidate",
        "risk": "info",
        "color": "#60a5fa",
        "reason": "Object candidate from sampled model analysis.",
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


def phone_person_match_score(
    phone_box: list[float],
    person_box: list[float],
) -> float:
    """Score one phone/person match without assigning the phone to every box."""

    phone_area = box_area(phone_box)
    if phone_area <= 0 or not phone_overlaps_person(phone_box, person_box):
        return 0.0
    overlap_ratio = intersection_area(phone_box, person_box) / phone_area
    phone_center_x = (phone_box[0] + phone_box[2]) / 2
    phone_center_y = (phone_box[1] + phone_box[3]) / 2
    center_inside = (
        person_box[0] <= phone_center_x <= person_box[2]
        and person_box[1] <= phone_center_y <= person_box[3]
    )
    return overlap_ratio + (0.01 if center_inside else 0.0)


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


def safe_unit_confidence(value) -> float | None:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1:
        confidence /= 100
    return round(max(0.0, min(1.0, confidence)), 3)


def attention_signal_for_track(analysis: dict, track_id: int) -> dict | None:
    """Resolve only explicitly per-student signals; never copy one global signal."""

    signals = analysis.get("student_attention_signals")
    if isinstance(signals, dict):
        candidate = signals.get(str(track_id)) or signals.get(f"Student {track_id}")
        return candidate if isinstance(candidate, dict) else None
    if isinstance(signals, list):
        for candidate in signals:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("track_id") == track_id or candidate.get("student_label") == f"Student {track_id}":
                return candidate
    return None


def attention_candidate_status(analysis: dict, track_id: int) -> tuple[str, float | None, str]:
    signal = attention_signal_for_track(analysis, track_id)
    if not signal or not (
        signal.get("validated")
        or signal.get("pose_landmarks_available")
        or signal.get("head_orientation_available")
    ):
        return (
            "model_required",
            None,
            "Attention model required; a person box alone cannot create an attention candidate.",
        )

    is_candidate = bool(
        signal.get("attention_candidate")
        or signal.get("possible_inattentive")
    )
    confidence = safe_unit_confidence(
        signal.get("attention_confidence", signal.get("inattentive_confidence"))
    )
    if is_candidate:
        return (
            "candidate",
            confidence,
            "Attention candidate from a validated per-student signal; teacher review required.",
        )
    return (
        "none",
        confidence,
        "No attention candidate in the validated per-student sampled signal.",
    )


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
    detection.setdefault("attention_label", "Teacher review required")
    detection.setdefault("emotion_label", "Model required")
    detection.setdefault("posture_label", "Model required")
    detection.setdefault("model_status", "object_model_only")
    if track_id is not None:
        detection["track_id"] = track_id
        detection["student_label"] = f"Student {track_id}"
        detection["overlay_label"] = (
            f"Student {track_id} · {behavior_label} {confidence}%"
            if confidence
            else f"Student {track_id} · {behavior_label}"
        )
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
    person_phone_scores: dict[int, float] = {}
    for phone_index in phone_indexes:
        phone_box = boxes.get(phone_index)
        if not phone_box:
            continue
        scored_people = [
            (phone_person_match_score(phone_box, boxes[person_index]), person_index)
            for person_index in person_indexes
            if person_index in boxes
        ]
        score, person_index = max(scored_people, default=(0.0, -1))
        if score > person_phone_scores.get(person_index, 0.0):
            person_phone_match[person_index] = phone_index
            person_phone_scores[person_index] = score

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
                reason=(
                    f"Sampled object model found a phone-like candidate "
                    f"'{phone_detection.get('label', 'phone')}' near this person candidate; "
                    "teacher review required."
                ),
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
    student_candidates = []
    for person_index in sorted_person_indexes:
        detection = detections[person_index]
        if not isinstance(detection, dict):
            continue
        track_id = track_ids[person_index]
        phone_index = person_phone_match.get(person_index)
        phone_detection = detections[phone_index] if phone_index is not None else None
        attention_status, attention_confidence, attention_reason = attention_candidate_status(
            enriched,
            track_id,
        )
        phone_candidate = isinstance(phone_detection, dict)
        attention_label = {
            "candidate": "Attention candidate · teacher review",
            "none": "No attention candidate",
            "model_required": "Attention model required",
        }[attention_status]
        candidate_label = (
            "Phone-use candidate"
            if phone_candidate
            else (
                "Attention candidate · teacher review"
                if attention_status == "candidate"
                else "Person candidate"
            )
        )
        detection["attention_label"] = attention_label
        detection["attention_confidence"] = attention_confidence
        detection["student_candidate_label"] = candidate_label
        candidate_confidence = (
            safe_unit_confidence(phone_detection.get("confidence"))
            if phone_candidate
            else (
                attention_confidence
                if attention_status == "candidate" and attention_confidence is not None
                else safe_unit_confidence(detection.get("confidence"))
            )
        )
        detection["candidate_confidence"] = candidate_confidence
        candidate_percent = confidence_percent(candidate_confidence)
        detection["overlay_label"] = (
            f"Student {track_id} · {candidate_label} {candidate_percent}%"
            if candidate_percent
            else f"Student {track_id} · {candidate_label}"
        )
        reason = (
            detection.get("behavior_reason")
            if phone_candidate
            else attention_reason
        )
        student_candidates.append(
            {
                "student_label": f"Student {track_id}",
                "track_id": track_id,
                "person_confidence": safe_unit_confidence(detection.get("confidence")),
                "box": boxes.get(person_index),
                "phone_candidate": phone_candidate,
                "phone_confidence": (
                    safe_unit_confidence(phone_detection.get("confidence"))
                    if phone_candidate
                    else None
                ),
                "attention_candidate": attention_status,
                "attention_confidence": attention_confidence,
                "candidate_label": candidate_label,
                "reason": reason,
                "frame_quality_label": enriched.get("frame_quality_label", "unknown"),
            }
        )

    # Close-up views may produce face landmarks without a YOLO person box.
    # Preserve that available box as a safe review candidate for the overlay.
    if not sorted_person_indexes:
        signals = enriched.get("student_attention_signals")
        if isinstance(signals, dict):
            signal_items = signals.values()
        elif isinstance(signals, list):
            signal_items = signals
        else:
            signal_items = []
        for order, signal in enumerate(signal_items, start=1):
            if not isinstance(signal, dict) or not signal.get("face_only"):
                continue
            face_box = safe_box(signal)
            if face_box is None:
                continue
            is_attention_candidate = bool(signal.get("attention_candidate"))
            attention_confidence = safe_unit_confidence(signal.get("attention_confidence"))
            student_candidates.append(
                {
                    "student_label": signal.get("student_label") or f"Student {order}",
                    "track_id": signal.get("track_id", order),
                    "person_confidence": None,
                    "box": face_box,
                    "phone_candidate": False,
                    "phone_confidence": None,
                    "attention_candidate": "candidate" if is_attention_candidate else "none",
                    "attention_confidence": attention_confidence,
                    "candidate_label": (
                        "Attention candidate"
                        if is_attention_candidate
                        else "Face/upper-body candidate"
                    ),
                    "reason": signal.get("reason") or "Teacher review required.",
                    "frame_quality_label": enriched.get("frame_quality_label", "unknown"),
                }
            )
    enriched["student_candidates"] = student_candidates
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
            "All results are candidates from sampled analysis and require teacher review.",
            "Drowsiness and head-down candidates require a validated pose or head-landmark model.",
            "Expression candidates require a validated model; no emotion state is inferred.",
            "A person candidate alone cannot establish emotion, attention, or behavior.",
            "Low confidence or low_quality_frame input must not produce a final judgment.",
        ],
    }
    return behavior_decision_engine.analyze_with_model_adapters(b"", enriched)
