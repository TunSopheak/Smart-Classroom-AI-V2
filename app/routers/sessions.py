from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.services import session_service


router = APIRouter(prefix="/sessions", tags=["sessions"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


@router.get("")
async def list_sessions(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    view: str = "today",
    session_date: str | None = None,
    status: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    closed_count = session_service.cleanup_stale_active_sessions(db)
    view = session_service.normalize_session_view(view)
    selected_date = session_service.parse_filter_date(session_date)
    selected_status = session_service.normalize_session_status(status)

    if view == "date" and selected_date is None:
        view = "today"
        error = error or "Please choose a valid date."

    if closed_count and not message:
        message = f"Previous active session(s) were automatically closed: {closed_count}."

    return templates.TemplateResponse(
        request,
        "sessions/list.html",
        {
            "sessions": session_service.list_sessions(
                db,
                view=view,
                selected_date=selected_date,
                status=selected_status,
            ),
            "filters": {
                "view": view,
                "session_date": selected_date.isoformat() if selected_date else "",
                "status": selected_status or "",
            },
            "statuses": session_service.SESSION_STATUSES,
            "filter_label": session_service.session_filter_label(view, selected_date, selected_status),
            "message": message,
            "error": error,
        },
    )


@router.post("/generate-today")
async def generate_today_sessions(db: DatabaseSession = Depends(get_db)):
    closed_count = session_service.cleanup_stale_active_sessions(db)
    created, skipped, message = session_service.generate_sessions_for_date(db)
    if closed_count:
        message = f"Previous active session(s) were automatically closed: {closed_count}. {message or ''}".strip()
    if created == 0 and skipped == 0:
        return redirect_with("/sessions", error=message or "No sessions generated.")

    return redirect_with("/sessions", message=message or "Sessions generated.")


@router.post("/{session_id}/start")
async def start_session(session_id: int, db: DatabaseSession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if session is None:
        return redirect_with("/sessions", error="Session not found.")

    updated, error = session_service.start_session(db, session)
    if error:
        return redirect_with("/sessions", error=error)

    return redirect_with("/sessions", message=f"Session {updated.title} started.")


@router.post("/{session_id}/close")
async def close_session(session_id: int, db: DatabaseSession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if session is None:
        return redirect_with("/sessions", error="Session not found.")

    updated, error = session_service.close_session(db, session)
    if error:
        return redirect_with("/sessions", error=error)

    return redirect_with("/sessions", message=f"Session {updated.title} closed.")


@router.post("/{session_id}/cancel")
async def cancel_session(session_id: int, db: DatabaseSession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if session is None:
        return redirect_with("/sessions", error="Session not found.")

    updated, error = session_service.cancel_session(db, session)
    if error:
        return redirect_with("/sessions", error=error)

    return redirect_with("/sessions", message=f"Session {updated.title} cancelled.")
