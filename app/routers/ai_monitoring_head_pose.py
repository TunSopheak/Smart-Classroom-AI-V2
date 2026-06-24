from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DatabaseSession

from app.ai.frame_utils import decode_base64_image
from app.ai.yolo_detector import get_yolo_detector
from app.core.database import get_db
from app.services import (
    ai_service,
    behavior_overlay_service,
    camera_quality_service,
    head_pose_attention_service,
)

router = APIRouter(prefix="/ai-monitoring", tags=["ai monitoring head pose"])


def candidate_summary(result: dict) -> str:
    candidates = result.get("student_candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    parts: list[str] = []
    for candidate in candidates[:5]:
        if not isinstance(candidate, dict):
            continue
        label = candidate.get("student_label") or "Student"
        status = candidate.get("attention_candidate")
        if status == "candidate":
            parts.append(f"{label}: attention candidate for teacher review")
        elif candidate.get("phone_candidate"):
            parts.append(f"{label}: phone-use candidate")
        else:
            parts.append(f"{label}: no attention candidate")
    return "Per-student candidate review: " + "; ".join(parts)


@router.post("/analyze-frame")
async def analyze_frame(
    session_id: str = Form(""),
    frame_data: str = Form(""),
    frame_file: UploadFile | None = File(None),
    db: DatabaseSession = Depends(get_db),
):
    active_session, session_error = ai_service.get_session_for_event(db, session_id)
    if session_error:
        return JSONResponse({"ok": False, "message": session_error}, status_code=400)

    image_bytes = await frame_file.read() if frame_file else decode_base64_image(frame_data)
    if image_bytes is None:
        return JSONResponse(
            {"ok": False, "message": "Camera frame could not be read. Please restart the camera and try again."},
            status_code=400,
        )

    frame_quality = camera_quality_service.evaluate_live_frame_quality(image_bytes)
    object_analysis = get_yolo_detector().analyze(image_bytes)
    object_analysis.update(frame_quality)
    head_pose = head_pose_attention_service.analyze_student_attention_candidates(
        image_bytes,
        object_analysis.get("detections", []),
        str(active_session.id),
    )
    object_analysis["head_pose"] = head_pose
    object_analysis["student_attention_signals"] = head_pose.get("student_attention_signals", {})

    result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(object_analysis)
    result.update(
        {
            "analysis_source": "computer_camera",
            "ai_mode": "advanced_safe_mode_head_pose_candidate",
            "frame_type": "browser_camera_sampled_frame",
            "result_type": "candidate_for_review",
            "head_pose_status": head_pose.get("status"),
            "head_pose_available": head_pose.get("available"),
        }
    )
    confidences = [
        float(detection.get("confidence") or 0)
        for detection in result.get("detections", [])
        if isinstance(detection, dict)
    ]
    result["latest_confidence"] = max(confidences) if confidences else None
    result["candidate_warning"] = (
        "Low confidence candidate: teacher review required."
        if confidences and result["latest_confidence"] < 0.5
        else ""
    )
    result["warnings"] = [
        warning
        for warning in (
            result.get("frame_quality_warning"),
            result.get("candidate_warning"),
        )
        if warning
    ]

    event_messages: list[str] = []
    if result.get("available"):
        result["message"] = (
            "Advanced AI Safe Mode completed sampled computer camera analysis. "
            "Head-pose outputs are candidates for teacher review."
        )
        occupancy, occupancy_error = ai_service.update_detected_count(
            db,
            active_session.id,
            result["person_count"],
        )
        if occupancy_error:
            event_messages.append(occupancy_error)
        elif occupancy:
            result["occupancy"] = occupancy

        summary = candidate_summary(result)
        if summary:
            event_messages.append(summary)

        if result.get("phone_count", 0) > 0:
            phone_event, phone_error, cooldown_remaining_seconds = ai_service.log_phone_usage_detected(
                db,
                active_session.id,
                snapshot_image_bytes=image_bytes,
            )
            if phone_error:
                event_messages.append(phone_error)
                result["phone_cooldown_remaining_seconds"] = cooldown_remaining_seconds
            else:
                result["snapshot_url"] = ai_service.event_snapshot_url(phone_event)
                result["phone_cooldown_seconds"] = cooldown_remaining_seconds
                result["phone_event_id"] = phone_event.id if phone_event else None
                event_messages.append("Phone-use candidate logged for teacher review. Snapshot saved.")

    result["ok"] = True
    result["event_message"] = " ".join(event_messages)
    return result
