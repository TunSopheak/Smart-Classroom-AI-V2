from sqlalchemy import func
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from app.models.ai_event import AIEvent
from app.models.session import Session as ClassroomSession


INFO = "info"
WARNING = "warning"
CRITICAL = "critical"

EVENTS = {
    "monitoring_started": (INFO, "Monitoring started for the active session."),
    "monitoring_stopped": (INFO, "Monitoring stopped for the active session."),
    "face_detected": (INFO, "Demo event: face detected."),
    "attention_warning": (WARNING, "Demo event: attention warning logged."),
    "phone_usage_warning": (WARNING, "Demo event: phone usage warning logged."),
    "no_event": (INFO, "Demo event: no event detected."),
}


def active_session_query(db: DatabaseSession):
    return db.query(ClassroomSession).options(
        joinedload(ClassroomSession.teacher),
        joinedload(ClassroomSession.subject),
        joinedload(ClassroomSession.class_group),
        joinedload(ClassroomSession.weekly_schedule),
    )


def list_active_sessions(db: DatabaseSession) -> list[ClassroomSession]:
    return (
        active_session_query(db)
        .filter(ClassroomSession.status == "active")
        .order_by(ClassroomSession.session_date.desc(), ClassroomSession.start_time.asc())
        .all()
    )


def get_active_session(db: DatabaseSession) -> ClassroomSession | None:
    return (
        active_session_query(db)
        .filter(ClassroomSession.status == "active")
        .order_by(ClassroomSession.session_date.desc(), ClassroomSession.start_time.asc())
        .first()
    )


def get_active_session_by_id(db: DatabaseSession, session_id: int) -> ClassroomSession | None:
    return (
        active_session_query(db)
        .filter(ClassroomSession.id == session_id, ClassroomSession.status == "active")
        .first()
    )


def resolve_selected_session(
    db: DatabaseSession,
    session_id: str | None,
) -> tuple[ClassroomSession | None, list[ClassroomSession], str | None]:
    active_sessions = list_active_sessions(db)
    if not active_sessions:
        return None, active_sessions, "No active session. Start a session before AI monitoring."

    if session_id:
        try:
            selected_id = int(session_id)
        except ValueError:
            return None, active_sessions, "Please select a valid active session."

        selected = get_active_session_by_id(db, selected_id)
        if selected is None:
            return None, active_sessions, "Selected session is no longer active."
        return selected, active_sessions, None

    if len(active_sessions) == 1:
        return active_sessions[0], active_sessions, None

    return None, active_sessions, "Please select an active session to monitor."


def get_session_for_event(db: DatabaseSession, session_id: int | str | None) -> tuple[ClassroomSession | None, str | None]:
    if session_id is None:
        return None, "Please select an active session to monitor."

    try:
        selected_id = int(session_id)
    except (TypeError, ValueError):
        return None, "Please select a valid active session."

    selected = get_active_session_by_id(db, selected_id)
    if selected is None:
        return None, "Selected session is no longer active."
    return selected, None


def recent_events(db: DatabaseSession, session_id: int | None = None, limit: int = 20) -> list[AIEvent]:
    query = (
        db.query(AIEvent)
        .options(
            joinedload(AIEvent.session).joinedload(ClassroomSession.teacher),
            joinedload(AIEvent.session).joinedload(ClassroomSession.subject),
            joinedload(AIEvent.session).joinedload(ClassroomSession.class_group),
        )
        .order_by(AIEvent.detected_at.desc())
    )
    if session_id is not None:
        query = query.filter(AIEvent.session_id == session_id)
    return query.limit(limit).all()


def list_ai_events(
    db: DatabaseSession,
    class_group_id: int | None = None,
    session_id: int | None = None,
    subject_id: int | None = None,
    teacher_id: int | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    detected_date=None,
) -> list[AIEvent]:
    query = (
        db.query(AIEvent)
        .options(
            joinedload(AIEvent.session).joinedload(ClassroomSession.teacher),
            joinedload(AIEvent.session).joinedload(ClassroomSession.subject),
            joinedload(AIEvent.session).joinedload(ClassroomSession.class_group),
        )
        .order_by(AIEvent.detected_at.desc())
    )

    if class_group_id:
        query = query.filter(AIEvent.class_group_id == class_group_id)
    if session_id:
        query = query.filter(AIEvent.session_id == session_id)
    if subject_id:
        query = query.filter(AIEvent.subject_id == subject_id)
    if teacher_id:
        query = query.filter(AIEvent.teacher_id == teacher_id)
    if event_type:
        query = query.filter(AIEvent.event_type == event_type)
    if severity:
        query = query.filter(AIEvent.severity == severity)
    if detected_date:
        query = query.filter(func.date(AIEvent.detected_at) == detected_date.isoformat())

    return query.all()


def ai_event_summary(events: list[AIEvent]) -> dict[str, int]:
    return {
        "total": len(events),
        "info": sum(1 for event in events if event.severity == INFO),
        "warning": sum(1 for event in events if event.severity == WARNING),
        "critical": sum(1 for event in events if event.severity == CRITICAL),
        "face_detected": sum(1 for event in events if event.event_type == "face_detected"),
        "attention_warning": sum(1 for event in events if event.event_type == "attention_warning"),
        "phone_usage_warning": sum(1 for event in events if event.event_type == "phone_usage_warning"),
    }


def log_event(db: DatabaseSession, event_type: str, session_id: int | str | None) -> tuple[AIEvent | None, str | None]:
    active_session, session_error = get_session_for_event(db, session_id)
    if session_error:
        return None, session_error
    if event_type not in EVENTS:
        return None, "Unknown AI monitoring event."

    severity, message = EVENTS[event_type]
    event = AIEvent(
        session_id=active_session.id,
        class_group_id=active_session.class_group_id,
        teacher_id=active_session.teacher_id,
        subject_id=active_session.subject_id,
        schedule_id=active_session.schedule_id,
        event_type=event_type,
        severity=severity,
        message=message,
        description=message,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event, None
