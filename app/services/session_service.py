from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from app.models.session import Session as ClassroomSession
from app.models.weekly_schedule import WeeklySchedule


SCHEDULED = "scheduled"
ACTIVE = "active"
CLOSED = "closed"
CANCELLED = "cancelled"
SESSION_STATUSES = [SCHEDULED, ACTIVE, CLOSED, CANCELLED]


def cleanup_stale_active_sessions(db: DatabaseSession, today: date | None = None) -> int:
    today = today or date.today()
    stale_sessions = (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.status == ACTIVE,
            ClassroomSession.session_date < today,
        )
        .all()
    )
    for session in stale_sessions:
        session.status = CLOSED

    if stale_sessions:
        db.commit()
    return len(stale_sessions)


def list_sessions(
    db: DatabaseSession,
    view: str = "today",
    selected_date: date | None = None,
    status: str | None = None,
) -> list[ClassroomSession]:
    query = (
        db.query(ClassroomSession)
        .options(
            joinedload(ClassroomSession.teacher),
            joinedload(ClassroomSession.subject),
            joinedload(ClassroomSession.class_group),
            joinedload(ClassroomSession.weekly_schedule),
        )
    )

    if view == "today":
        query = query.filter(ClassroomSession.session_date == date.today())
    elif view == "date" and selected_date is not None:
        query = query.filter(ClassroomSession.session_date == selected_date)

    if status in SESSION_STATUSES:
        query = query.filter(ClassroomSession.status == status)

    return query.order_by(ClassroomSession.session_date.desc(), ClassroomSession.start_time.asc()).all()


def parse_filter_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def normalize_session_view(view: str | None) -> str:
    return view if view in {"today", "all", "date"} else "today"


def normalize_session_status(status: str | None) -> str | None:
    return status if status in SESSION_STATUSES else None


def session_filter_label(view: str, selected_date: date | None, status: str | None) -> str:
    if view == "all":
        label = "All Sessions"
    elif view == "date" and selected_date is not None:
        label = f"Sessions for {selected_date.isoformat()}"
    else:
        label = "Today's Sessions"

    if status:
        label = f"{label} - {status.capitalize()}"
    return label


def get_session(db: DatabaseSession, session_id: int) -> ClassroomSession | None:
    return (
        db.query(ClassroomSession)
        .options(
            joinedload(ClassroomSession.teacher),
            joinedload(ClassroomSession.subject),
            joinedload(ClassroomSession.class_group),
            joinedload(ClassroomSession.weekly_schedule),
        )
        .filter(ClassroomSession.id == session_id)
        .first()
    )


def find_session_for_schedule_date(
    db: DatabaseSession,
    schedule_id: int,
    session_date: date,
) -> ClassroomSession | None:
    return (
        db.query(ClassroomSession)
        .filter(
            ClassroomSession.schedule_id == schedule_id,
            ClassroomSession.session_date == session_date,
        )
        .first()
    )


def generate_title(schedule: WeeklySchedule, session_date: date) -> str:
    return f"{schedule.subject.code} - {schedule.class_group.class_code} - {session_date.isoformat()}"


def calculate_late_time(schedule: WeeklySchedule):
    return (datetime.combine(date.today(), schedule.start_time) + timedelta(minutes=15)).time().replace(
        second=0,
        microsecond=0,
    )


def active_schedules_for_day(db: DatabaseSession, day_name: str) -> list[WeeklySchedule]:
    return (
        db.query(WeeklySchedule)
        .options(
            joinedload(WeeklySchedule.teacher),
            joinedload(WeeklySchedule.subject),
            joinedload(WeeklySchedule.class_group),
        )
        .filter(
            WeeklySchedule.status == ACTIVE,
            func.lower(WeeklySchedule.day_of_week) == day_name.lower(),
        )
        .order_by(WeeklySchedule.start_time.asc())
        .all()
    )


def generate_sessions_for_date(db: DatabaseSession, target_date: date | None = None) -> tuple[int, int, str | None]:
    target_date = target_date or date.today()
    cleanup_stale_active_sessions(db, today=target_date)
    day_name = target_date.strftime("%A")
    schedules = active_schedules_for_day(db, day_name)

    if not schedules:
        return 0, 0, f"No active weekly schedules match {day_name}."

    created = 0
    skipped = 0
    for schedule in schedules:
        existing = find_session_for_schedule_date(db, schedule.id, target_date)
        if existing is not None:
            skipped += 1
            continue

        session = ClassroomSession(
            schedule_id=schedule.id,
            weekly_schedule_id=schedule.id,
            class_group_id=schedule.class_group_id,
            teacher_id=schedule.teacher_id,
            subject_id=schedule.subject_id,
            session_date=target_date,
            title=generate_title(schedule, target_date),
            start_time=schedule.start_time,
            late_time=calculate_late_time(schedule),
            end_time=schedule.end_time,
            room=schedule.room,
            status=SCHEDULED,
        )
        db.add(session)
        created += 1

    db.commit()
    if created == 0:
        return created, skipped, f"Today's sessions were already generated. {skipped} duplicate schedule(s) skipped."
    if skipped:
        return created, skipped, f"Generated {created} session(s). Skipped {skipped} duplicate schedule(s)."
    return created, skipped, f"Generated {created} session(s) for {day_name}."


def active_session_for_class(
    db: DatabaseSession,
    class_group_id: int,
    exclude_session_id: int | None = None,
) -> ClassroomSession | None:
    query = db.query(ClassroomSession).filter(
        ClassroomSession.class_group_id == class_group_id,
        ClassroomSession.status == ACTIVE,
    )
    if exclude_session_id is not None:
        query = query.filter(ClassroomSession.id != exclude_session_id)
    return query.first()


def start_session(db: DatabaseSession, session: ClassroomSession) -> tuple[ClassroomSession | None, str | None]:
    if session.status == CANCELLED:
        return None, "Cancelled sessions cannot be started."
    if session.status == CLOSED:
        return None, "Closed sessions cannot be started."
    if session.status == ACTIVE:
        return session, "This session is already active."

    active = active_session_for_class(db, session.class_group_id, exclude_session_id=session.id)
    if active is not None:
        return None, f"{session.class_group.class_code} already has an active session."

    session.status = ACTIVE
    db.commit()
    db.refresh(session)
    return session, None


def close_session(db: DatabaseSession, session: ClassroomSession) -> tuple[ClassroomSession | None, str | None]:
    if session.status == SCHEDULED:
        return None, "Start the session before closing it."
    if session.status == CANCELLED:
        return None, "Cancelled sessions cannot be closed."
    if session.status == CLOSED:
        return session, "This session is already closed."

    from app.services import attendance_service

    session.status = CLOSED
    absent_count = attendance_service.create_absent_records_for_session(db, session)
    db.commit()
    db.refresh(session)
    session.auto_absent_count = absent_count
    return session, None


def cancel_session(db: DatabaseSession, session: ClassroomSession) -> tuple[ClassroomSession | None, str | None]:
    if session.status == ACTIVE:
        return None, "Active sessions must be closed before they can be cancelled."
    if session.status == CLOSED:
        return None, "Closed sessions cannot be cancelled."
    if session.status == CANCELLED:
        return session, "This session is already cancelled."

    session.status = CANCELLED
    db.commit()
    db.refresh(session)
    return session, None
