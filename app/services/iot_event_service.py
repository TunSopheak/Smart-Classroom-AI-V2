"""Conservative Raspberry Pi event-evidence storage for sampled frames."""

from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.config import (
    EVENT_COOLDOWN_SECONDS,
    EVENT_SNAPSHOT_MAX_FILES,
    EVENT_SNAPSHOT_RETENTION_DAYS,
    EVENT_SNAPSHOTS_ENABLED,
    PHONE_EVENT_CONFIDENCE,
)


EVENT_SNAPSHOT_DIR = Path("app/static/uploads/iot_events")
EVENT_SNAPSHOT_URL_PREFIX = "/static/uploads/iot_events"
EVENT_FILE_SUFFIXES = {".jpg", ".jpeg", ".png"}
RECENT_EVENT_LIMIT = 10

_recent_events: list[dict] = []
_saved_source_files: set[str] = set()
_last_event_at: dict[tuple[str, str, str], datetime] = {}
_last_error: str | None = None


def utc_now() -> datetime:
    return datetime.utcnow()


def time_label(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def event_files() -> list[Path]:
    if not EVENT_SNAPSHOT_DIR.exists():
        return []
    try:
        candidates = list(EVENT_SNAPSHOT_DIR.iterdir())
    except OSError:
        return []

    files: list[tuple[float, Path]] = []
    for path in candidates:
        try:
            if path.is_file() and path.suffix.lower() in EVENT_FILE_SUFFIXES:
                files.append((path.stat().st_mtime, path))
        except OSError:
            continue
    return [path for _, path in sorted(files, reverse=True)]


def prune_recent_events() -> None:
    retained_names = {path.name for path in event_files()}
    _recent_events[:] = [
        event
        for event in _recent_events
        if event.get("filename") in retained_names
    ][:RECENT_EVENT_LIMIT]


def cleanup_event_snapshots(now: datetime | None = None) -> dict:
    global _last_error

    if not EVENT_SNAPSHOTS_ENABLED:
        return event_storage_status()

    current_time = now or utc_now()
    cutoff = current_time - timedelta(days=EVENT_SNAPSHOT_RETENTION_DAYS)
    removed_count = 0
    errors: list[str] = []

    for path in event_files():
        try:
            modified_at = datetime.utcfromtimestamp(path.stat().st_mtime)
            if modified_at < cutoff:
                path.unlink()
                removed_count += 1
        except OSError as error:
            errors.append(str(error))

    for path in event_files()[EVENT_SNAPSHOT_MAX_FILES:]:
        try:
            path.unlink()
            removed_count += 1
        except OSError as error:
            errors.append(str(error))

    _last_error = "; ".join(errors) if errors else None
    prune_recent_events()
    status = event_storage_status()
    status["removed_count"] = removed_count
    return status


def event_storage_status() -> dict:
    files = event_files()
    return {
        "enabled": EVENT_SNAPSHOTS_ENABLED,
        "event_folder": str(EVENT_SNAPSHOT_DIR),
        "event_url_prefix": EVENT_SNAPSHOT_URL_PREFIX,
        "max_files": EVENT_SNAPSHOT_MAX_FILES,
        "retention_days": EVENT_SNAPSHOT_RETENTION_DAYS,
        "cooldown_seconds": EVENT_COOLDOWN_SECONDS,
        "phone_confidence_threshold": PHONE_EVENT_CONFIDENCE,
        "total_event_files": len(files),
        "recent_events": list(_recent_events[:RECENT_EVENT_LIMIT]),
        "last_error": _last_error,
    }


def initialize_event_storage() -> None:
    if EVENT_SNAPSHOTS_ENABLED:
        EVENT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        cleanup_event_snapshots()


def record_event_error(error: Exception) -> None:
    global _last_error
    _last_error = str(error)


def phone_confidence(analysis: dict) -> float | None:
    confidences = []
    for detection in analysis.get("detections") or []:
        label = str(detection.get("label") or "").strip().lower()
        if label not in {"cell phone", "phone"}:
            continue
        try:
            confidences.append(float(detection.get("confidence")))
        except (TypeError, ValueError):
            continue
    return max(confidences) if confidences else None


def cooldown_ready(
    event_type: str,
    session_id: str | int | None,
    device_name: str | None,
    now: datetime,
) -> bool:
    key = (event_type, str(session_id or ""), str(device_name or ""))
    last_event_at = _last_event_at.get(key)
    if last_event_at is None:
        return True
    return (now - last_event_at).total_seconds() >= EVENT_COOLDOWN_SECONDS


def mark_event_cooldown(
    event_type: str,
    session_id: str | int | None,
    device_name: str | None,
    now: datetime,
) -> None:
    key = (event_type, str(session_id or ""), str(device_name or ""))
    _last_event_at[key] = now


def qualifying_events(
    analysis: dict,
    session_id: str | int | None,
    device_name: str | None,
    previous_light: dict | None,
    current_light: dict | None,
    now: datetime,
) -> list[dict]:
    events: list[dict] = []
    confidence = phone_confidence(analysis)

    if (
        session_id
        and confidence is not None
        and confidence >= PHONE_EVENT_CONFIDENCE
        and cooldown_ready("phone_detected", session_id, device_name, now)
    ):
        events.append(
            {
                "event_type": "phone_detected",
                "confidence": round(confidence, 3),
            }
        )

    previous_light = previous_light or {}
    current_light = current_light or {}
    was_on = bool(previous_light.get("light_1")) or bool(
        previous_light.get("light_2")
    )
    is_off = not bool(current_light.get("light_1")) and not bool(
        current_light.get("light_2")
    )
    if (
        was_on
        and is_off
        and cooldown_ready("light_auto_off", session_id, device_name, now)
    ):
        events.append({"event_type": "light_auto_off", "confidence": None})

    # Unexpected presence is intentionally not enabled until reliable
    # schedule and empty-room context are available to the sampler.
    return events


def safe_suffix(source_filename: str) -> str:
    suffix = Path(source_filename).suffix.lower()
    return suffix if suffix in EVENT_FILE_SUFFIXES else ".jpg"


def save_event_evidence(
    source_filename: str,
    image_bytes: bytes,
    snapshot: dict,
    analysis: dict,
    events: list[dict],
    now: datetime,
) -> dict | None:
    global _last_error

    if not events or source_filename in _saved_source_files:
        return None

    EVENT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    primary_event = events[0]["event_type"]
    source_hash = sha256(image_bytes).hexdigest()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    filename = (
        f"{primary_event}_{timestamp}_{source_hash[:8]}"
        f"{safe_suffix(source_filename)}"
    )
    final_path = EVENT_SNAPSHOT_DIR / filename
    temporary_path = EVENT_SNAPSHOT_DIR / f".{uuid4().hex}.tmp"

    try:
        temporary_path.write_bytes(image_bytes)
        temporary_path.replace(final_path)
    except OSError as error:
        _last_error = str(error)
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        return None

    _saved_source_files.add(source_filename)
    for event in events:
        mark_event_cooldown(
            event["event_type"],
            snapshot.get("session_id"),
            snapshot.get("device_name"),
            now,
        )

    metadata = {
        "event_type": primary_event,
        "event_types": [event["event_type"] for event in events],
        "filename": filename,
        "url": f"{EVENT_SNAPSHOT_URL_PREFIX}/{filename}",
        "source_filename": source_filename,
        "source_sha256": source_hash,
        "session_id": snapshot.get("session_id"),
        "device_name": snapshot.get("device_name"),
        "person_count": int(analysis.get("person_count") or 0),
        "phone_count": int(analysis.get("phone_count") or 0),
        "confidence": next(
            (
                event.get("confidence")
                for event in events
                if event.get("confidence") is not None
            ),
            None,
        ),
        "created_at": time_label(now),
    }
    _recent_events.insert(0, metadata)
    del _recent_events[RECENT_EVENT_LIMIT:]
    _last_error = None
    cleanup_event_snapshots(now)
    return metadata


def evaluate_sampled_frame(
    snapshot: dict,
    image_bytes: bytes,
    analysis: dict,
    previous_light: dict | None,
    current_light: dict | None,
) -> dict | None:
    global _last_error

    if not EVENT_SNAPSHOTS_ENABLED or not analysis.get("available"):
        return None

    source_filename = str(snapshot.get("filename") or "").strip()
    if not source_filename or not image_bytes:
        return None
    if source_filename in _saved_source_files:
        return None

    now = utc_now()
    try:
        events = qualifying_events(
            analysis=analysis,
            session_id=snapshot.get("session_id"),
            device_name=snapshot.get("device_name"),
            previous_light=previous_light,
            current_light=current_light,
            now=now,
        )
        return save_event_evidence(
            source_filename=source_filename,
            image_bytes=image_bytes,
            snapshot=snapshot,
            analysis=analysis,
            events=events,
            now=now,
        )
    except Exception as error:
        _last_error = str(error)
        return None
