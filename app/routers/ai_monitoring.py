from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.services import ai_service


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
