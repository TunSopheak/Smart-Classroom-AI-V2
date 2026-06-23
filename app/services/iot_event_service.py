"""Conservative Raspberry Pi event-evidence storage for sampled frames."""

import json
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.config import (
    BASE_DIR,
    EVENT_COOLDOWN_SECONDS,
    EVENT_SNAPSHOT_MAX_FILES,
    EVENT_SNAPSHOT_RETENTION_DAYS,
    EVENT_SNAPSHOTS_ENABLED,
    PHONE_EVENT_CONFIDENCE,
)


EVENT_SNAPSHOT_DIR = BASE_DIR / "app" / "static" / "uploads" / "iot_events"
EVENT_SNAPSHOT_URL_PREFIX = "/static/uploads/iot_events"
EVENT_FILE_SUFFIXES = {".jpg", ".jpeg", ".png"}
RECENT_EVENT_LIMIT = 10
EVENT_FILENAME_PATTERN = re.compile(
    r"^(?P<event_type>.+)_(?P<date>\d{8})_(?P<time>\d{6})_"
    r"(?P<microseconds>\d{6})_[0-9a-fA-F]{8}$"
)
EVENT_REASON_LABELS = {
    "phone_usage": "Phone-like object detected above confidence threshold.",
    "light_auto_off": "Classroom lights transitioned to auto-off.",
}
EVENT_TITLE_LABELS = {
    "phone_usage": "Possible phone usage detected",
    "light_auto_off": "Lights auto-off evidence",
}
PHONE_LABELS = {"phone", "cell phone", "mobile phone"}
PHONE_COMPACT_LABELS = {
    "cellphone",
    "mobilephone",
    "smartphone",
    "telephone",
}

_recent_events: list[dict] = []
_saved_source_files: set[str] = set()
_last_event_at: dict[tuple[str, str, str], datetime] = {}
_last_error: str | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_from_timestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)


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


def inferred_event_details(path: Path) -> dict:
    try:
        stat = path.stat()
    except OSError:
        stat = None

    created_at = None
    match = EVENT_FILENAME_PATTERN.match(path.stem)
    if match:
        try:
            created_at = datetime.strptime(
                "".join(
                    (
                        match.group("date"),
                        match.group("time"),
                        match.group("microseconds"),
                    )
                ),
                "%Y%m%d%H%M%S%f",
            )
        except ValueError:
            created_at = None

    modified_at = utc_from_timestamp(stat.st_mtime) if stat else None
    evidence_time = created_at or modified_at
    return {
        "event_type": "ai_evidence",
        "event_types": ["ai_evidence"],
        "event_type_label": "AI Evidence",
        "title": "AI evidence",
        "filename": path.name,
        "url": f"{EVENT_SNAPSHOT_URL_PREFIX}/{path.name}",
        "image_url": f"{EVENT_SNAPSHOT_URL_PREFIX}/{path.name}",
        "created_at": time_label(evidence_time),
        "modified_at": time_label(modified_at),
        "size_bytes": stat.st_size if stat else None,
        "reason": "Alert-worthy AI evidence retained for review.",
        "confidence": None,
        "label": None,
        "source_snapshot_filename": None,
    }


def read_event_metadata(path: Path) -> dict:
    metadata_path = path.with_suffix(".json")
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def recent_event_files(files: list[Path] | None = None) -> list[dict]:
    live_metadata = {
        event.get("filename"): event
        for event in _recent_events
        if event.get("filename")
    }
    recent: list[dict] = []
    candidates = event_files() if files is None else files
    for path in candidates[:RECENT_EVENT_LIMIT]:
        inferred = inferred_event_details(path)
        persisted_metadata = read_event_metadata(path)
        if persisted_metadata:
            inferred.update(persisted_metadata)
        live_event = live_metadata.get(path.name)
        if live_event:
            inferred.update(live_event)
        event_type = str(inferred.get("event_type") or "ai_evidence")
        if event_type == "phone_usage":
            inferred["event_type_label"] = "Phone Usage"
        elif event_type == "ai_evidence":
            inferred["event_type_label"] = "AI Evidence"
        else:
            inferred["event_type_label"] = event_type.replace("_", " ").title()
        inferred["filename"] = path.name
        inferred["url"] = f"{EVENT_SNAPSHOT_URL_PREFIX}/{path.name}"
        inferred["image_url"] = inferred["url"]
        try:
            inferred["size_bytes"] = path.stat().st_size
        except OSError:
            pass
        inferred.setdefault(
            "title",
            EVENT_TITLE_LABELS.get(event_type, "AI evidence"),
        )
        inferred.setdefault(
            "reason",
            EVENT_REASON_LABELS.get(
                event_type,
                "Alert-worthy AI evidence retained for review.",
            ),
        )
        recent.append(inferred)
    return recent


def prune_recent_events() -> None:
    retained_names = {path.name for path in event_files()}
    _recent_events[:] = [
        event
        for event in _recent_events
        if event.get("filename") in retained_names
    ][:RECENT_EVENT_LIMIT]


def delete_event_evidence(path: Path) -> None:
    path.unlink()
    path.with_suffix(".json").unlink(missing_ok=True)


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
            modified_at = utc_from_timestamp(path.stat().st_mtime)
            if modified_at < cutoff:
                delete_event_evidence(path)
                removed_count += 1
        except OSError as error:
            errors.append(str(error))

    for path in event_files()[EVENT_SNAPSHOT_MAX_FILES:]:
        try:
            delete_event_evidence(path)
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
        "recent_events": recent_event_files(files),
        "last_error": _last_error,
    }


def initialize_event_storage() -> None:
    if EVENT_SNAPSHOTS_ENABLED:
        EVENT_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        cleanup_event_snapshots()


def record_event_error(error: Exception) -> None:
    global _last_error
    _last_error = str(error)


def normalize_detection_label(label: object) -> str:
    return " ".join(
        str(label or "")
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def is_phone_label(label: object) -> bool:
    normalized = normalize_detection_label(label)
    if normalized in PHONE_LABELS:
        return True
    words = set(normalized.split())
    compact = normalized.replace(" ", "")
    return bool(words.intersection({"phone", "telephone"})) or (
        compact in PHONE_COMPACT_LABELS
    )


def strongest_phone_detection(analysis: dict) -> dict | None:
    matches: list[dict] = []
    for detection in analysis.get("detections") or []:
        if not isinstance(detection, dict) or not is_phone_label(
            detection.get("label")
        ):
            continue
        try:
            confidence = float(detection.get("confidence"))
        except (TypeError, ValueError):
            continue
        matches.append(
            {
                "label": str(detection.get("label") or "phone").strip(),
                "confidence": confidence,
                "box": detection.get("box"),
            }
        )
    return max(matches, key=lambda item: item["confidence"]) if matches else None


def qualifying_phone_detection(
    analysis: dict,
    threshold: float = PHONE_EVENT_CONFIDENCE,
) -> dict | None:
    detection = strongest_phone_detection(analysis)
    if detection is None or detection["confidence"] < threshold:
        return None
    return detection


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
    phone_detection = qualifying_phone_detection(analysis)

    if (
        phone_detection is not None
        and cooldown_ready("phone_usage", session_id, device_name, now)
    ):
        events.append(
            {
                "event_type": "phone_usage",
                "title": EVENT_TITLE_LABELS["phone_usage"],
                "reason": EVENT_REASON_LABELS["phone_usage"],
                "confidence": round(phone_detection["confidence"], 3),
                "label": phone_detection["label"],
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
        events.append(
            {
                "event_type": "light_auto_off",
                "title": EVENT_TITLE_LABELS["light_auto_off"],
                "reason": EVENT_REASON_LABELS["light_auto_off"],
                "confidence": None,
                "label": None,
            }
        )

    # Unexpected presence is intentionally not enabled until reliable
    # schedule and empty-room context are available to the sampler.
    return events


def safe_suffix(source_filename: str) -> str:
    suffix = Path(source_filename).suffix.lower()
    return suffix if suffix in EVENT_FILE_SUFFIXES else ".jpg"


def write_event_metadata(image_path: Path, metadata: dict) -> None:
    metadata_path = image_path.with_suffix(".json")
    temporary_path = EVENT_SNAPSHOT_DIR / f".{uuid4().hex}.json.tmp"
    try:
        temporary_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(metadata_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


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

    primary_details = events[0]
    metadata = {
        "event_type": primary_event,
        "event_types": [event["event_type"] for event in events],
        "title": primary_details.get("title")
        or EVENT_TITLE_LABELS.get(primary_event, "AI evidence"),
        "reason": primary_details.get("reason")
        or EVENT_REASON_LABELS.get(
            primary_event,
            "Alert-worthy AI evidence retained for review.",
        ),
        "label": primary_details.get("label"),
        "filename": filename,
        "url": f"{EVENT_SNAPSHOT_URL_PREFIX}/{filename}",
        "image_filename": filename,
        "image_url": f"{EVENT_SNAPSHOT_URL_PREFIX}/{filename}",
        "source_snapshot_filename": source_filename,
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
    metadata_error = None
    try:
        write_event_metadata(final_path, metadata)
    except OSError as error:
        metadata_error = f"Evidence image saved, but metadata could not be saved: {error}"

    _recent_events.insert(0, metadata)
    del _recent_events[RECENT_EVENT_LIMIT:]
    cleanup_event_snapshots(now)
    if metadata_error:
        _last_error = "; ".join(filter(None, (_last_error, metadata_error)))
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
