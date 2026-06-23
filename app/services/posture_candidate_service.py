"""Safe posture candidate helpers for Phase 30D.

This module turns sandbox pose-landmark summaries into cautious posture
candidates. It does not save evidence, write to the database, or make final
behavior claims.
"""

from __future__ import annotations

from typing import Any

MIN_KEYPOINT_VISIBILITY = 0.50
NOSE_SHOULDER_CLOSE_THRESHOLD = -0.08


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _landmark_ready(landmark: dict[str, Any] | None) -> bool:
    if not isinstance(landmark, dict):
        return False
    x_value = _as_float(landmark.get("x"))
    y_value = _as_float(landmark.get("y"))
    visibility = _as_float(landmark.get("visibility"))
    return (
        x_value is not None
        and y_value is not None
        and visibility is not None
        and visibility >= MIN_KEYPOINT_VISIBILITY
    )


def _key_landmarks(pose_summary: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    keypoints = pose_summary.get("key_landmarks")
    return keypoints if isinstance(keypoints, dict) else {}


def evaluate_posture_candidate(pose_summary: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one pose summary and return a safe candidate result.

    Coordinate note: MediaPipe image landmark `y` grows downward, so a nose y
    value close to or below the shoulder midpoint may indicate a leaning/head-low
    posture candidate. This is not a final sleeping or attention label.
    """

    keypoints = _key_landmarks(pose_summary)
    nose = keypoints.get("nose")
    left_shoulder = keypoints.get("left_shoulder")
    right_shoulder = keypoints.get("right_shoulder")

    required = {
        "nose": _landmark_ready(nose),
        "left_shoulder": _landmark_ready(left_shoulder),
        "right_shoulder": _landmark_ready(right_shoulder),
    }
    if not all(required.values()):
        return {
            "label": "insufficient_pose_quality",
            "confidence": 0.0,
            "safe_mode": True,
            "generated_behavior_labels": [],
            "ready_keypoints": required,
            "reason": "Nose and both shoulder landmarks must be visible before a posture candidate can be evaluated.",
        }

    nose_y = float(nose["y"])  # type: ignore[index]
    left_shoulder_y = float(left_shoulder["y"])  # type: ignore[index]
    right_shoulder_y = float(right_shoulder["y"])  # type: ignore[index]
    shoulder_mid_y = (left_shoulder_y + right_shoulder_y) / 2
    nose_to_shoulder_delta = nose_y - shoulder_mid_y

    average_visibility = _as_float(pose_summary.get("average_visibility"))
    lower_body_quality_note = None
    if average_visibility is not None and average_visibility < MIN_KEYPOINT_VISIBILITY:
        lower_body_quality_note = (
            "Average visibility is below 0.50, but head/shoulder landmarks are usable. "
            "Keep this as a candidate only."
        )

    if nose_to_shoulder_delta >= NOSE_SHOULDER_CLOSE_THRESHOLD:
        label = "possible_head_low_candidate"
        confidence = 0.55
        reason = (
            "Nose landmark is close to or below the shoulder midpoint. This may indicate a leaning/head-low posture, "
            "but it requires more frames before any alert."
        )
    else:
        label = "normal_upright_candidate"
        confidence = 0.60
        reason = "Nose landmark is clearly above the shoulder midpoint in this single image."

    return {
        "label": label,
        "confidence": confidence,
        "safe_mode": True,
        "generated_behavior_labels": [],
        "ready_keypoints": required,
        "nose_y": round(nose_y, 6),
        "shoulder_mid_y": round(shoulder_mid_y, 6),
        "nose_to_shoulder_delta": round(nose_to_shoulder_delta, 6),
        "lower_body_quality_note": lower_body_quality_note,
        "reason": reason,
    }


def evaluate_pose_result(pose_result: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a full pose sandbox result without creating final alerts."""

    status = pose_result.get("status")
    if not pose_result.get("ok"):
        return {
            "ok": False,
            "phase": "30D",
            "status": status or "pose_result_not_ok",
            "safe_mode": True,
            "generated_behavior_labels": [],
            "message": "Pose result was not successful, so posture candidate evaluation was skipped.",
        }

    if status != "completed":
        return {
            "ok": True,
            "phase": "30D",
            "status": status or "model_required",
            "safe_mode": True,
            "generated_behavior_labels": [],
            "message": "Pose model is not ready or did not complete, so no posture candidate was generated.",
        }

    pose_summaries = pose_result.get("pose_summaries")
    if not isinstance(pose_summaries, list) or not pose_summaries:
        return {
            "ok": True,
            "phase": "30D",
            "status": "pose_not_detected",
            "safe_mode": True,
            "posture_candidates": [],
            "generated_behavior_labels": [],
            "message": "No pose landmarks were detected in this image.",
        }

    candidates = [
        evaluate_posture_candidate(summary)
        for summary in pose_summaries
        if isinstance(summary, dict)
    ]
    return {
        "ok": True,
        "phase": "30D",
        "status": "completed",
        "safe_mode": True,
        "posture_candidates": candidates,
        "generated_behavior_labels": [],
        "message": "Posture candidate evaluation completed in sandbox mode only.",
    }
