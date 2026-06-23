from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.services import (
    academic_service,
    ai_service,
    iot_event_service,
    report_service,
    session_service,
)


router = APIRouter(prefix="/ai-events", tags=["ai events"])
reports_router = APIRouter(tags=["ai reports"])
templates = Jinja2Templates(directory="app/templates")

SEVERITIES = ["info", "warning", "critical"]


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def optional_date(value: str | None):
    if value is None or value.strip() == "":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def ai_event_filter_context(
    db: DatabaseSession,
    class_group_id: str | None,
    session_id: str | None,
    subject_id: str | None,
    teacher_id: str | None,
    event_type: str | None,
    severity: str | None,
    selected_date: str | None,
):
    date_value = date.today().isoformat() if selected_date is None else selected_date
    clean_event_type = event_type if event_type in ai_service.EVENTS else None
    clean_severity = severity if severity in SEVERITIES else None
    selected_class_group_id = optional_int(class_group_id)
    selected_session_id = optional_int(session_id)
    selected_subject_id = optional_int(subject_id)
    selected_teacher_id = optional_int(teacher_id)
    parsed_date = optional_date(date_value)

    events = ai_service.list_ai_events(
        db,
        class_group_id=selected_class_group_id,
        session_id=selected_session_id,
        subject_id=selected_subject_id,
        teacher_id=selected_teacher_id,
        event_type=clean_event_type,
        severity=clean_severity,
        detected_date=parsed_date,
    )

    filters = {
        "class_group_id": selected_class_group_id or "",
        "session_id": selected_session_id or "",
        "subject_id": selected_subject_id or "",
        "teacher_id": selected_teacher_id or "",
        "event_type": clean_event_type or "",
        "severity": clean_severity or "",
        "date": date_value or "",
    }

    if selected_class_group_id:
        class_group = academic_service.get_class(db, selected_class_group_id)
        if class_group:
            filters["class_group_label"] = f"{class_group.class_code} - {class_group.name}"
    if selected_session_id:
        session = session_service.get_session(db, selected_session_id)
        if session:
            filters["session_label"] = f"{session.session_date.strftime('%Y-%m-%d')} | {session.subject.code} | {session.class_group.class_code}"
    if selected_subject_id:
        subject = academic_service.get_subject(db, selected_subject_id)
        if subject:
            filters["subject_label"] = f"{subject.code} - {subject.name}"
    if selected_teacher_id:
        teacher = academic_service.get_teacher(db, selected_teacher_id)
        if teacher:
            filters["teacher_label"] = f"{teacher.teacher_code} - {teacher.first_name} {teacher.last_name}"

    return events, filters


def export_query(filters: dict) -> str:
    keys = ["class_group_id", "session_id", "subject_id", "teacher_id", "event_type", "severity", "date"]
    return urlencode({key: filters.get(key, "") for key in keys})


def has_explicit_filter(*values: str | None) -> bool:
    return any(value is not None and value.strip() != "" for value in values)


@router.get("")
async def list_ai_events(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    subject_id: str | None = None,
    teacher_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    date: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    events, filters = ai_event_filter_context(
        db,
        class_group_id,
        session_id,
        subject_id,
        teacher_id,
        event_type,
        severity,
        date,
    )
    return templates.TemplateResponse(
        request,
        "ai_reports/list.html",
        {
            "events": events,
            "summary": ai_service.ai_event_summary(events),
            "filters": filters,
            "export_query": export_query(filters),
            "classes": academic_service.list_classes(db),
            "sessions": session_service.list_sessions(db, view="all"),
            "subjects": academic_service.list_subjects(db),
            "teachers": academic_service.list_teachers(db),
            "event_types": list(ai_service.EVENTS.keys()),
            "severities": SEVERITIES,
            "evidence_status": iot_event_service.event_storage_status(),
            "report_page_path": request.url.path,
            "message": message,
            "error": error,
        },
    )


@reports_router.get("/ai-reports")
async def list_ai_reports(
    request: Request,
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    subject_id: str | None = None,
    teacher_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    date: str | None = None,
    message: str | None = None,
    error: str | None = None,
):
    return await list_ai_events(
        request=request,
        db=db,
        class_group_id=class_group_id,
        session_id=session_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
        event_type=event_type,
        severity=severity,
        date=date,
        message=message,
        error=error,
    )


@router.get("/export.csv")
async def export_ai_events_csv(
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    subject_id: str | None = None,
    teacher_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    date: str | None = None,
):
    events, _ = ai_event_filter_context(db, class_group_id, session_id, subject_id, teacher_id, event_type, severity, date)
    return Response(
        content=report_service.build_ai_events_csv(events),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ai-event-report.csv"'},
    )


@router.get("/export.pdf")
async def export_ai_events_pdf(
    db: DatabaseSession = Depends(get_db),
    class_group_id: str | None = None,
    session_id: str | None = None,
    subject_id: str | None = None,
    teacher_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    date: str | None = None,
):
    explicit_filter = has_explicit_filter(class_group_id, session_id, subject_id, teacher_id, event_type, severity, date)
    if explicit_filter:
        events, filters = ai_event_filter_context(
            db,
            class_group_id,
            session_id,
            subject_id,
            teacher_id,
            event_type,
            severity,
            date,
        )
        pdf_events = events
        limited_note = None
    else:
        events = ai_service.list_ai_events(db)
        filters = {
            "class_group_id": "",
            "session_id": "",
            "subject_id": "",
            "teacher_id": "",
            "event_type": "",
            "severity": "",
            "date": "",
        }
        pdf_events = events[:50]
        limited_note = "Showing latest 50 events. Use filters for a focused report."

    try:
        pdf = report_service.build_ai_events_pdf(
            pdf_events,
            filters,
            ai_service.ai_event_summary(events),
            note=limited_note,
        )
    except ImportError:
        return redirect_with("/ai-events", error="PDF export is unavailable. Install reportlab from requirements.txt.")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ai-event-report.pdf"'},
    )
