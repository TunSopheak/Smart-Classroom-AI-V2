from datetime import datetime

from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from app.models.attendance import Attendance
from app.models.enrollment import Enrollment
from app.models.session import Session as ClassroomSession
from app.models.student import Student


PRESENT = "present"
LATE = "late"
ABSENT = "absent"
PERMISSION = "permission"
QR = "qr"
MANUAL = "manual"
AUTO_ABSENT = "auto_absent"
ACTIVE = "active"


def list_active_sessions(db: DatabaseSession) -> list[ClassroomSession]:
    return (
        db.query(ClassroomSession)
        .options(
            joinedload(ClassroomSession.teacher),
            joinedload(ClassroomSession.subject),
            joinedload(ClassroomSession.class_group),
        )
        .filter(ClassroomSession.status == ACTIVE)
        .order_by(ClassroomSession.session_date.desc(), ClassroomSession.start_time.asc())
        .all()
    )


def find_student_by_qr_value(db: DatabaseSession, qr_value: str) -> Student | None:
    return db.query(Student).filter(Student.student_code == qr_value.strip()).first()


def active_enrollment_for_class(db: DatabaseSession, student_id: int, class_group_id: int) -> Enrollment | None:
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student_id,
            Enrollment.class_group_id == class_group_id,
            Enrollment.status == ACTIVE,
        )
        .first()
    )


def existing_attendance(db: DatabaseSession, session_id: int, student_id: int) -> Attendance | None:
    return (
        db.query(Attendance)
        .filter(Attendance.session_id == session_id, Attendance.student_id == student_id)
        .first()
    )


def attendance_status_for_time(session: ClassroomSession, recorded_at: datetime) -> str:
    if session.late_time is None:
        return PRESENT
    return PRESENT if recorded_at.time() <= session.late_time else LATE


def scan_student(
    db: DatabaseSession,
    qr_value: str,
    source: str = QR,
    recorded_at: datetime | None = None,
) -> tuple[Attendance | None, str | None]:
    active_sessions = list_active_sessions(db)
    if not active_sessions:
        return None, "No active session is available for attendance scanning."

    student = find_student_by_qr_value(db, qr_value)
    if student is None:
        return None, "Student ID was not found."
    if student.status != ACTIVE:
        return None, "This student is inactive and cannot be marked present."

    eligible_sessions = [
        session
        for session in active_sessions
        if active_enrollment_for_class(db, student.id, session.class_group_id) is not None
    ]
    if not eligible_sessions:
        return None, "This student is not actively enrolled in the active session class."

    session = eligible_sessions[0]
    duplicate = existing_attendance(db, session.id, student.id)
    if duplicate is not None:
        return None, "Attendance was already recorded for this student and session."

    recorded_at = recorded_at or datetime.now()
    status = attendance_status_for_time(session, recorded_at)
    attendance = Attendance(
        session_id=session.id,
        student_id=student.id,
        class_group_id=session.class_group_id,
        schedule_id=session.schedule_id,
        status=status,
        source=source,
        method=source,
        recorded_at=recorded_at,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance, None


def create_absent_records_for_session(db: DatabaseSession, session: ClassroomSession) -> int:
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.class_group_id == session.class_group_id,
            Enrollment.status == ACTIVE,
        )
        .all()
    )

    created = 0
    for enrollment in enrollments:
        student = db.get(Student, enrollment.student_id)
        if student is None or student.status != ACTIVE:
            continue
        if existing_attendance(db, session.id, enrollment.student_id) is not None:
            continue

        attendance = Attendance(
            session_id=session.id,
            student_id=enrollment.student_id,
            class_group_id=session.class_group_id,
            schedule_id=session.schedule_id,
            status=ABSENT,
            source=AUTO_ABSENT,
            method=AUTO_ABSENT,
            note="Created automatically when the session was closed.",
        )
        db.add(attendance)
        created += 1

    if created:
        db.commit()
    return created


def list_attendance_records(
    db: DatabaseSession,
    class_group_id: int | None = None,
    session_id: int | None = None,
    student_search: str | None = None,
    status: str | None = None,
) -> list[Attendance]:
    query = (
        db.query(Attendance)
        .options(
            joinedload(Attendance.student),
            joinedload(Attendance.class_group),
            joinedload(Attendance.session).joinedload(ClassroomSession.teacher),
            joinedload(Attendance.session).joinedload(ClassroomSession.subject),
            joinedload(Attendance.session).joinedload(ClassroomSession.class_group),
        )
        .order_by(Attendance.recorded_at.desc())
    )

    if class_group_id:
        query = query.filter(Attendance.class_group_id == class_group_id)
    if session_id:
        query = query.filter(Attendance.session_id == session_id)
    if status:
        query = query.filter(Attendance.status == status)
    if student_search:
        term = f"%{student_search.strip()}%"
        query = query.join(Attendance.student).filter(
            (Student.student_code.ilike(term))
            | (Student.first_name.ilike(term))
            | (Student.last_name.ilike(term))
        )

    return query.all()
