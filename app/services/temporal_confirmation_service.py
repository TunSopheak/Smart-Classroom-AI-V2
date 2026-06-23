"""Phase 30F temporal confirmation helpers.

This module evaluates posture candidates across multiple frames before anything
could be considered for teacher review. It is intentionally conservative and
research-only: it does not write evidence, update the database, or create live
dashboard alerts.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

DEFAULT_TARGET_LABEL = "possible_head_low_candidate"
DEFAULT_WINDOW_SIZE = 5
DEFAULT_MIN_MATCHES = 3
DEFAULT_MIN_CONFIDENCE = 0.50


def normalize_candidate(candidate: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe candidate with stable keys."""

    source = candidate if isinstance(candidate, dict) else {}
    label = str(source.get("label") or "none")
    try:
        confidence = float(source.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "label": label,
        "confidence": confidence,
        "safe_mode": True,
        "generated_behavior_labels": [],
    }


def extract_first_candidate(frame_result: dict[str, Any]) -> dict[str, Any]:
    """Extract the first posture candidate from a Phase 30D frame result."""

    if not isinstance(frame_result, dict):
        return normalize_candidate(None)

    # Accept direct candidate dictionaries for simple unit tests and CLI usage.
    if "label" in frame_result:
        return normalize_candidate(frame_result)

    candidate_result = frame_result.get("candidate_result")
    if not isinstance(candidate_result, dict):
        return normalize_candidate(None)

    candidates = candidate_result.get("posture_candidates")
    if not isinstance(candidates, list) or not candidates:
        return normalize_candidate(None)

    first_candidate = candidates[0]
    return normalize_candidate(first_candidate if isinstance(first_candidate, dict) else None)


def evaluate_temporal_confirmation(
    frame_results: list[dict[str, Any]],
    target_label: str = DEFAULT_TARGET_LABEL,
    window_size: int = DEFAULT_WINDOW_SIZE,
    min_matches: int = DEFAULT_MIN_MATCHES,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Evaluate whether a candidate is repeated enough for teacher review.

    This function returns a research status only. Even when a candidate is
    confirmed, the result says `confirmed_for_review` and still keeps dashboard
    alerts/evidence disabled.
    """

    safe_window_size = max(1, int(window_size or DEFAULT_WINDOW_SIZE))
    safe_min_matches = max(1, int(min_matches or DEFAULT_MIN_MATCHES))
    safe_min_confidence = float(min_confidence or DEFAULT_MIN_CONFIDENCE)

    recent_frames = frame_results[-safe_window_size:] if isinstance(frame_results, list) else []
    candidates = [extract_first_candidate(frame) for frame in recent_frames]

    confident_target_matches = [
        candidate
        for candidate in candidates
        if candidate["label"] == target_label and candidate["confidence"] >= safe_min_confidence
    ]
    labels = [candidate["label"] for candidate in candidates]
    label_counts = dict(Counter(labels))

    if not candidates:
        status = "no_frames"
        confirmed = False
        reason = "No candidate frames were provided."
    elif len(candidates) < safe_min_matches:
        status = "needs_more_frames"
        confirmed = False
        reason = "More frames are required before any temporal decision."
    elif len(confident_target_matches) >= safe_min_matches:
        status = "confirmed_for_review"
        confirmed = True
        reason = (
            "The same posture candidate repeated across multiple frames with enough confidence. "
            "This is still for teacher review only, not an automatic alert."
        )
    elif target_label in labels:
        status = "unstable_candidate"
        confirmed = False
        reason = "The target candidate appeared, but not consistently enough across the recent frame window."
    elif "insufficient_pose_quality" in labels:
        status = "insufficient_pose_quality"
        confirmed = False
        reason = "Pose landmarks were not reliable enough for temporal confirmation."
    elif "model_required" in labels:
        status = "model_required"
        confirmed = False
        reason = "The real pose model is required before temporal confirmation can run."
    elif "pose_not_detected" in labels or "none" in labels:
        status = "pose_not_detected"
        confirmed = False
        reason = "No usable posture candidate was detected in the recent frames."
    else:
        status = "no_target_candidate"
        confirmed = False
        reason = "Recent frames did not contain the target posture candidate."

    return {
        "ok": True,
        "phase": "30F",
        "safe_mode": True,
        "status": status,
        "target_label": target_label,
        "window_size": safe_window_size,
        "min_matches": safe_min_matches,
        "min_confidence": safe_min_confidence,
        "frames_evaluated": len(candidates),
        "target_matches": len(confident_target_matches),
        "label_counts": label_counts,
        "confirmed_for_review": confirmed,
        "should_show_dashboard_alert": False,
        "should_save_evidence": False,
        "should_update_database": False,
        "generated_behavior_labels": [],
        "message": reason,
    }
