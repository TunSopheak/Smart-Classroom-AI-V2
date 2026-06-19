# Raspberry Pi Demo Guide

This guide explains how to run the Raspberry Pi client for the Smart Classroom AI Monitoring project.

## Current Raspberry Pi Role

The Raspberry Pi works as an IoT client device.

- It sends a heartbeat to the backend every 5 seconds.
- It shows as Online/Offline on the AI Monitoring dashboard.
- It reads Light 1 and Light 2 state from the backend.
- It is currently a safe software-only light demo. Real GPIO/relay control can be added later.

## Network Setup

Use the same network for both devices:

1. Turn on the phone hotspot.
2. Connect the laptop to the hotspot.
3. Power on the Raspberry Pi.
4. Wait 2-3 minutes for the Raspberry Pi to boot.

Example hotspot used during testing:

```text
SSID: SmartClassroom
```

## First-Time Raspberry Pi Setup

If the Raspberry Pi is newly prepared, install the required tools first:

```bash
sudo apt update
sudo apt install -y git python3-requests
```

Clone the project if it is not already on the Raspberry Pi:

```bash
git clone https://github.com/TunSopheak/Smart-Classroom-AI-V2.git
```

If the project folder already exists, use `git pull` instead of cloning again.

## 1. Start Backend Server on Laptop

Open PowerShell on the laptop and go to the project folder:

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2"
```

Run FastAPI so other devices on the same network can access it:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Keep this PowerShell window open.

## 2. Find Laptop IP Address

Open another PowerShell window and run:

```powershell
ipconfig
```

Look for:

```text
Wireless LAN adapter Wi-Fi
IPv4 Address
```

Example from successful testing:

```text
Laptop IP: 10.86.94.199
```

Note: The IP address can change when restarting the hotspot or reconnecting Wi-Fi.

## 3. SSH into Raspberry Pi

From PowerShell on the laptop:

```powershell
ssh sopheak@smart-classroom-pi.local
```

If it asks for a password, type the Raspberry Pi password. The password will not show while typing.

## 4. Run Raspberry Pi Client

Inside the Raspberry Pi terminal:

```bash
cd Smart-Classroom-AI-V2
git pull
```

Set the backend URL using the laptop IP address:

```bash
export SMART_CLASSROOM_BACKEND_URL="http://<LAPTOP_IP>:8000"
```

Example:

```bash
export SMART_CLASSROOM_BACKEND_URL="http://10.86.94.199:8000"
```

Run the client:

```bash
python3 raspberry_pi/pi_client.py
```

Expected output:

```text
Smart Classroom Raspberry Pi Client
Backend URL: http://10.86.94.199:8000
Device Name: Raspberry Pi 5
Mode: Software light demo only
Heartbeat sent | Status: Online
Light state | Light 1: OFF | Light 2: OFF | Mode: Software Demo
```

## 5. Open Dashboard

On the laptop browser:

```text
http://127.0.0.1:8000/ai-monitoring
```

Expected result:

- Raspberry Pi Device Status shows Online.
- The dashboard shows the Raspberry Pi IP address.
- Light 1 and Light 2 buttons can be clicked.
- The Raspberry Pi terminal prints updated light states.

## 6. Stop the Client

In the Raspberry Pi terminal:

```text
Ctrl + C
```

## 7. Safe Shutdown Raspberry Pi

Run this command before removing power:

```bash
sudo shutdown now
```

Wait around 30-60 seconds. When the fan becomes quiet and only the red power light remains, it is safe to unplug the USB-C power cable.

## Troubleshooting

### Raspberry Pi shows Offline

Check these points:

- Laptop backend server is still running.
- Backend was started with `--host 0.0.0.0`.
- Laptop and Raspberry Pi are on the same hotspot/Wi-Fi.
- The laptop IP address in `SMART_CLASSROOM_BACKEND_URL` is correct.
- Windows Firewall is not blocking port 8000.

### Test backend from Raspberry Pi

Inside Raspberry Pi terminal:

```bash
python3 - <<'PY'
import requests
print(requests.get("http://<LAPTOP_IP>:8000/iot/health", timeout=5).text)
PY
```

Replace `<LAPTOP_IP>` with the real laptop IP address.

## Demo Status

Successfully tested:

- Raspberry Pi boot
- SSH login
- Internet access
- Git clone
- Backend connection
- Heartbeat to dashboard
- Dashboard shows Raspberry Pi Online
- Light ON/OFF software demo
- Safe shutdown
