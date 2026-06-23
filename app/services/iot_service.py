import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services import behavior_overlay_service

DEVICE_NAME_DEFAULT = "Raspberry Pi 5"
HEARTBEAT_TIMEOUT_SECONDS = 15
SNAPSHOT_FRESHNESS_SECONDS = 45
SNAPSHOT_UPLOAD_DIR = Path("app/static/uploads/iot_snapshots")
SNAPSHOT_URL_PREFIX = "/static/uploads/iot_snapshots"
SNAPSHOT_MAX_FILES = int(os.getenv("SMART_CLASSROOM_SNAPSHOT_MAX_FILES", "30"))

_device_state: dict = {
    "device_name": DEVICE_NAME_DEFAULT,
    "last_seen_at": None,
    "ip_address": None,
}

_light_state: dict = {
    "light_1": False,
    "light_2": False,
    "updated_at": None,
}

_camera_snapshot_state: dict = {
    "filename": None,
    "url": None,
    "uploaded_at": None,
    "device_name": None,
    "ip_address": None,
    "size_bytes": None,
    "session_id": None,
}

_camera_analysis_state: dict = {
    "available": False,
    "analyzed_at": None,
    "analysis": None,
    "occupancy": None,
    "occupancy_synced": False,
    "occupancy_error": None,
    "session_sync_status": "missing",
    "session_sync_message": "Occupancy sync is waiting for an active session.",
    "session_id": None,
    "light": None,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_datetime(value) -> str | None:
    normalized = normalize_datetime(value)
    if normalized is None:
        return None
    return normalized.strftime("%Y-%m-%d %H:%M:%S")


def normalize_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_snapshot_uploaded_at(value) -> datetime | None:
    """Parse snapshot timestamps as UTC, including legacy naive UTC strings."""

    return normalize_datetime(value)


def compute_snapshot_age_seconds(
    uploaded_at,
    now: datetime | None = None,
) -> int | None:
    uploaded_time = parse_snapshot_uploaded_at(uploaded_at)
    if uploaded_time is None:
        return None
    current_time = normalize_datetime(now) or utc_now()
    return max(0, int((current_time - uploaded_time).total_seconds()))


def is_snapshot_fresh(
    uploaded_at,
    now: datetime | None = None,
    freshness_seconds: int = SNAPSHOT_FRESHNESS_SECONDS,
) -> bool:
    age = compute_snapshot_age_seconds(uploaded_at, now)
    return age is not None and age <= freshness_seconds


def build_device_status(
    device_state: dict | None = None,
    snapshot_state: dict | None = None,
    now: datetime | None = None,
) -> dict:
    device_state = device_state if isinstance(device_state, dict) else {}
    snapshot_state = snapshot_state if isinstance(snapshot_state, dict) else {}
    current_time = normalize_datetime(now) or utc_now()
    heartbeat_at = normalize_datetime(device_state.get("last_seen_at"))
    snapshot_at = parse_snapshot_uploaded_at(snapshot_state.get("uploaded_at"))
    heartbeat_age = compute_snapshot_age_seconds(heartbeat_at, current_time)
    snapshot_age = compute_snapshot_age_seconds(snapshot_at, current_time)
    heartbeat_online = (
        heartbeat_age is not None and heartbeat_age <= HEARTBEAT_TIMEOUT_SECONDS
    )
    snapshot_available_value = snapshot_state.get("available")
    snapshot_available = (
        bool(snapshot_at)
        if snapshot_available_value is None
        else bool(snapshot_available_value)
    )
    snapshot_upload_online = snapshot_available and is_snapshot_fresh(
        snapshot_at,
        current_time,
    )
    online = heartbeat_online or snapshot_upload_online

    if heartbeat_online and snapshot_upload_online:
        status_source = "Heartbeat + Snapshot Upload"
    elif snapshot_upload_online:
        status_source = "Snapshot Upload"
    elif heartbeat_online:
        status_source = "Heartbeat"
    else:
        status_source = "No Fresh Signal"

    has_stale_signal = heartbeat_at is not None or snapshot_at is not None
    status_label = (
        "Online" if online else ("Stale" if has_stale_signal else "Offline")
    )
    activity_times = [value for value in (heartbeat_at, snapshot_at) if value]
    last_activity_at = max(activity_times) if activity_times else None
    last_activity_age = compute_snapshot_age_seconds(last_activity_at, current_time)

    if heartbeat_online and snapshot_upload_online:
        message = "Raspberry Pi is online from heartbeat and recent snapshot uploads."
    elif snapshot_upload_online:
        message = "Raspberry Pi is online from recent snapshot uploads."
    elif heartbeat_online:
        message = "Raspberry Pi is online from heartbeat."
    elif snapshot_at is not None:
        message = (
            "Latest Raspberry Pi snapshot is stale. Waiting for a new snapshot "
            "upload or heartbeat."
        )
    elif has_stale_signal:
        message = "Raspberry Pi heartbeat is stale. Waiting for fresh activity."
    else:
        message = "No Raspberry Pi heartbeat or snapshot upload has been received yet."

    prefer_snapshot_identity = snapshot_upload_online and not heartbeat_online
    device_name = (
        snapshot_state.get("device_name")
        if prefer_snapshot_identity
        else device_state.get("device_name")
    ) or snapshot_state.get("device_name") or DEVICE_NAME_DEFAULT
    ip_address = device_state.get("ip_address") or snapshot_state.get(
        "ip_address"
    )

    return {
        "device_name": device_name,
        "online": online,
        "status": status_label,
        "status_label": status_label,
        "status_source": status_source,
        "heartbeat_online": heartbeat_online,
        "snapshot_upload_online": snapshot_upload_online,
        "latest_snapshot_age_seconds": snapshot_age,
        "last_snapshot_uploaded_at": format_datetime(snapshot_at),
        "last_seen_at": format_datetime(last_activity_at),
        "seconds_since_last_seen": last_activity_age,
        "heartbeat_last_seen_at": format_datetime(heartbeat_at),
        "heartbeat_age_seconds": heartbeat_age,
        "ip_address": ip_address,
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "snapshot_freshness_seconds": SNAPSHOT_FRESHNESS_SECONDS,
        "message": message,
    }


def build_session_sync_status(
    session_id: str | int | None,
    occupancy_synced: bool,
    occupancy_error: str | None = None,
) -> dict:
    clean_session_id = str(session_id or "").strip()
    if occupancy_synced:
        return {
            "session_sync_status": "active",
            "session_sync_message": (
                "AI analysis completed and occupancy synced to the active session."
            ),
        }
    if not clean_session_id:
        return {
            "session_sync_status": "missing",
            "session_sync_message": (
                "AI analysis completed. Occupancy sync skipped until an active "
                "session is selected."
            ),
        }
    if occupancy_error:
        return {
            "session_sync_status": "not_active",
            "session_sync_message": (
                "AI analysis completed. Occupancy sync skipped because the "
                "snapshot session is no longer active."
            ),
        }
    return {
        "session_sync_status": "not_active",
        "session_sync_message": "AI analysis completed. Occupancy sync was not applied to an active session.",
    }


def seconds_since_last_seen(now: datetime | None = None) -> int | None:
    last_seen_at = normalize_datetime(_device_state.get("last_seen_at"))
    if last_seen_at is None:
        return None

    current_time = normalize_datetime(now) or utc_now()
    return max(0, int((current_time - last_seen_at).total_seconds()))


def is_device_online(now: datetime | None = None) -> bool:
    return bool(build_device_status(_device_state, _camera_snapshot_state, now)["online"])


def record_heartbeat(
    device_name: str | None = None,
    ip_address: str | None = None,
) -> dict:
    now = utc_now()

    clean_device_name = (device_name or "").strip() or DEVICE_NAME_DEFAULT
    clean_ip_address = (ip_address or "").strip() or None

    _device_state["device_name"] = clean_device_name
    _device_state["last_seen_at"] = now

    if clean_ip_address:
        _device_state["ip_address"] = clean_ip_address

    return device_status(now)


def light_label(value: bool) -> str:
    return "ON" if value else "OFF"


def normalize_light_value(value) -> bool | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    clean_value = str(value).strip().lower()

    if clean_value in {"on", "true", "1", "yes"}:
        return True

    if clean_value in {"off", "false", "0", "no"}:
        return False

    return None


def light_status() -> dict:
    light_1 = bool(_light_state.get("light_1"))
    light_2 = bool(_light_state.get("light_2"))

    return {
        "light_1": light_1,
        "light_2": light_2,
        "light_1_label": light_label(light_1),
        "light_2_label": light_label(light_2),
        "updated_at": format_datetime(_light_state.get("updated_at")),
        "mode": "Software Demo",
    }


def update_light_state(
    light_1=None,
    light_2=None,
) -> dict:
    new_light_1 = normalize_light_value(light_1)
    new_light_2 = normalize_light_value(light_2)

    if new_light_1 is not None:
        _light_state["light_1"] = new_light_1

    if new_light_2 is not None:
        _light_state["light_2"] = new_light_2

    _light_state["updated_at"] = utc_now()
    return light_status()


def reset_light_state() -> dict:
    _light_state["light_1"] = False
    _light_state["light_2"] = False
    _light_state["updated_at"] = utc_now()
    return light_status()


def snapshot_status() -> dict:
    uploaded_at = _camera_snapshot_state.get("uploaded_at")
    return {
        "available": bool(_camera_snapshot_state.get("url")),
        "filename": _camera_snapshot_state.get("filename"),
        "url": _camera_snapshot_state.get("url"),
        "uploaded_at": format_datetime(uploaded_at),
        "device_name": _camera_snapshot_state.get("device_name"),
        "ip_address": _camera_snapshot_state.get("ip_address"),
        "size_bytes": _camera_snapshot_state.get("size_bytes"),
        "session_id": _camera_snapshot_state.get("session_id"),
    }


def analysis_status() -> dict:
    analyzed_at = _camera_analysis_state.get("analyzed_at")
    return {
        "available": bool(_camera_analysis_state.get("available")),
        "analyzed_at": format_datetime(analyzed_at),
        "analysis": _camera_analysis_state.get("analysis"),
        "occupancy": _camera_analysis_state.get("occupancy"),
        "occupancy_synced": bool(_camera_analysis_state.get("occupancy_synced")),
        "occupancy_error": _camera_analysis_state.get("occupancy_error"),
        "session_sync_status": _camera_analysis_state.get("session_sync_status"),
        "session_sync_message": _camera_analysis_state.get("session_sync_message"),
        "session_id": _camera_analysis_state.get("session_id"),
        "light": _camera_analysis_state.get("light"),
    }


def save_camera_analysis(
    analysis: dict | None,
    occupancy: dict | None = None,
    occupancy_synced: bool = False,
    occupancy_error: str | None = None,
    light: dict | None = None,
    session_id: str | int | None = None,
) -> dict:
    enriched_analysis = (
        behavior_overlay_service.enrich_analysis_for_behavior_overlay(analysis)
        if analysis
        else analysis
    )
    session_sync = build_session_sync_status(
        session_id,
        occupancy_synced,
        occupancy_error,
    )
    _camera_analysis_state.update(
        {
            "available": bool(enriched_analysis),
            "analyzed_at": utc_now(),
            "analysis": enriched_analysis,
            "occupancy": occupancy,
            "occupancy_synced": occupancy_synced,
            "occupancy_error": occupancy_error,
            **session_sync,
            "session_id": str(session_id or "").strip() or None,
            "light": light or light_status(),
        }
    )
    return analysis_status()


def reset_camera_analysis() -> dict:
    _camera_analysis_state.update(
        {
            "available": False,
            "analyzed_at": None,
            "analysis": None,
            "occupancy": None,
            "occupancy_synced": False,
            "occupancy_error": None,
            "session_sync_status": "missing",
            "session_sync_message": "Occupancy sync is waiting for an active session.",
            "session_id": None,
            "light": None,
        }
    )
    return analysis_status()


def snapshot_file_list() -> list[Path]:
    if not SNAPSHOT_UPLOAD_DIR.exists():
        return []

    files: list[Path] = []
    for pattern in ("*.jpg", "*.jpeg", "*.png"):
        files.extend(SNAPSHOT_UPLOAD_DIR.glob(pattern))

    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def snapshot_storage_status() -> dict:
    files = snapshot_file_list()
    total_size = sum(path.stat().st_size for path in files if path.exists())
    return {
        "directory": str(SNAPSHOT_UPLOAD_DIR),
        "file_count": len(files),
        "total_size_bytes": total_size,
        "max_files": SNAPSHOT_MAX_FILES,
    }


def cleanup_old_snapshots(keep_filename: str | None = None) -> dict:
    if SNAPSHOT_MAX_FILES <= 0:
        return snapshot_storage_status()

    files = snapshot_file_list()
    old_files = files[SNAPSHOT_MAX_FILES:]

    removed_count = 0
    removed_size = 0

    for path in old_files:
        if keep_filename and path.name == keep_filename:
            continue
        try:
            size = path.stat().st_size
            path.unlink()
            removed_count += 1
            removed_size += size
        except OSError:
            continue

    status = snapshot_storage_status()
    status.update(
        {
            "removed_count": removed_count,
            "removed_size_bytes": removed_size,
        }
    )
    return status


def save_camera_snapshot(
    image_bytes: bytes,
    original_filename: str | None = None,
    device_name: str | None = None,
    ip_address: str | None = None,
    session_id: str | int | None = None,
) -> dict:
    if not image_bytes:
        raise ValueError("Snapshot image is empty.")

    SNAPSHOT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    now = utc_now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = Path(original_filename or "snapshot.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"

    filename = f"pi_snapshot_{timestamp}_{uuid4().hex[:8]}{suffix}"
    file_path = SNAPSHOT_UPLOAD_DIR / filename
    file_path.write_bytes(image_bytes)

    clean_device_name = (device_name or "").strip() or DEVICE_NAME_DEFAULT
    clean_ip_address = (ip_address or "").strip() or None
    clean_session_id = str(session_id or "").strip() or None

    _camera_snapshot_state.update(
        {
            "filename": filename,
            "url": f"{SNAPSHOT_URL_PREFIX}/{filename}",
            "uploaded_at": now,
            "device_name": clean_device_name,
            "ip_address": clean_ip_address,
            "size_bytes": len(image_bytes),
            "session_id": clean_session_id,
        }
    )

    cleanup_old_snapshots(keep_filename=filename)
    reset_camera_analysis()
    return snapshot_status()


def reset_camera_snapshot() -> dict:
    _camera_snapshot_state.update(
        {
            "filename": None,
            "url": None,
            "uploaded_at": None,
            "device_name": None,
            "ip_address": None,
            "size_bytes": None,
            "session_id": None,
        }
    )
    reset_camera_analysis()
    return snapshot_status()


def device_status(now: datetime | None = None) -> dict:
    lights = light_status()
    snapshot = snapshot_status()
    status = build_device_status(_device_state, snapshot, now)
    status.update(
        {
            "light_1": lights["light_1"],
            "light_2": lights["light_2"],
            "light_1_label": lights["light_1_label"],
            "light_2_label": lights["light_2_label"],
            "snapshot": snapshot,
            "analysis": analysis_status(),
            "snapshot_storage": snapshot_storage_status(),
        }
    )
    return status


def reset_device_state() -> dict:
    _device_state["device_name"] = DEVICE_NAME_DEFAULT
    _device_state["last_seen_at"] = None
    _device_state["ip_address"] = None
    return device_status()
