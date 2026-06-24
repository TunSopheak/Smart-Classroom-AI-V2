"""Conservative foundation for future landmark-backed behavior monitoring."""

from datetime import datetime, timedelta, timezone

from app.core.config import (
    BEHAVIOR_ALERTS_ENABLED,
    BEHAVIOR_REQUIRED_SAMPLES,
    HEAD_DOWN_EVENT_COOLDOWN_SECONDS,
)


PROTOTYPE_MIN_CONFIDENCE = 0.75
LANDMARK_REQUIREMENT_MESSAGE = (
    "Model required: validated pose/head landmarks are needed for a head-down "
    "candidate. A person candidate alone is not behavioral evidence."
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def safe_confidence(value) -> float | None:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, confidence))


def safe_count(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def analyze_behavior_from_ai_result(analysis: dict) -> dict:
    analysis = analysis if isinstance(analysis, dict) else {}
    signals = analysis.get("behavior_signals")
    signals = signals if isinstance(signals, dict) else {}
    person_count = safe_count(analysis.get("person_count"))

    pose_available = bool(signals.get("pose_landmarks_available"))
    head_orientation_available = bool(
        signals.get("head_orientation_available")
    )
    head_down_confidence = safe_confidence(signals.get("head_down_confidence"))
    inattentive_confidence = safe_confidence(
        signals.get("inattentive_confidence")
    )

    possible_head_down = bool(
        person_count
        and pose_available
        and signals.get("possible_head_down")
        and head_down_confidence is not None
        and head_down_confidence >= PROTOTYPE_MIN_CONFIDENCE
    )
    possible_inattentive = bool(
        person_count
        and head_orientation_available
        and signals.get("possible_inattentive")
        and inattentive_confidence is not None
        and inattentive_confidence >= PROTOTYPE_MIN_CONFIDENCE
    )
    supported = pose_available or head_orientation_available
    confidence_candidates = [
        confidence
        for confidence, active in (
            (head_down_confidence, possible_head_down),
            (inattentive_confidence, possible_inattentive),
        )
        if active and confidence is not None
    ]

    if not person_count:
        reason = "No person is available in the latest sample for behavior evaluation."
    elif not supported:
        reason = LANDMARK_REQUIREMENT_MESSAGE
    elif possible_head_down:
        reason = "Sampled landmark analysis produced a head-down candidate; teacher review required."
    elif possible_inattentive:
        reason = "Sampled head-orientation analysis produced an attention candidate; teacher review required."
    else:
        reason = "No candidate met the prototype threshold in the latest sampled analysis."

    return {
        "behavior_supported": supported,
        "behavior_stage": "prototype",
        "review_requirement": "teacher review required",
        "alerts_enabled": BEHAVIOR_ALERTS_ENABLED,
        "person_count": person_count,
        "pose_landmarks_available": pose_available,
        "head_orientation_available": head_orientation_available,
        "possible_head_down": possible_head_down,
        "possible_inattentive": possible_inattentive,
        "confidence": max(confidence_candidates) if confidence_candidates else None,
        "head_down_confidence": head_down_confidence,
        "inattentive_confidence": inattentive_confidence,
        "reason": reason,
        "message": reason,
        "required_consecutive_samples": BEHAVIOR_REQUIRED_SAMPLES,
        "current_consecutive_count": 0,
        "alert_ready": False,
    }


def advance_behavior_state(result: dict, previous_state: dict | None = None) -> dict:
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    head_down_count = (
        int(previous_state.get("head_down_consecutive_count") or 0) + 1
        if result.get("possible_head_down")
        else 0
    )
    inattentive_count = (
        int(previous_state.get("inattentive_consecutive_count") or 0) + 1
        if result.get("possible_inattentive")
        else 0
    )
    return {
        "head_down_consecutive_count": head_down_count,
        "inattentive_consecutive_count": inattentive_count,
        "last_head_down_event_at": previous_state.get("last_head_down_event_at"),
        "last_inattentive_event_at": previous_state.get(
            "last_inattentive_event_at"
        ),
    }


def cooldown_ready(last_event_at, now: datetime) -> bool:
    if isinstance(last_event_at, str):
        try:
            last_event_at = datetime.fromisoformat(last_event_at)
        except ValueError:
            last_event_at = None
    if not isinstance(last_event_at, datetime):
        return True
    return now - last_event_at >= timedelta(
        seconds=HEAD_DOWN_EVENT_COOLDOWN_SECONDS
    )


def evaluate_behavior_event(
    snapshot: dict,
    image_bytes: bytes,
    analysis: dict,
    previous_state: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Evaluate temporal behavior state without saving evidence or database rows."""

    result = analyze_behavior_from_ai_result(analysis)
    state = advance_behavior_state(result, previous_state)
    current_time = now or utc_now()
    event = None
    evidence_input_available = bool(
        image_bytes and isinstance(snapshot, dict) and snapshot.get("filename")
    )

    if (
        BEHAVIOR_ALERTS_ENABLED
        and result.get("behavior_supported")
        and evidence_input_available
    ):
        if (
            state["head_down_consecutive_count"] >= BEHAVIOR_REQUIRED_SAMPLES
            and cooldown_ready(state.get("last_head_down_event_at"), current_time)
        ):
            event = {
                "event_type": "possible_head_down",
                "title": "Head-down candidate for review",
                "reason": result["reason"],
                "confidence": result["head_down_confidence"],
                "source_snapshot_filename": snapshot.get("filename"),
                "created_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "required_consecutive_samples": BEHAVIOR_REQUIRED_SAMPLES,
                "evidence_bytes_available": bool(image_bytes),
            }
            state["last_head_down_event_at"] = current_time
            state["head_down_consecutive_count"] = 0
        elif (
            state["inattentive_consecutive_count"] >= BEHAVIOR_REQUIRED_SAMPLES
            and cooldown_ready(
                state.get("last_inattentive_event_at"),
                current_time,
            )
        ):
            event = {
                "event_type": "possible_inattentive",
                "title": "Attention candidate for review",
                "reason": result["reason"],
                "confidence": result["inattentive_confidence"],
                "source_snapshot_filename": snapshot.get("filename"),
                "created_at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "required_consecutive_samples": BEHAVIOR_REQUIRED_SAMPLES,
                "evidence_bytes_available": bool(image_bytes),
            }
            state["last_inattentive_event_at"] = current_time
            state["inattentive_consecutive_count"] = 0

    current_count = max(
        state["head_down_consecutive_count"],
        state["inattentive_consecutive_count"],
    )
    result["current_consecutive_count"] = current_count
    result["alert_ready"] = event is not None
    return {"status": result, "state": state, "event": event}
