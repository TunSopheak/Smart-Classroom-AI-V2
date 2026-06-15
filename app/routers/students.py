from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.academic import EnrollmentCreate, StudentCreate, StudentUpdate
from app.services import academic_service


router = APIRouter(prefix="/students", tags=["students"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def student_form_payload(student_code: str, first_name: str, last_name: str, email: str, status: str = "active"):
    return {
        "student_code": student_code.strip(),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email.strip() or None,
        "status": status,
    }


@router.get("")
async def list_students(request: Request, db: Session = Depends(get_db), message: str | None = None, error: str | None = None):
    students = academic_service.list_students(db)
    current_enrollments = {
        student.id: academic_service.current_enrollment_for_student(student)
        for student in students
    }
    return templates.TemplateResponse(
        request,
        "students/list.html",
        {"students": students, "current_enrollments": current_enrollments, "message": message, "error": error},
    )


@router.get("/new")
async def new_student(request: Request):
    return templates.TemplateResponse(
        request,
        "students/form.html",
        {"student": None, "form": {}, "error": None, "action": "/students/new"},
    )


@router.post("/new")
async def create_student(
    request: Request,
    student_code: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    form = student_form_payload(student_code, first_name, last_name, email)
    try:
        payload = StudentCreate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "students/form.html",
            {"student": None, "form": form, "error": "Student ID, first name, and last name are required.", "action": "/students/new"},
            status_code=400,
        )

    student, error = academic_service.create_student(db, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "students/form.html",
            {"student": None, "form": form, "error": error, "action": "/students/new"},
            status_code=400,
        )

    return redirect_with(f"/students/{student.id}", message="Student created successfully.")


@router.get("/{student_id}")
async def student_detail(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    student = academic_service.get_student(db, student_id)
    if student is None:
        return redirect_with("/students", error="Student not found.")

    return templates.TemplateResponse(
        request,
        "students/detail.html",
        {
            "student": student,
            "current_enrollment": academic_service.current_enrollment_for_student(student),
            "classes": academic_service.list_classes(db),
            "message": message,
            "error": error,
        },
    )


@router.get("/{student_id}/edit")
async def edit_student(request: Request, student_id: int, db: Session = Depends(get_db)):
    student = academic_service.get_student(db, student_id)
    if student is None:
        return redirect_with("/students", error="Student not found.")

    return templates.TemplateResponse(
        request,
        "students/form.html",
        {"student": student, "form": {}, "error": None, "action": f"/students/{student_id}/edit"},
    )


@router.post("/{student_id}/edit")
async def update_student(
    request: Request,
    student_id: int,
    student_code: str = Form(""),
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    student = academic_service.get_student(db, student_id)
    if student is None:
        return redirect_with("/students", error="Student not found.")

    form = student_form_payload(student_code, first_name, last_name, email, status)
    try:
        payload = StudentUpdate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "students/form.html",
            {"student": student, "form": form, "error": "Student ID, first name, and last name are required.", "action": f"/students/{student_id}/edit"},
            status_code=400,
        )

    updated, error = academic_service.update_student(db, student, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "students/form.html",
            {"student": student, "form": form, "error": error, "action": f"/students/{student_id}/edit"},
            status_code=400,
        )

    return redirect_with(f"/students/{updated.id}", message="Student updated successfully.")


@router.post("/{student_id}/toggle")
async def toggle_student_status(student_id: int, db: Session = Depends(get_db)):
    student = academic_service.get_student(db, student_id)
    if student is None:
        return redirect_with("/students", error="Student not found.")

    new_status = "inactive" if student.status == "active" else "active"
    academic_service.set_student_status(db, student, new_status)
    return redirect_with(f"/students/{student_id}", message=f"Student marked {new_status}.")


@router.post("/{student_id}/enroll")
async def enroll_from_student(student_id: int, class_group_id: int = Form(0), db: Session = Depends(get_db)):
    enrollment, error = academic_service.create_enrollment(
        db, EnrollmentCreate(student_id=student_id, class_group_id=class_group_id)
    )
    if error:
        return redirect_with(f"/students/{student_id}", error=error)

    return redirect_with(f"/students/{student_id}", message="Student enrolled successfully.")
