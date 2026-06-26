from datetime import datetime

from sqlalchemy.orm import Session as DatabaseSession

from app.ai.face_detection import recognize_faces
from app.models.attendance import Attendance
from app.models.student import Student
from app.services import attendance_service


FACE = "face"


def student_full_name(student: Student) -> str:
    return f"{student.first_name} {student.last_name}".strip()


def label_candidates(label: str | None) -> list[str]:
    clean_label = (label or "").strip()
    if not clean_label:
        return []

    candidates = []
    for separator in ("__", "_", " "):
        if separator in clean_label:
            candidates.append(clean_label.split(separator, 1)[0].strip())
    candidates.append(clean_label)

    return [candidate for index, candidate in enumerate(candidates) if candidate and candidate not in candidates[:index]]


def find_student_for_label(db: DatabaseSession, label: str | None) -> Student | None:
    for candidate in label_candidates(label):
        student = db.query(Student).filter(Student.student_code == candidate).first()
        if student is not None:
            return student
    return None


def attendance_payload(
    attendance: Attendance,
    student: Student,
    confidence: float,
    duplicate: bool,
    message: str,
) -> dict:
    detected_at = attendance.recorded_at or datetime.now()
    return {
        "student_id": student.id,
        "student_code": student.student_code,
        "student_name": student_full_name(student),
        "session_id": attendance.session_id,
        "first_seen_time": detected_at.strftime("%Y-%m-%d %H:%M:%S"),
        "detected_time": detected_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": attendance.status,
        "method": attendance.method,
        "confidence": round(float(confidence), 2),
        "duplicate": duplicate,
        "message": message,
    }


def mark_face_attendance(
    db: DatabaseSession,
    session_id: int | str | None,
    image_bytes: bytes,
) -> dict:
    face_result = recognize_faces(image_bytes)
    attendance_results = []
    warnings = []
    unknown_face_count = int(face_result.get("unknown_face_count") or 0)

    for face in face_result.get("faces", []):
        if not face.get("recognized"):
            continue

        label = face.get("label") or face.get("student_code")
        student = find_student_for_label(db, label)
        confidence = float(face.get("confidence") or 0)

        if student is None:
            unknown_face_count += 1
            warning = f"Student not found in database for face label: {label}"
            warnings.append(warning)
            print(f"[face-attendance] {warning}")
            continue

        existing_session, _, session_error = attendance_service.resolve_scan_session(db, session_id)
        if session_error or existing_session is None:
            warning = session_error or "No active session is available for face attendance."
            warnings.append(warning)
            attendance_results.append(
                {
                    "student_id": student.id,
                    "student_code": student.student_code,
                    "student_name": student_full_name(student),
                    "session_id": session_id,
                    "confidence": round(confidence, 2),
                    "duplicate": False,
                    "message": warning,
                }
            )
            continue

        duplicate = attendance_service.existing_attendance(db, existing_session.id, student.id)
        if duplicate is not None:
            print(f"[face-attendance] Duplicate skipped: {student.student_code} session={existing_session.id}")
            attendance_results.append(
                attendance_payload(
                    duplicate,
                    student,
                    confidence,
                    True,
                    "Attendance already recorded for this student and session.",
                )
            )
            continue

        attendance, error = attendance_service.scan_student(
            db,
            student.student_code,
            session_id=existing_session.id,
            source=FACE,
            recorded_at=datetime.now(),
        )
        if error or attendance is None:
            warning = error or "Face attendance could not be saved."
            warnings.append(warning)
            attendance_results.append(
                {
                    "student_id": student.id,
                    "student_code": student.student_code,
                    "student_name": student_full_name(student),
                    "session_id": existing_session.id,
                    "confidence": round(confidence, 2),
                    "duplicate": False,
                    "message": warning,
                }
            )
            continue

        print(f"[face-attendance] Attendance saved: {student.student_code} {attendance.status}")
        attendance_results.append(
            attendance_payload(
                attendance,
                student,
                confidence,
                False,
                "Face attendance saved.",
            )
        )

    return {
        "available": bool(face_result.get("available")),
        "message": face_result.get("message"),
        "faces": face_result.get("faces", []),
        "recognized_count": len(attendance_results),
        "unknown_face_count": unknown_face_count,
        "attendance": attendance_results,
        "warnings": warnings,
    }
