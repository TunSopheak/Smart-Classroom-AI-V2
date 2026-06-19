# Final Demo Checklist

Smart Classroom AI Monitoring - Final Demo Preparation

## Demo Goal

Show that the Smart Classroom system can monitor classroom status, connect to a real Raspberry Pi device, and control classroom light status from the web dashboard.

## Main Demo Flow

```text
Laptop Backend + Web Dashboard
        |
        | Same Wi-Fi / Hotspot Network
        |
Raspberry Pi IoT Client
```

The teacher should see:

- Web dashboard is running.
- AI Monitoring page is accessible.
- Raspberry Pi device status is Online.
- Raspberry Pi IP address is displayed.
- Light 1 and Light 2 can be controlled from the dashboard.
- Raspberry Pi terminal receives updated light state.
- Auto light logic can update light state based on occupancy status.

## Equipment Checklist

Bring these items before the demo:

- Laptop with project source code
- Raspberry Pi 5
- Raspberry Pi microSD card
- Raspberry Pi USB-C power adapter/cable
- Raspberry Pi camera module and ribbon cable
- Phone hotspot or stable Wi-Fi network
- Phone charger or power bank
- Optional: mouse/keyboard/monitor if available
- Optional: extension cable

## Before Demo Day

Check these tasks one day before the demo:

- Pull latest code on laptop.
- Pull latest code on Raspberry Pi.
- Test backend server.
- Test AI Monitoring page.
- Test Raspberry Pi SSH login.
- Test Raspberry Pi client connection.
- Test Light 1 and Light 2 buttons.
- Prepare sample data / screenshots if live demo has network problems.

## Start Demo Step-by-Step

### 1. Turn on Network

Turn on phone hotspot or connect both devices to the same Wi-Fi.

Example tested hotspot:

```text
SSID: SmartClassroom
```

### 2. Connect Laptop to Network

Make sure the laptop is connected to the same hotspot/Wi-Fi as the Raspberry Pi.

### 3. Start Raspberry Pi

Plug in Raspberry Pi USB-C power.

Wait around 2-3 minutes for the Raspberry Pi to boot.

### 4. Find Laptop IP Address

Open PowerShell on the laptop:

```powershell
ipconfig
```

Find:

```text
Wireless LAN adapter Wi-Fi
IPv4 Address
```

Example from previous successful test:

```text
10.86.94.199
```

Note: The laptop IP address may change, so always check it before starting the Pi client.

### 5. Start Backend Server on Laptop

Open PowerShell on the laptop:

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Keep this terminal open.

Expected output:

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

### 6. Open Web Dashboard

Open browser on laptop:

```text
http://127.0.0.1:8000/dashboard
```

Then open AI Monitoring page:

```text
http://127.0.0.1:8000/ai-monitoring
```

### 7. SSH into Raspberry Pi

Open another PowerShell window:

```powershell
ssh sopheak@smart-classroom-pi.local
```

If the hostname does not work, use the Raspberry Pi IP address instead.

### 8. Run Raspberry Pi Client

Inside Raspberry Pi terminal:

```bash
cd Smart-Classroom-AI-V2
git pull
export SMART_CLASSROOM_BACKEND_URL="http://<LAPTOP_IP>:8000"
python3 raspberry_pi/pi_client.py
```

Example:

```bash
export SMART_CLASSROOM_BACKEND_URL="http://10.86.94.199:8000"
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

## Live Demo Script

Use this order when presenting:

### Part 1: System Overview

Explain:

```text
This project is Smart Classroom AI Monitoring. It combines a web dashboard, backend API, AI monitoring logic, and Raspberry Pi IoT device connection.
```

### Part 2: Web Dashboard

Show:

- Dashboard page
- AI Monitoring page
- Sessions button
- AI Events button

Explain:

```text
The dashboard is used by the teacher/admin to monitor classroom status, student attention events, device status, and light control.
```

### Part 3: Raspberry Pi Device Status

Show:

- Raspberry Pi Device Status card
- Online status
- Device name
- Last seen time
- IP address
- Seconds since last seen

Explain:

```text
The Raspberry Pi sends heartbeat data to the backend every few seconds. If the device is connected, the dashboard shows Online. If it stops sending heartbeat, the status will become Offline.
```

### Part 4: Light Control Demo

Click:

- Light 1 ON
- Light 1 OFF
- Light 2 ON
- Light 2 OFF

Show Raspberry Pi terminal printing the new light state.

Explain:

```text
The web dashboard sends the light command to the backend. The Raspberry Pi client reads the latest light state from the backend and prints the result. This is currently a safe software demo. A real relay module can be connected later for physical classroom light control.
```

### Part 5: Auto Light Logic

Explain:

```text
The system is designed to support automatic light control. If no students are detected for a period of time, the system can turn off the light automatically to save energy.
```

### Part 6: AI Monitoring and Reports

Show:

- AI Events page
- Report links if available
- Snapshots if available

Explain:

```text
The AI Monitoring module records classroom events and can generate reports for teacher review. This helps the teacher understand classroom activity and attention status.
```

## Quick Troubleshooting

### Problem: Raspberry Pi hostname not found

Error:

```text
Could not resolve hostname smart-classroom-pi.local
```

Possible causes:

- Raspberry Pi is turned off.
- Raspberry Pi is not connected to the same network.
- Raspberry Pi is still booting.
- Windows cannot resolve `.local` hostname.

Fix:

- Wait 2-3 minutes after powering the Pi.
- Check phone hotspot connected devices.
- Try ping:

```powershell
ping smart-classroom-pi.local
```

- Use Raspberry Pi IP address if known:

```powershell
ssh sopheak@<RASPBERRY_PI_IP>
```

### Problem: Raspberry Pi shows Offline

Check:

- Backend server is still running on laptop.
- Backend was started with `--host 0.0.0.0`.
- Laptop and Raspberry Pi are on the same network.
- Laptop IP in `SMART_CLASSROOM_BACKEND_URL` is correct.
- Windows Firewall is not blocking port 8000.

### Problem: Wrong laptop IP

Run:

```powershell
ipconfig
```

Use the IPv4 Address under:

```text
Wireless LAN adapter Wi-Fi
```

Do not use:

- VirtualBox IP
- ZeroTier IP
- 127.0.0.1

### Problem: Backend stopped

Restart backend:

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Problem: Pi client cannot connect to backend

Test from Raspberry Pi:

```bash
python3 - <<'PY'
import requests
print(requests.get("http://<LAPTOP_IP>:8000/iot/health", timeout=5).text)
PY
```

Replace `<LAPTOP_IP>` with the real laptop IP address.

## Safe Shutdown After Demo

Stop Raspberry Pi client:

```text
Ctrl + C
```

Shutdown Raspberry Pi safely:

```bash
sudo shutdown now
```

Wait 30-60 seconds. When the fan is quiet and only the red power light remains, unplug the USB-C power cable.

Stop backend server on laptop:

```text
Ctrl + C
```

## What to Say at the End

```text
In conclusion, our Smart Classroom system already supports web-based monitoring, Raspberry Pi IoT connection, device online status, software light control, and AI event/report features. The next improvement is to connect real relay hardware and fully integrate Raspberry Pi camera-based AI detection.
```

## Completed Demo Features

- Web Dashboard
- AI Monitoring page
- AI Events / Reports page
- Raspberry Pi device status integration
- Raspberry Pi real client connection
- Heartbeat every 5 seconds
- Raspberry Pi IP address display
- Software Light Control Demo
- Occupancy auto light sync
- Raspberry Pi demo guide
- Auto-start service example

## Future Improvements

- Real relay module for physical light control
- Raspberry Pi camera integration
- Auto-start client service enabled on demo device
- Stronger AI attention detection
- Flutter mobile app integration
- More classroom test data
