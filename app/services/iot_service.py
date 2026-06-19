from datetime import datetime
from pathlib import Path
from uuid import uuid4

DEVICE_NAME_DEFAULT = "Raspberry Pi 5"
HEARTBEAT_TIMEOUT_SECONDS = 15
SNAPSHOT_UPLOAD_DIR = Path("app/static/uploads/iot_snapshots")
SNAPSHOT_URL_PREFIX = "/static/uploads/iot_snapshots"

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
    }


def save_camera_snapshot(
    image_bytes: bytes,
    original_filename: str | None = None,
    device_name: str | None = None,
    ip_address: str | None = None,
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

    _camera_snapshot_state.update(
        {
            "filename": filename,
            "url": f"{SNAPSHOT_URL_PREFIX}/{filename}",
            "uploaded_at": now,
            "device_name": clean_device_name,
            "ip_address": clean_ip_address,
            "size_bytes": len(image_bytes),
        }
    )

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
        }
    )
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
    }


def reset_device_state() -> dict:
    _device_state["device_name"] = DEVICE_NAME_DEFAULT
    _device_state["last_seen_at"] = None
    _device_state["ip_address"] = None
    return device_status()
