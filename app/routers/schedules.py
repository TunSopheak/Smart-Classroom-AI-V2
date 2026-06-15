from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.academic import WeeklyScheduleCreate, WeeklyScheduleUpdate
from app.services import academic_service


router = APIRouter(prefix="/schedules", tags=["schedules"])
templates = Jinja2Templates(directory="app/templates")

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def schedule_form_payload(
    teacher_id: int,
    subject_id: int,
    class_group_id: int,
    day_of_week: str,
    start_time: str,
    end_time: str,
    room: str,
    status: str = "active",
):
    return {
        "teacher_id": teacher_id,
        "subject_id": subject_id,
        "class_group_id": class_group_id,
        "day_of_week": day_of_week.strip(),
        "start_time": start_time.strip(),
        "end_time": end_time.strip(),
        "room": room.strip(),
        "status": status,
    }


def schedule_form_context(
    db: Session,
    schedule=None,
    form: dict | None = None,
    error: str | None = None,
    action: str = "/schedules/new",
) -> dict:
    teachers = academic_service.list_teachers(db)
    subjects = academic_service.list_subjects(db)
    classes = academic_service.list_classes(db)
    missing = []
    if not teachers:
        missing.append("teacher")
    if not subjects:
        missing.append("subject")
    if not classes:
        missing.append("class")

    return {
        "schedule": schedule,
        "form": form or {},
        "error": error,
        "action": action,
        "teachers": teachers,
        "subjects": subjects,
        "classes": classes,
        "days_of_week": DAYS_OF_WEEK,
        "missing_dependencies": missing,
    }


@router.get("")
async def list_schedules(
    request: Request,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "schedules/list.html",
        {"schedules": academic_service.list_schedules(db), "message": message, "error": error},
    )


@router.get("/new")
async def new_schedule(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "schedules/form.html",
        schedule_form_context(db),
    )


@router.post("/new")
async def create_schedule(
    request: Request,
    teacher_id: int = Form(0),
    subject_id: int = Form(0),
    class_group_id: int = Form(0),
    day_of_week: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    room: str = Form(""),
    db: Session = Depends(get_db),
):
    form = schedule_form_payload(teacher_id, subject_id, class_group_id, day_of_week, start_time, end_time, room)
    try:
        payload = WeeklyScheduleCreate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "schedules/form.html",
            schedule_form_context(db, form=form, error="Teacher, subject, class, day, time, and room are required."),
            status_code=400,
        )

    schedule, error = academic_service.create_schedule(db, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "schedules/form.html",
            schedule_form_context(db, form=form, error=error),
            status_code=400,
        )

    return redirect_with("/schedules", message="Weekly schedule created successfully.")


@router.get("/{schedule_id}/edit")
async def edit_schedule(request: Request, schedule_id: int, db: Session = Depends(get_db)):
    schedule = academic_service.get_schedule(db, schedule_id)
    if schedule is None:
        return redirect_with("/schedules", error="Schedule not found.")

    return templates.TemplateResponse(
        request,
        "schedules/form.html",
        schedule_form_context(db, schedule=schedule, action=f"/schedules/{schedule_id}/edit"),
    )


@router.post("/{schedule_id}/edit")
async def update_schedule(
    request: Request,
    schedule_id: int,
    teacher_id: int = Form(0),
    subject_id: int = Form(0),
    class_group_id: int = Form(0),
    day_of_week: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    room: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    schedule = academic_service.get_schedule(db, schedule_id)
    if schedule is None:
        return redirect_with("/schedules", error="Schedule not found.")

    form = schedule_form_payload(teacher_id, subject_id, class_group_id, day_of_week, start_time, end_time, room, status)
    try:
        payload = WeeklyScheduleUpdate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "schedules/form.html",
            schedule_form_context(
                db,
                schedule=schedule,
                form=form,
                error="Teacher, subject, class, day, time, and room are required.",
                action=f"/schedules/{schedule_id}/edit",
            ),
            status_code=400,
        )

    updated, error = academic_service.update_schedule(db, schedule, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "schedules/form.html",
            schedule_form_context(
                db,
                schedule=schedule,
                form=form,
                error=error,
                action=f"/schedules/{schedule_id}/edit",
            ),
            status_code=400,
        )

    return redirect_with("/schedules", message=f"Schedule {updated.day_of_week} {updated.start_time.strftime('%H:%M')} updated successfully.")


@router.post("/{schedule_id}/toggle")
async def toggle_schedule_status(schedule_id: int, db: Session = Depends(get_db)):
    schedule = academic_service.get_schedule(db, schedule_id)
    if schedule is None:
        return redirect_with("/schedules", error="Schedule not found.")

    new_status = "inactive" if schedule.status == "active" else "active"
    academic_service.set_schedule_status(db, schedule, new_status)
    return redirect_with("/schedules", message=f"Schedule marked {new_status}.")
