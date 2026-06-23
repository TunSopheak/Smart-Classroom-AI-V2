from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DatabaseSession

from app.ai.frame_utils import decode_base64_image
from app.ai.yolo_detector import get_yolo_detector
from app.core.config import PI_LIVE_STREAM_URL
from app.core.database import get_db
from app.services import ai_service, behavior_detection_service, iot_service


router = APIRouter(prefix="/ai-monitoring", tags=["ai monitoring"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


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
    behavior_status = behavior_detection_service.analyze_behavior_from_ai_result(
        latest_analysis_state.get("analysis") or {}
    )
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
        "message": "Phone warning logged. Waiting for cooldown.",
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
        "message": "Attention warning logged. Waiting for cooldown.",
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

    result = get_yolo_detector().analyze(image_bytes)
    event_messages = []

    if result["available"]:
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
                event_messages.append("Phone warning logged. Snapshot saved. Waiting for cooldown.")
                result["phone_cooldown_seconds"] = cooldown_remaining_seconds
                result["snapshot_url"] = snapshot_url
                result["phone_event_id"] = phone_event.id if phone_event else None

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
