import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

DEVICE_NAME_DEFAULT = "Raspberry Pi 5"
HEARTBEAT_TIMEOUT_SECONDS = 15
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
    "light": None,
}


def utc_now() -> datetime:
    return datetime.utcnow()


def format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S")


def seconds_since_last_seen(now: datetime | None = None) -> int | None:
    last_seen_at = _device_state.get("last_seen_at")
    if last_seen_at is None:
        return None

    current_time = now or utc_now()
    return max(0, int((current_time - last_seen_at).total_seconds()))


def is_device_online(now: datetime | None = None) -> bool:
    seconds = seconds_since_last_seen(now)
    if seconds is None:
        return False
    return seconds <= HEARTBEAT_TIMEOUT_SECONDS


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
        "light": _camera_analysis_state.get("light"),
    }


def save_camera_analysis(
    analysis: dict | None,
    occupancy: dict | None = None,
    occupancy_synced: bool = False,
    occupancy_error: str | None = None,
    light: dict | None = None,
) -> dict:
    _camera_analysis_state.update(
        {
            "available": bool(analysis),
            "analyzed_at": utc_now(),
            "analysis": analysis,
            "occupancy": occupancy,
            "occupancy_synced": occupancy_synced,
            "occupancy_error": occupancy_error,
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
    current_time = now or utc_now()
    last_seen_at = _device_state.get("last_seen_at")
    seconds = seconds_since_last_seen(current_time)
    online = is_device_online(current_time)
    lights = light_status()

    return {
        "device_name": _device_state.get("device_name") or DEVICE_NAME_DEFAULT,
        "online": online,
        "status": "Online" if online else "Offline",
        "last_seen_at": format_datetime(last_seen_at),
        "seconds_since_last_seen": seconds,
        "ip_address": _device_state.get("ip_address"),
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "light_1": lights["light_1"],
        "light_2": lights["light_2"],
        "light_1_label": lights["light_1_label"],
        "light_2_label": lights["light_2_label"],
        "snapshot": snapshot_status(),
        "analysis": analysis_status(),
        "snapshot_storage": snapshot_storage_status(),
    }


def reset_device_state() -> dict:
    _device_state["device_name"] = DEVICE_NAME_DEFAULT
    _device_state["last_seen_at"] = None
    _device_state["ip_address"] = None
    return device_status()
