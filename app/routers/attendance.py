from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.schemas.academic import AttendanceScan
from app.services import academic_service, attendance_service, report_service, session_service


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


def attendance_filter_context(
    db: DatabaseSession,
    class_group_id: str | None,
    session_id: str | None,
    student_search: str | None,
    status: str | None,
):
    selected_class_group_id = optional_int(class_group_id)
    selected_session_id = optional_int(session_id)
    clean_status = status or None
    clean_search = student_search or None

    records = attendance_service.list_attendance_records(
        db,
        class_group_id=selected_class_group_id,
        session_id=selected_session_id,
        student_search=clean_search,
        status=clean_status,
    )

    class_label = None
    session_label = None
    if selected_class_group_id:
        class_group = academic_service.get_class(db, selected_class_group_id)
        if class_group:
            class_label = f"{class_group.class_code} - {class_group.name}"
    if selected_session_id:
        session = session_service.get_session(db, selected_session_id)
        if session:
            session_label = f"{session.session_date.strftime('%Y-%m-%d')} | {session.subject.code} | {session.class_group.class_code}"

    filters = {
        "class_group_id": selected_class_group_id or "",
        "session_id": selected_session_id or "",
        "student_search": clean_search or "",
        "status": clean_status or "",
        "class_group_label": class_label,
        "session_label": session_label,
    }
    return records, filters


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
    records, filters = attendance_filter_context(db, class_group_id, session_id, student_search, status)

    return templates.TemplateResponse(
        request,
        "attendance/list.html",
        {
            "records": records,
            "classes": academic_service.list_classes(db),
            "sessions": session_service.list_sessions(db, view="all"),
            "statuses": ["present", "late", "absent", "permission"],
            "filters": filters,
            "message": message,
            "error": error,
        },
    )


@router.get("/export.csv")
async def export_attendance_csv(
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    student_search: str | None = None,
    status: str | None = None,
):
    records, _ = attendance_filter_context(db, class_group_id, session_id, student_search, status)
    return Response(
        content=report_service.build_attendance_csv(records),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="attendance-report.csv"'},
    )


@router.get("/export.pdf")
async def export_attendance_pdf(
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    student_search: str | None = None,
    status: str | None = None,
):
    records, filters = attendance_filter_context(db, class_group_id, session_id, student_search, status)
    try:
        pdf = report_service.build_attendance_pdf(records, filters)
    except ImportError:
        return redirect_with(
            "/attendance",
            error="PDF export is unavailable. Install reportlab from requirements.txt.",
        )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="attendance-report.pdf"'},
    )


@router.get("/scan")
async def scan_form(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    session_id: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    selected_session, active_sessions, selection_error = attendance_service.resolve_scan_session(db, session_id)
    return templates.TemplateResponse(
        request,
        "attendance/scan.html",
        {
            "active_sessions": active_sessions,
            "selected_session": selected_session,
            "selected_session_id": str(selected_session.id) if selected_session else session_id,
            "selection_error": selection_error,
            "message": message,
            "error": error,
            "form": {},
        },
    )


@router.post("/scan")
async def scan_student(
    request: Request,
    student_code: str = Form(""),
    session_id: str = Form(""),
    db: DatabaseSession = Depends(get_db),
):
    form = {"student_code": student_code.strip(), "session_id": session_id.strip()}
    selected_session, active_sessions, selection_error = attendance_service.resolve_scan_session(db, form["session_id"])
    try:
        payload = AttendanceScan(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "attendance/scan.html",
            {
                "active_sessions": active_sessions,
                "selected_session": selected_session,
                "selected_session_id": str(selected_session.id) if selected_session else form["session_id"],
                "selection_error": selection_error,
                "message": None,
                "error": "Enter a student ID or QR value.",
                "form": form,
            },
            status_code=400,
        )

    attendance, error = attendance_service.scan_student(db, payload.student_code, session_id=form["session_id"])
    if error:
        return templates.TemplateResponse(
            request,
            "attendance/scan.html",
            {
                "active_sessions": active_sessions,
                "selected_session": selected_session,
                "selected_session_id": str(selected_session.id) if selected_session else form["session_id"],
                "selection_error": selection_error,
                "message": None,
                "error": error,
                "form": form,
            },
            status_code=400,
        )

    return redirect_with(
        "/attendance/scan",
        message=f"{attendance.student.student_code} marked {attendance.status}.",
        session_id=str(attendance.session_id),
    )


@qr_router.get("/qr-scanner")
async def qr_scanner_alias(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    session_id: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    return await scan_form(request, db, session_id, message, error)


@qr_router.post("/qr-scanner")
async def qr_scanner_post_alias(
    request: Request,
    student_code: str = Form(""),
    session_id: str = Form(""),
    db: DatabaseSession = Depends(get_db),
):
    return await scan_student(request, student_code, session_id, db)
