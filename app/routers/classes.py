from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.academic import ClassGroupCreate, ClassGroupUpdate, EnrollmentCreate
from app.services import academic_service


router = APIRouter(prefix="/classes", tags=["classes"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def class_form_payload(class_code: str, name: str, academic_year: str, semester: str, status: str = "active"):
    return {
        "class_code": class_code.strip(),
        "name": name.strip(),
        "academic_year": academic_year.strip() or None,
        "semester": semester.strip() or None,
        "status": status,
    }


@router.get("")
async def list_classes(request: Request, db: Session = Depends(get_db), message: str | None = None, error: str | None = None):
    return templates.TemplateResponse(
        request,
        "classes/list.html",
        {
            "classes": academic_service.list_classes(db),
            "message": message,
            "error": error,
        },
    )


@router.get("/new")
async def new_class(request: Request):
    return templates.TemplateResponse(
        request,
        "classes/form.html",
        {"class_group": None, "form": {}, "error": None, "action": "/classes/new"},
    )


@router.post("/new")
async def create_class(
    request: Request,
    class_code: str = Form(""),
    name: str = Form(""),
    academic_year: str = Form(""),
    semester: str = Form(""),
    db: Session = Depends(get_db),
):
    form = class_form_payload(class_code, name, academic_year, semester)
    try:
        payload = ClassGroupCreate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "classes/form.html",
            {"class_group": None, "form": form, "error": "Class code and name are required.", "action": "/classes/new"},
            status_code=400,
        )

    class_group, error = academic_service.create_class(db, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "classes/form.html",
            {"class_group": None, "form": form, "error": error, "action": "/classes/new"},
            status_code=400,
        )

    return redirect_with(f"/classes/{class_group.id}", message="Class created successfully.")


@router.get("/{class_id}")
async def class_detail(
    request: Request,
    class_id: int,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    class_group = academic_service.get_class(db, class_id)
    if class_group is None:
        return redirect_with("/classes", error="Class not found.")

    return templates.TemplateResponse(
        request,
        "classes/detail.html",
        {
            "class_group": class_group,
            "members": academic_service.active_class_members(class_group),
            "students": academic_service.list_students(db),
            "message": message,
            "error": error,
        },
    )


@router.get("/{class_id}/edit")
async def edit_class(request: Request, class_id: int, db: Session = Depends(get_db)):
    class_group = academic_service.get_class(db, class_id)
    if class_group is None:
        return redirect_with("/classes", error="Class not found.")

    return templates.TemplateResponse(
        request,
        "classes/form.html",
        {"class_group": class_group, "form": {}, "error": None, "action": f"/classes/{class_id}/edit"},
    )


@router.post("/{class_id}/edit")
async def update_class(
    request: Request,
    class_id: int,
    class_code: str = Form(""),
    name: str = Form(""),
    academic_year: str = Form(""),
    semester: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    class_group = academic_service.get_class(db, class_id)
    if class_group is None:
        return redirect_with("/classes", error="Class not found.")

    form = class_form_payload(class_code, name, academic_year, semester, status)
    try:
        payload = ClassGroupUpdate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "classes/form.html",
            {"class_group": class_group, "form": form, "error": "Class code and name are required.", "action": f"/classes/{class_id}/edit"},
            status_code=400,
        )

    updated, error = academic_service.update_class(db, class_group, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "classes/form.html",
            {"class_group": class_group, "form": form, "error": error, "action": f"/classes/{class_id}/edit"},
            status_code=400,
        )

    return redirect_with(f"/classes/{updated.id}", message="Class updated successfully.")


@router.post("/{class_id}/toggle")
async def toggle_class_status(class_id: int, db: Session = Depends(get_db)):
    class_group = academic_service.get_class(db, class_id)
    if class_group is None:
        return redirect_with("/classes", error="Class not found.")

    new_status = "inactive" if class_group.status == "active" else "active"
    academic_service.set_class_status(db, class_group, new_status)
    return redirect_with(f"/classes/{class_id}", message=f"Class marked {new_status}.")


@router.post("/{class_id}/enroll")
async def enroll_from_class(class_id: int, student_id: int = Form(0), db: Session = Depends(get_db)):
    enrollment, error = academic_service.create_enrollment(
        db, EnrollmentCreate(student_id=student_id, class_group_id=class_id)
    )
    if error:
        return redirect_with(f"/classes/{class_id}", error=error)

    return redirect_with(f"/classes/{class_id}", message="Student enrolled successfully.")
