"""Model-adapter plan for future multi-behavior and emotion recognition.

The current project uses object detection first. This module prepares a safe
contract for future pose, head-orientation, and face-emotion models without
pretending those models are active today.
"""

from __future__ import annotations

from copy import deepcopy


MODEL_REQUIREMENTS: dict[str, dict] = {
    "normal_sitting": {
        "label": "Normal Sitting",
        "group": "posture",
        "required_models": ["object_detector"],
        "active": True,
        "risk": "low",
        "color": "#2dd4bf",
        "description": "Basic person monitoring from the current object detector.",
    },
    "possible_phone_usage": {
        "label": "Possible Phone Usage",
        "group": "object_behavior",
        "required_models": ["object_detector"],
        "active": True,
        "risk": "high",
        "color": "#ef4444",
        "description": "Phone-like object appears near a detected person.",
    },
    "possible_head_down": {
        "label": "Possible Head Down",
        "group": "pose_behavior",
        "required_models": ["pose_model", "head_landmark_model", "temporal_smoothing"],
        "active": False,
        "risk": "high",
        "color": "#ef4444",
        "description": "Needs pose/head landmarks and repeated confirmation before activation.",
    },
    "looking_around": {
        "label": "Looking Around",
        "group": "attention_behavior",
        "required_models": ["face_orientation_model", "temporal_smoothing"],
        "active": False,
        "risk": "warning",
        "color": "#a855f7",
        "description": "Needs head direction or face orientation over time.",
    },
    "sleepy_drowsy": {
        "label": "Sleepy / Drowsy",
        "group": "face_state",
        "required_models": ["face_landmark_model", "eye_state_model", "temporal_smoothing"],
        "active": False,
        "risk": "warning",
        "color": "#f97316",
        "description": "Needs eye/head landmarks and repeated confirmation.",
    },
    "happy_smile": {
        "label": "Happy / Smile",
        "group": "emotion",
        "required_models": ["face_emotion_model"],
        "active": False,
        "risk": "low",
        "color": "#22c55e",
        "description": "Needs a validated face-emotion model.",
    },
    "laughing": {
        "label": "Laughing",
        "group": "emotion",
        "required_models": ["face_emotion_model", "temporal_smoothing"],
        "active": False,
        "risk": "low",
        "color": "#22c55e",
        "description": "Needs a validated face-emotion model and classroom testing.",
    },
    "sad_tired": {
        "label": "Sad / Tired",
        "group": "emotion",
        "required_models": ["face_emotion_model"],
        "active": False,
        "risk": "warning",
        "color": "#64748b",
        "description": "Needs a validated face-emotion model; should be used carefully.",
    },
}

ACTIVE_MODEL_ADAPTERS = {
    "object_detector": True,
    "pose_model": False,
    "head_landmark_model": False,
    "face_orientation_model": False,
    "face_landmark_model": False,
    "eye_state_model": False,
    "face_emotion_model": False,
    "temporal_smoothing": False,
}


def model_capability_status() -> dict:
    """Return a UI-friendly status for available and future behavior models."""

    catalog = []
    for behavior_key, details in MODEL_REQUIREMENTS.items():
        required = details["required_models"]
        ready = all(ACTIVE_MODEL_ADAPTERS.get(model, False) for model in required)
        catalog.append(
            {
                "behavior": behavior_key,
                "label": details["label"],
                "group": details["group"],
                "risk": details["risk"],
                "color": details["color"],
                "active": bool(details["active"] and ready),
                "implemented": bool(details["active"]),
                "model_ready": ready,
                "required_models": required,
                "missing_models": [model for model in required if not ACTIVE_MODEL_ADAPTERS.get(model, False)],
                "description": details["description"],
            }
        )

    return {
        "schema_version": "multi-behavior-model-plan-v1",
        "object_detector_active": True,
        "pose_model_active": False,
        "emotion_model_active": False,
        "tracking_active": False,
        "temporal_smoothing_active": False,
        "safe_mode": True,
        "message": "Object-based behavior overlay is active. Pose, head, and emotion models are planned, not active.",
        "catalog": catalog,
    }


def attach_candidate_model_fields(analysis: dict | None) -> dict:
    """Attach future-model metadata without changing detection decisions."""

    if not isinstance(analysis, dict):
        return {}

    enriched = deepcopy(analysis)
    detections = enriched.get("detections") if isinstance(enriched.get("detections"), list) else []
    capabilities = model_capability_status()

    for detection in detections:
        if not isinstance(detection, dict):
            continue
        detection.setdefault("attention_label", "Monitoring")
        detection.setdefault("emotion_label", "Model Required")
        detection.setdefault("posture_label", "Model Required")
        detection.setdefault("model_status", "object_model_only")
        detection.setdefault(
            "future_behavior_candidates",
            [
                "possible_head_down",
                "looking_around",
                "sleepy_drowsy",
                "happy_smile",
                "laughing",
                "sad_tired",
            ],
        )
        detection.setdefault(
            "requires_model",
            ["pose_model", "head_landmark_model", "face_emotion_model", "temporal_smoothing"],
        )

    enriched["detections"] = detections
    enriched["model_capabilities"] = capabilities
    return enriched
