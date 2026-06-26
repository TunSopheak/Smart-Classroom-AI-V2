from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DatabaseSession

from app.ai.frame_utils import decode_base64_image
from app.ai.yolo_detector import get_yolo_detector
from app.core.config import PI_LIVE_STREAM_URL
from app.core.database import get_db
from app.services import (
    ai_service,
    behavior_detection_service,
    behavior_overlay_service,
    camera_quality_service,
    face_attendance_service,
    iot_service,
    multibehavior_model_service,
)


router = APIRouter(prefix="/ai-monitoring", tags=["ai monitoring"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def default_behavior_status(message: str | None = None) -> dict:
    """Return a safe behavior-status payload for the monitoring template."""

    status = behavior_detection_service.analyze_behavior_from_ai_result({})
    if message:
        status["message"] = message
        status["reason"] = message
    return status


def behavior_status_from_analysis(latest_analysis_state: dict | None) -> dict:
    """Build behavior status defensively so /ai-monitoring never fails on prototype data."""

    try:
        analysis = latest_analysis_state.get("analysis") if isinstance(latest_analysis_state, dict) else None
        return behavior_detection_service.analyze_behavior_from_ai_result(
            analysis if isinstance(analysis, dict) else {}
        )
    except Exception as error:  # pragma: no cover - defensive UI fallback
        return default_behavior_status(
            f"Behavior AI prototype status is temporarily unavailable: {error}"
        )


@router.get("")
async def ai_monitoring_page(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    session_id: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    selected_session, active_sessions, selection_error = ai_service.resolve_selected_session(db, session_id)
    occupancy = ai_service.occupancy_context(db, selected_session) if selected_session else None
    latest_analysis_state = iot_service.analysis_status()
    device_status = iot_service.device_status()
    behavior_status = behavior_status_from_analysis(latest_analysis_state)
    return templates.TemplateResponse(
        request,
        "ai_monitoring/index.html",
        {
            "active_session": selected_session,
            "active_sessions": active_sessions,
            "selected_session_id": str(selected_session.id) if selected_session else session_id,
            "selection_error": selection_error,
            "events": ai_service.recent_events(db, selected_session.id if selected_session else None),
            "occupancy": occupancy,
            "behavior_status": behavior_status,
            "device_status": device_status,
            "latest_analysis_state": latest_analysis_state,
            "model_capabilities": multibehavior_model_service.model_capability_status(),
            "pi_live_stream_url": PI_LIVE_STREAM_URL,
            "message": message,
            "error": error,
        },
    )


@router.post("/events/{event_type}")
async def log_ai_event(event_type: str, session_id: str | None = None, db: DatabaseSession = Depends(get_db)):
    event, error = ai_service.log_event(db, event_type, session_id)
    redirect_params = {"session_id": str(session_id)} if session_id is not None else {}
    if error:
        return redirect_with("/ai-monitoring", error=error, **redirect_params)

    return redirect_with(
        "/ai-monitoring",
        message=f"AI event logged: {event.event_type.replace('_', ' ')}.",
        session_id=str(event.session_id),
    )


@router.post("/auto-event")
async def log_auto_ai_event(session_id: str = Form(""), db: DatabaseSession = Depends(get_db)):
    event, error = ai_service.log_auto_face_detected(db, session_id)
    if error:
        return JSONResponse({"ok": False, "message": error}, status_code=400)

    return {
        "ok": True,
        "message": event.message or "Face detected by camera.",
        "event_type": event.event_type,
        "severity": event.severity,
    }


@router.post("/phone-event")
async def log_phone_usage_event(session_id: str = Form(""), db: DatabaseSession = Depends(get_db)):
    event, error, cooldown_remaining_seconds = ai_service.log_phone_usage_detected(db, session_id)
    if error:
        cooldown_active = cooldown_remaining_seconds > 0
        return JSONResponse(
            {
                "ok": False,
                "message": error,
                "cooldown_active": cooldown_active,
                "cooldown_remaining_seconds": cooldown_remaining_seconds,
            },
            status_code=429 if cooldown_active else 400,
        )

    return {
        "ok": True,
        "message": "Phone-use candidate logged for teacher review. Waiting for cooldown.",
        "event_type": event.event_type,
        "severity": event.severity,
        "snapshot_url": ai_service.event_snapshot_url(event),
        "cooldown_seconds": ai_service.PHONE_USAGE_COOLDOWN_SECONDS,
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
    }


@router.post("/attention-event")
async def log_attention_warning_event(session_id: str = Form(""), db: DatabaseSession = Depends(get_db)):
    event, error, cooldown_remaining_seconds = ai_service.log_attention_warning_detected(db, session_id)
    if error:
        cooldown_active = cooldown_remaining_seconds > 0
        return JSONResponse(
            {
                "ok": False,
                "message": error,
                "cooldown_active": cooldown_active,
                "cooldown_remaining_seconds": cooldown_remaining_seconds,
            },
            status_code=429 if cooldown_active else 400,
        )

    return {
        "ok": True,
        "message": "Attention candidate logged for teacher review. Waiting for cooldown.",
        "event_type": event.event_type,
        "severity": event.severity,
        "snapshot_url": ai_service.event_snapshot_url(event),
        "cooldown_seconds": ai_service.ATTENTION_WARNING_COOLDOWN_SECONDS,
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
    }


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
    result = behavior_overlay_service.enrich_analysis_for_behavior_overlay(
        object_analysis

    )
    result.update(
        {
            "analysis_source": "computer_camera",
            "ai_mode": "advanced_safe_mode",
            "frame_type": "browser_camera_sampled_frame",
            "result_type": "candidate_for_review",
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
    event_messages = []

    if result["available"]:
        result["message"] = (
            "Advanced AI Safe Mode completed sampled computer camera analysis. "
            "Candidates require teacher review."
        )
        occupancy, occupancy_error = ai_service.update_detected_count(db, active_session.id, result["person_count"])
        if occupancy_error:
            event_messages.append(occupancy_error)
        elif occupancy:
            result["occupancy"] = occupancy

        if result["phone_count"] > 0:
            phone_event, phone_error, cooldown_remaining_seconds = ai_service.log_phone_usage_detected(
                db,
                active_session.id,
                snapshot_image_bytes=image_bytes,
            )
            if phone_error:
                event_messages.append(phone_error)
                result["phone_cooldown_remaining_seconds"] = cooldown_remaining_seconds
            else:
                snapshot_url = ai_service.event_snapshot_url(phone_event)
                event_messages.append("Phone-use candidate logged for teacher review. Snapshot saved. Waiting for cooldown.")
                result["phone_cooldown_seconds"] = cooldown_remaining_seconds
                result["snapshot_url"] = snapshot_url
                result["phone_event_id"] = phone_event.id if phone_event else None

    try:
        face_attendance = face_attendance_service.mark_face_attendance(
            db,
            active_session.id,
            image_bytes,
        )
        result["face_attendance"] = face_attendance
        if face_attendance.get("attendance"):
            saved_count = sum(1 for item in face_attendance["attendance"] if not item.get("duplicate"))
            duplicate_count = sum(1 for item in face_attendance["attendance"] if item.get("duplicate"))
            if saved_count:
                event_messages.append(f"Face attendance saved for {saved_count} student(s).")
            if duplicate_count:
                event_messages.append(f"Duplicate face attendance skipped for {duplicate_count} student(s).")
        if face_attendance.get("unknown_face_count"):
            event_messages.append(f"Unknown face count: {face_attendance['unknown_face_count']}.")
    except Exception as error:  # pragma: no cover - demo route safety
        result["face_attendance"] = {
            "available": False,
            "message": f"Face attendance unavailable: {error}",
            "faces": [],
            "recognized_count": 0,
            "unknown_face_count": 0,
            "attendance": [],
        }
        event_messages.append("Face attendance unavailable.")

    result["ok"] = True
    result["event_message"] = " ".join(event_messages)
    return result


@router.post("/occupancy")
async def update_occupancy_count(
    session_id: str = Form(""),
    detected_count: int = Form(...),
    db: DatabaseSession = Depends(get_db),
):
    occupancy, error = ai_service.update_detected_count(db, session_id, detected_count)
    if error:
        return JSONResponse({"ok": False, "message": error}, status_code=400)
    return {"ok": True, "occupancy": occupancy}


@router.get("/occupancy/status")
async def occupancy_status(session_id: str = "", db: DatabaseSession = Depends(get_db)):
    occupancy, error = ai_service.occupancy_context_for_session_id(db, session_id)
    if error:
        return JSONResponse({"ok": False, "message": error}, status_code=400)
    return {"ok": True, "occupancy": occupancy}


