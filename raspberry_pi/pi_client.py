import time
from datetime import datetime

import requests


BACKEND_URL = "http://127.0.0.1:8000"
DEVICE_NAME = "Raspberry Pi 5"
HEARTBEAT_INTERVAL_SECONDS = 5

_last_light_state = {
    "light_1_label": None,
    "light_2_label": None,
}


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


def main():
    print("Smart Classroom Raspberry Pi Client")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Device Name: {DEVICE_NAME}")
    print("Mode: Software light demo only")
    print("Press Ctrl + C to stop.\n")

    try:
        while True:
            send_heartbeat()

            light = fetch_light_status()
            print_light_status_if_changed(light)

            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nRaspberry Pi client stopped.")


if __name__ == "__main__":
    main()