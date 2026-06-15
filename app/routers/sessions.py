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
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "sessions/list.html",
        {
            "sessions": session_service.list_sessions(db),
            "message": message,
            "error": error,
        },
    )


@router.post("/generate-today")
async def generate_today_sessions(db: DatabaseSession = Depends(get_db)):
    created, skipped, message = session_service.generate_sessions_for_date(db)
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
