import time
from datetime import datetime

import requests


BACKEND_URL = "http://127.0.0.1:8000"
DEVICE_NAME = "Raspberry Pi 5"
HEARTBEAT_INTERVAL_SECONDS = 5


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
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Heartbeat sent | "
            f"Status: {device.get('status')} | "
            f"Last seen: {device.get('last_seen_at')}"
        )
        return True

    except requests.RequestException as error:
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Heartbeat failed: {error}"
        )
        return False


def main():
    print("Smart Classroom Raspberry Pi Client")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Device Name: {DEVICE_NAME}")
    print("Press Ctrl + C to stop.\n")

    try:
        while True:
            send_heartbeat()
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nRaspberry Pi client stopped.")


if __name__ == "__main__":
    main()