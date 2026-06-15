from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.academic import SubjectCreate, SubjectUpdate
from app.services import academic_service


router = APIRouter(prefix="/subjects", tags=["subjects"])
templates = Jinja2Templates(directory="app/templates")


def redirect_with(path: str, **params: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode(params)}", status_code=303)


def subject_form_payload(code: str, name: str, description: str, status: str = "active"):
    return {
        "code": code.strip(),
        "name": name.strip(),
        "description": description.strip() or None,
        "status": status,
    }


@router.get("")
async def list_subjects(
    request: Request,
    db: Session = Depends(get_db),
    message: str | None = None,
    error: str | None = None,
):
    return templates.TemplateResponse(
        request,
        "subjects/list.html",
        {"subjects": academic_service.list_subjects(db), "message": message, "error": error},
    )


@router.get("/new")
async def new_subject(request: Request):
    return templates.TemplateResponse(
        request,
        "subjects/form.html",
        {"subject": None, "form": {}, "error": None, "action": "/subjects/new"},
    )


@router.post("/new")
async def create_subject(
    request: Request,
    code: str = Form(""),
    name: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    form = subject_form_payload(code, name, description)
    if not form["code"] and form["name"]:
        form["code"] = academic_service.generate_subject_code(db)
    try:
        payload = SubjectCreate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "subjects/form.html",
            {"subject": None, "form": form, "error": "Subject name is required.", "action": "/subjects/new"},
            status_code=400,
        )

    subject, error = academic_service.create_subject(db, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "subjects/form.html",
            {"subject": None, "form": form, "error": error, "action": "/subjects/new"},
            status_code=400,
        )

    return redirect_with("/subjects", message=f"Subject created successfully with code {subject.code}.")


@router.get("/{subject_id}/edit")
async def edit_subject(request: Request, subject_id: int, db: Session = Depends(get_db)):
    subject = academic_service.get_subject(db, subject_id)
    if subject is None:
        return redirect_with("/subjects", error="Subject not found.")

    return templates.TemplateResponse(
        request,
        "subjects/form.html",
        {"subject": subject, "form": {}, "error": None, "action": f"/subjects/{subject_id}/edit"},
    )


@router.post("/{subject_id}/edit")
async def update_subject(
    request: Request,
    subject_id: int,
    code: str = Form(""),
    name: str = Form(""),
    description: str = Form(""),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    subject = academic_service.get_subject(db, subject_id)
    if subject is None:
        return redirect_with("/subjects", error="Subject not found.")

    form = subject_form_payload(code, name, description, status)
    try:
        payload = SubjectUpdate(**form)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "subjects/form.html",
            {"subject": subject, "form": form, "error": "Subject code and name are required.", "action": f"/subjects/{subject_id}/edit"},
            status_code=400,
        )

    updated, error = academic_service.update_subject(db, subject, payload)
    if error:
        return templates.TemplateResponse(
            request,
            "subjects/form.html",
            {"subject": subject, "form": form, "error": error, "action": f"/subjects/{subject_id}/edit"},
            status_code=400,
        )

    return redirect_with("/subjects", message=f"Subject {updated.code} updated successfully.")


@router.post("/{subject_id}/toggle")
async def toggle_subject_status(subject_id: int, db: Session = Depends(get_db)):
    subject = academic_service.get_subject(db, subject_id)
    if subject is None:
        return redirect_with("/subjects", error="Subject not found.")

    new_status = "inactive" if subject.status == "active" else "active"
    academic_service.set_subject_status(db, subject, new_status)
    return redirect_with("/subjects", message=f"Subject marked {new_status}.")
