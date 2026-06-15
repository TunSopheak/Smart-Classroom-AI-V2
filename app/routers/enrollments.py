from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enrollment import Enrollment
from app.schemas.academic import EnrollmentCreate
from app.services import academic_service


router = APIRouter(prefix="/enrollments", tags=["enrollments"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


@router.get("")
async def list_enrollments(
    request: Request,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "enrollments/list.html",
        {
            "enrollments": academic_service.list_enrollments(db),
            "students": academic_service.list_students(db),
            "classes": academic_service.list_classes(db),
            "message": message,
            "error": error,
        },
    )


@router.post("")
async def create_enrollment(
    student_id: int = Form(0),
    class_group_id: int = Form(0),
    db: Session = Depends(get_db),
):
    enrollment, error = academic_service.create_enrollment(
        db, EnrollmentCreate(student_id=student_id, class_group_id=class_group_id)
    )
    if error:
        return redirect_with("/enrollments", error=error)

    return redirect_with("/enrollments", message="Enrollment created successfully.")


@router.post("/{enrollment_id}/deactivate")
async def deactivate_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None:
        return redirect_with("/enrollments", error="Enrollment not found.")

    academic_service.deactivate_enrollment(db, enrollment)
    return redirect_with("/enrollments", message="Enrollment marked inactive.")
