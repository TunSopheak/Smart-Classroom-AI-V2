from datetime import date, time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DatabaseSession

from app.core.database import get_db
from app.models.class_group import ClassGroup
from app.models.session import Session as ClassroomSession
from app.models.student import Student
from app.services import academic_service, iot_service, session_service

router = APIRouter(prefix="/api/mobile", tags=["mobile-api"])


def iso_date(value: date | None) -> str | None:
    return value.isoformat() if isinstance(value, date) else None


def time_label(value: time | None) -> str | None:
    return value.strftime("%H:%M") if isinstance(value, time) else None


def student_payload(student: Student) -> dict:
    current_enrollment = academic_service.current_enrollment_for_student(student)
    class_group = current_enrollment.class_group if current_enrollment else None
    return {
        "id": student.id,
        "student_code": student.student_code,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "full_name": f"{student.first_name} {student.last_name}".strip(),
        "email": student.email,
        "status": student.status,
        "class_group": class_group_payload(class_group) if class_group else None,
    }


def class_group_payload(class_group: ClassGroup | None) -> dict | None:
    if class_group is None:
        return None
    return {
        "id": class_group.id,
        "class_code": class_group.class_code,
        "name": class_group.name,
        "department": class_group.department,
        "group_code": class_group.group_code,
        "academic_year": class_group.academic_year,
        "semester": class_group.semester,
        "status": class_group.status,
    }


def session_payload(session: ClassroomSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "session_date": iso_date(session.session_date),
        "start_time": time_label(session.start_time),
        "late_time": time_label(session.late_time),
        "end_time": time_label(session.end_time),
        "room": session.room,
        "status": session.status,
        "class_group": class_group_payload(session.class_group),
        "subject": {
            "id": session.subject.id,
            "code": session.subject.code,
            "name": session.subject.name,
        }
        if session.subject
        else None,
        "teacher": {
            "id": session.teacher.id,
            "teacher_code": session.teacher.teacher_code,
            "full_name": f"{session.teacher.first_name} {session.teacher.last_name}".strip(),
        }
        if session.teacher
        else None,
    }


@router.get("/health")
async def mobile_health():
    return {
        "ok": True,
        "message": "Smart Classroom mobile API is running.",
        "version": "31A-mvp",
    }


@router.get("/summary")
async def mobile_summary(db: DatabaseSession = Depends(get_db)):
    students = academic_service.list_students(db)
    classes = academic_service.list_classes(db)
    sessions_today = session_service.list_sessions(db, view="today")
    active_sessions = [session for session in sessions_today if session.status == session_service.ACTIVE]
    device = iot_service.device_status()
    analysis_state = device.get("analysis") or {}
    snapshot = device.get("snapshot") or {}

    return {
        "ok": True,
        "summary": {
            "student_count": len(students),
            "active_student_count": sum(1 for student in students if student.status == "active"),
            "class_count": len(classes),
            "today_session_count": len(sessions_today),
            "active_session_count": len(active_sessions),
            "raspberry_pi_online": bool(device.get("online")),
            "raspberry_pi_status": device.get("status_label") or device.get("status"),
            "latest_snapshot_available": bool(snapshot.get("available")),
            "latest_snapshot_uploaded_at": snapshot.get("uploaded_at"),
            "ai_analysis_available": bool(analysis_state.get("available")),
            "session_sync_status": analysis_state.get("session_sync_status"),
            "light_1_label": device.get("light_1_label"),
            "light_2_label": device.get("light_2_label"),
        },
        "device": device,
    }


@router.get("/students")
async def mobile_students(db: DatabaseSession = Depends(get_db), limit: int = 50):
    safe_limit = min(max(limit, 1), 200)
    students = academic_service.list_students(db)[:safe_limit]
    return {
        "ok": True,
        "count": len(students),
        "students": [student_payload(student) for student in students],
    }


@router.get("/sessions/today")
async def mobile_today_sessions(db: DatabaseSession = Depends(get_db)):
    sessions = session_service.list_sessions(db, view="today")
    return {
        "ok": True,
        "count": len(sessions),
        "sessions": [session_payload(session) for session in sessions],
    }


@router.get("/iot/status")
async def mobile_iot_status():
    device = iot_service.device_status()
    return {
        "ok": True,
        "device": device,
        "snapshot": device.get("snapshot"),
        "analysis_state": device.get("analysis"),
        "light": {
            "light_1": device.get("light_1"),
            "light_2": device.get("light_2"),
            "light_1_label": device.get("light_1_label"),
            "light_2_label": device.get("light_2_label"),
        },
    }
