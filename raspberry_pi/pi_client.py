import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests


BACKEND_URL = os.getenv(
    "SMART_CLASSROOM_BACKEND_URL",
    "http://127.0.0.1:8000",
).rstrip("/")
DEVICE_NAME = "Raspberry Pi 5"
HEARTBEAT_INTERVAL_SECONDS = 5
CAMERA_ENABLED = os.getenv("SMART_CLASSROOM_ENABLE_CAMERA", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CAMERA_INTERVAL_SECONDS = int(os.getenv("SMART_CLASSROOM_CAMERA_INTERVAL", "30"))
CAMERA_SNAPSHOT_PATH = Path(os.getenv("SMART_CLASSROOM_CAMERA_PATH", "/tmp/smart_classroom_snapshot.jpg"))

_last_light_state = {
    "light_1_label": None,
    "light_2_label": None,
}
_last_camera_upload_at = 0.0


def current_time_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send_heartbeat() -> bool:
    url = f"{BACKEND_URL}/iot/device/heartbeat"

    payload = {
        "device_name": DEVICE_NAME,
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()

        data = response.json()
        device = data.get("device", {})

        print(
            f"[{current_time_label()}] "
            f"Heartbeat sent | "
            f"Status: {device.get('status')} | "
            f"Last seen: {device.get('last_seen_at')}"
        )
        return True

    except requests.RequestException as error:
        print(f"[{current_time_label()}] Heartbeat failed: {error}")
        return False


def fetch_light_status() -> dict | None:
    url = f"{BACKEND_URL}/iot/light/status"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        return data.get("light", {})

    except requests.RequestException as error:
        print(f"[{current_time_label()}] Light status failed: {error}")
        return None


def print_light_status_if_changed(light: dict | None) -> None:
    if not light:
        return

    light_1_label = light.get("light_1_label", "OFF")
    light_2_label = light.get("light_2_label", "OFF")

    changed = (
        light_1_label != _last_light_state["light_1_label"]
        or light_2_label != _last_light_state["light_2_label"]
    )

    if not changed:
        return

    _last_light_state["light_1_label"] = light_1_label
    _last_light_state["light_2_label"] = light_2_label

    print(
        f"[{current_time_label()}] "
        f"Light state | "
        f"Light 1: {light_1_label} | "
        f"Light 2: {light_2_label} | "
        f"Mode: {light.get('mode', 'Software Demo')}"
    )

    # Real GPIO/relay control will be added later.
    # For now, this is a safe software-only demo.


def capture_camera_snapshot() -> bool:
    command = [
        "rpicam-still",
        "--output",
        str(CAMERA_SNAPSHOT_PATH),
        "--timeout",
        "1500",
        "--nopreview",
    ]

    try:
        subprocess.run(command, check=True, timeout=15)
        return CAMERA_SNAPSHOT_PATH.exists() and CAMERA_SNAPSHOT_PATH.stat().st_size > 0
    except (subprocess.SubprocessError, OSError) as error:
        print(f"[{current_time_label()}] Camera capture failed: {error}")
        return False


def upload_camera_snapshot() -> bool:
    url = f"{BACKEND_URL}/iot/camera/snapshot"

    try:
        with CAMERA_SNAPSHOT_PATH.open("rb") as image_file:
            files = {
                "snapshot": ("pi_client_snapshot.jpg", image_file, "image/jpeg"),
            }
            data = {
                "device_name": DEVICE_NAME,
            }
            response = requests.post(url, files=files, data=data, timeout=20)
            response.raise_for_status()

        snapshot = response.json().get("snapshot", {})
        print(
            f"[{current_time_label()}] "
            f"Camera snapshot uploaded | "
            f"URL: {snapshot.get('url')} | "
            f"Size: {snapshot.get('size_bytes')} bytes"
        )
        return True

    except (OSError, requests.RequestException) as error:
        print(f"[{current_time_label()}] Camera snapshot upload failed: {error}")
        return False


def maybe_capture_and_upload_camera_snapshot() -> None:
    global _last_camera_upload_at

    if not CAMERA_ENABLED:
        return

    now = time.time()
    if now - _last_camera_upload_at < CAMERA_INTERVAL_SECONDS:
        return

    _last_camera_upload_at = now

    if capture_camera_snapshot():
        upload_camera_snapshot()


def main():
    print("Smart Classroom Raspberry Pi Client")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Device Name: {DEVICE_NAME}")
    print("Mode: Software light demo only")
    print(f"Camera Snapshot Upload: {'Enabled' if CAMERA_ENABLED else 'Disabled'}")
    if CAMERA_ENABLED:
        print(f"Camera Snapshot Interval: {CAMERA_INTERVAL_SECONDS} seconds")
    print("Press Ctrl + C to stop.\n")

    try:
        while True:
            send_heartbeat()

            light = fetch_light_status()
            print_light_status_if_changed(light)

            maybe_capture_and_upload_camera_snapshot()

            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nRaspberry Pi client stopped.")


if __name__ == "__main__":
    main()
