from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.schemas.academic import AttendanceScan
from app.services import academic_service, attendance_service, session_service


router = APIRouter(prefix="/attendance", tags=["attendance"])
qr_router = APIRouter(tags=["attendance"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


@router.get("")
async def attendance_history(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    student_search: str | None = None,
    status: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    selected_class_group_id = optional_int(class_group_id)
    selected_session_id = optional_int(session_id)

    return templates.TemplateResponse(
        request,
        "attendance/list.html",
        {
            "records": attendance_service.list_attendance_records(
                db,
                class_group_id=selected_class_group_id,
                session_id=selected_session_id,
                student_search=student_search,
                status=status,
            ),
            "classes": academic_service.list_classes(db),
            "sessions": session_service.list_sessions(db, view="all"),
            "statuses": ["present", "late", "absent", "permission"],
            "filters": {
                "class_group_id": selected_class_group_id or "",
                "session_id": selected_session_id or "",
                "student_search": student_search or "",
                "status": status or "",
            },
            "message": message,
            "error": error,
        },
    )


@router.get("/scan")
async def scan_form(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "attendance/scan.html",
        {
            "active_sessions": attendance_service.list_active_sessions(db),
            "message": message,
            "error": error,
            "form": {},
        },
    )


@router.post("/scan")
async def scan_student(
    request: Request,
    student_code: str = Form(""),
    db: DatabaseSession = Depends(get_db),
):
    form = {"student_code": student_code.strip()}
    try:
        payload = AttendanceScan(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "attendance/scan.html",
            {
                "active_sessions": attendance_service.list_active_sessions(db),
                "message": None,
                "error": "Enter a student ID or QR value.",
                "form": form,
            },
            status_code=400,
        )

    attendance, error = attendance_service.scan_student(db, payload.student_code)
    if error:
        return templates.TemplateResponse(
            request,
            "attendance/scan.html",
            {
                "active_sessions": attendance_service.list_active_sessions(db),
                "message": None,
                "error": error,
                "form": form,
            },
            status_code=400,
        )

    return redirect_with(
        "/attendance/scan",
        message=f"{attendance.student.student_code} marked {attendance.status}.",
    )


@qr_router.get("/qr-scanner")
async def qr_scanner_alias(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return await scan_form(request, db, message, error)


@qr_router.post("/qr-scanner")
async def qr_scanner_post_alias(
    request: Request,
    student_code: str = Form(""),
    db: DatabaseSession = Depends(get_db),
):
    return await scan_student(request, student_code, db)
