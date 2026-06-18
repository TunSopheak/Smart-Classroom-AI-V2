from datetime import datetime

DEVICE_NAME_DEFAULT = "Raspberry Pi 5"
HEARTBEAT_TIMEOUT_SECONDS = 15

_device_state: dict = {
    "device_name": DEVICE_NAME_DEFAULT,
    "last_seen_at": None,
    "ip_address": None,
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


def device_status(now: datetime | None = None) -> dict:
    current_time = now or utc_now()
    last_seen_at = _device_state.get("last_seen_at")
    seconds = seconds_since_last_seen(current_time)
    online = is_device_online(current_time)

    return {
        "device_name": _device_state.get("device_name") or DEVICE_NAME_DEFAULT,
        "online": online,
        "status": "Online" if online else "Offline",
        "last_seen_at": format_datetime(last_seen_at),
        "seconds_since_last_seen": seconds,
        "ip_address": _device_state.get("ip_address"),
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
    }


def reset_device_state() -> dict:
    _device_state["device_name"] = DEVICE_NAME_DEFAULT
    _device_state["last_seen_at"] = None
    _device_state["ip_address"] = None
    return device_status()