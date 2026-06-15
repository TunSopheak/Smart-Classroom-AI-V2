from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.academic import TeacherCreate, TeacherUpdate
from app.services import academic_service


router = APIRouter(prefix="/teachers", tags=["teachers"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def teacher_form_payload(
    teacher_code: str,
    first_name: str,
    last_name: str,
    email: str,
    department: str,
    status: str = "active",
):
    return {
        "teacher_code": teacher_code.strip(),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email.strip() or None,
        "department": department.strip() or None,
        "status": status,
    }


@router.get("")
async def list_teachers(
    request: Request,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "teachers/list.html",
        {"teachers": academic_service.list_teachers(db), "message": message, "error": error},
    )


@router.get("/new")
async def new_teacher(request: Request):
    return templates.TemplateResponse(
        request,
        "teachers/form.html",
        {"teacher": None, "form": {}, "error": None, "action": "/teachers/new"},
    )


@router.post("/new")
async def create_teacher(
    request: Request,
    teacher_code: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    department: str = Form(""),
    db: Session = Depends(get_db),
):
    form = teacher_form_payload(teacher_code, first_name, last_name, email, department)
    if not form["teacher_code"]:
        form["teacher_code"] = academic_service.generate_next_teacher_code(db)
    try:
        payload = TeacherCreate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "teachers/form.html",
            {
                "teacher": None,
                "form": form,
                "error": "First name and last name are required.",
                "action": "/teachers/new",
            },
            status_code=400,
        )

    teacher, error = academic_service.create_teacher(db, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "teachers/form.html",
            {"teacher": None, "form": form, "error": error, "action": "/teachers/new"},
            status_code=400,
        )

    return redirect_with("/teachers", message="Teacher created successfully.")


@router.get("/{teacher_id}/edit")
async def edit_teacher(request: Request, teacher_id: int, db: Session = Depends(get_db)):
    teacher = academic_service.get_teacher(db, teacher_id)
    if teacher is None:
        return redirect_with("/teachers", error="Teacher not found.")

    return templates.TemplateResponse(
        request,
        "teachers/form.html",
        {"teacher": teacher, "form": {}, "error": None, "action": f"/teachers/{teacher_id}/edit"},
    )


@router.post("/{teacher_id}/edit")
async def update_teacher(
    request: Request,
    teacher_id: int,
    teacher_code: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    department: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    teacher = academic_service.get_teacher(db, teacher_id)
    if teacher is None:
        return redirect_with("/teachers", error="Teacher not found.")

    form = teacher_form_payload(teacher_code, first_name, last_name, email, department, status)
    try:
        payload = TeacherUpdate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "teachers/form.html",
            {
                "teacher": teacher,
                "form": form,
                "error": "Teacher code, first name, and last name are required.",
                "action": f"/teachers/{teacher_id}/edit",
            },
            status_code=400,
        )

    updated, error = academic_service.update_teacher(db, teacher, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "teachers/form.html",
            {"teacher": teacher, "form": form, "error": error, "action": f"/teachers/{teacher_id}/edit"},
            status_code=400,
        )

    return redirect_with("/teachers", message=f"Teacher {updated.teacher_code} updated successfully.")


@router.post("/{teacher_id}/toggle")
async def toggle_teacher_status(teacher_id: int, db: Session = Depends(get_db)):
    teacher = academic_service.get_teacher(db, teacher_id)
    if teacher is None:
        return redirect_with("/teachers", error="Teacher not found.")

    new_status = "inactive" if teacher.status == "active" else "active"
    academic_service.set_teacher_status(db, teacher, new_status)
    return redirect_with("/teachers", message=f"Teacher marked {new_status}.")
