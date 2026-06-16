from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session as DatabaseSession
from sqlalchemy.orm import joinedload

from app.models.ai_event import AIEvent
from app.models.attendance import Attendance
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
    "occupancy_empty": (WARNING, "No students detected in the classroom."),
    "light_auto_off": (WARNING, "Classroom light turned OFF automatically because no students were detected."),
    "light_auto_on": (INFO, "Classroom light turned ON because students were detected."),
}

AUTO_FACE_MESSAGE = "Face detected by camera."
AUTO_FACE_COOLDOWN_SECONDS = 15
DEMO_LIGHT_AUTO_OFF_SECONDS = 10
OCCUPANCY_EMPTY_COOLDOWN_SECONDS = 60
UNKNOWN = "Unknown"
OCCUPIED = "Occupied"
EMPTY = "Empty"
LIGHT_AUTO = "Auto Mode"
LIGHT_ON = "ON"
LIGHT_OFF = "OFF"
_occupancy_states: dict[int, dict] = {}


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


def qr_present_count(db: DatabaseSession, session_id: int) -> int:
    return (
        db.query(func.count(Attendance.id))
        .filter(Attendance.session_id == session_id, Attendance.status.in_(["present", "late"]))
        .scalar()
        or 0
    )


def default_occupancy_state() -> dict:
    return {
        "detected_count": None,
        "occupancy_status": UNKNOWN,
        "light_status": LIGHT_AUTO,
        "zero_since": None,
        "last_occupancy_empty_at": None,
    }


def occupancy_status_for_count(detected_count: int | None) -> str:
    if detected_count is None:
        return UNKNOWN
    if detected_count > 0:
        return OCCUPIED
    return EMPTY


def occupancy_empty_cooldown_ready(state: dict, now: datetime) -> bool:
    last_empty_at = state.get("last_occupancy_empty_at")
    return last_empty_at is None or (now - last_empty_at).total_seconds() >= OCCUPANCY_EMPTY_COOLDOWN_SECONDS


def log_occupancy_empty_if_ready(db: DatabaseSession, active_session: ClassroomSession, state: dict, now: datetime) -> AIEvent | None:
    if not occupancy_empty_cooldown_ready(state, now):
        return None

    event = create_event(db, active_session, "occupancy_empty", WARNING, EVENTS["occupancy_empty"][1])
    state["last_occupancy_empty_at"] = now
    return event


def log_light_change(
    db: DatabaseSession,
    active_session: ClassroomSession,
    state: dict,
    event_type: str,
    new_status: str,
    severity: str,
) -> AIEvent | None:
    if state["light_status"] == new_status:
        return None

    state["light_status"] = new_status
    return create_event(db, active_session, event_type, severity, EVENTS[event_type][1])


def occupancy_context(db: DatabaseSession, active_session: ClassroomSession) -> dict:
    state = evaluate_light_auto_off(db, active_session)
    detected_count = state.get("detected_count")
    qr_count = qr_present_count(db, active_session.id)
    return {
        "qr_present_count": qr_count,
        "detected_count": detected_count,
        "detected_count_label": "Unknown" if detected_count is None else str(detected_count),
        "difference": None if detected_count is None else detected_count - qr_count,
        "difference_label": "Unknown" if detected_count is None else str(detected_count - qr_count),
        "occupancy_status": state["occupancy_status"],
        "light_status": state["light_status"],
        "auto_off_seconds": DEMO_LIGHT_AUTO_OFF_SECONDS,
    }


def update_detected_count(
    db: DatabaseSession,
    session_id: int | str | None,
    detected_count: int,
) -> tuple[dict | None, str | None]:
    active_session, session_error = get_session_for_event(db, session_id)
    if session_error:
        return None, session_error
    if detected_count < 0:
        return None, "Detected count cannot be negative."

    now = datetime.utcnow()
    state = _occupancy_states.setdefault(active_session.id, default_occupancy_state())
    previous_light = state["light_status"]

    state["detected_count"] = detected_count
    state["occupancy_status"] = occupancy_status_for_count(detected_count)

    if detected_count == 0:
        if state["zero_since"] is None:
            state["zero_since"] = now
        log_occupancy_empty_if_ready(db, active_session, state, now)
        if previous_light == LIGHT_ON:
            state["light_status"] = LIGHT_AUTO
    else:
        state["zero_since"] = None
        log_light_change(db, active_session, state, "light_auto_on", LIGHT_ON, INFO)

    return occupancy_context(db, active_session), None


def evaluate_light_auto_off(db: DatabaseSession, active_session: ClassroomSession) -> dict:
    state = _occupancy_states.setdefault(active_session.id, default_occupancy_state())
    if state["detected_count"] == 0 and state["zero_since"]:
        elapsed = (datetime.utcnow() - state["zero_since"]).total_seconds()
        if elapsed >= DEMO_LIGHT_AUTO_OFF_SECONDS:
            log_light_change(db, active_session, state, "light_auto_off", LIGHT_OFF, WARNING)
    return state


def occupancy_context_for_session_id(
    db: DatabaseSession,
    session_id: int | str | None,
) -> tuple[dict | None, str | None]:
    active_session, session_error = get_session_for_event(db, session_id)
    if session_error:
        return None, session_error
    return occupancy_context(db, active_session), None


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
        "occupancy_empty": sum(1 for event in events if event.event_type == "occupancy_empty"),
        "light_auto_off": sum(1 for event in events if event.event_type == "light_auto_off"),
        "light_auto_on": sum(1 for event in events if event.event_type == "light_auto_on"),
    }


def create_event(
    db: DatabaseSession,
    active_session: ClassroomSession,
    event_type: str,
    severity: str,
    message: str,
) -> AIEvent:
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
    return event


def latest_auto_face_event(db: DatabaseSession, session_id: int) -> AIEvent | None:
    return (
        db.query(AIEvent)
        .filter(
            AIEvent.session_id == session_id,
            AIEvent.event_type == "face_detected",
            AIEvent.message == AUTO_FACE_MESSAGE,
        )
        .order_by(AIEvent.detected_at.desc())
        .first()
    )


def log_auto_face_detected(db: DatabaseSession, session_id: int | str | None) -> tuple[AIEvent | None, str | None]:
    active_session, session_error = get_session_for_event(db, session_id)
    if session_error:
        return None, session_error

    latest_event = latest_auto_face_event(db, active_session.id)
    if latest_event and latest_event.detected_at:
        cooldown_until = latest_event.detected_at + timedelta(seconds=AUTO_FACE_COOLDOWN_SECONDS)
        now = datetime.now(latest_event.detected_at.tzinfo) if latest_event.detected_at.tzinfo else datetime.utcnow()
        if cooldown_until > now:
            return None, "Face detected recently. Waiting for cooldown."

    return create_event(db, active_session, "face_detected", INFO, AUTO_FACE_MESSAGE), None


def log_event(db: DatabaseSession, event_type: str, session_id: int | str | None) -> tuple[AIEvent | None, str | None]:
    active_session, session_error = get_session_for_event(db, session_id)
    if session_error:
        return None, session_error
    if event_type not in EVENTS:
        return None, "Unknown AI monitoring event."

    state = _occupancy_states.setdefault(active_session.id, default_occupancy_state())
    now = datetime.utcnow()

    if event_type == "occupancy_empty":
        event = log_occupancy_empty_if_ready(db, active_session, state, now)
        if event is None:
            return None, "Occupancy empty was logged recently. Waiting for cooldown."
        return event, None

    if event_type == "light_auto_off":
        event = log_light_change(db, active_session, state, event_type, LIGHT_OFF, WARNING)
        if event is None:
            return None, "Classroom light is already OFF."
        return event, None

    if event_type == "light_auto_on":
        event = log_light_change(db, active_session, state, event_type, LIGHT_ON, INFO)
        if event is None:
            return None, "Classroom light is already ON."
        return event, None

    severity, message = EVENTS[event_type]
    return create_event(db, active_session, event_type, severity, message), None
