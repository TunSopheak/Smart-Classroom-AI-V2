# Phase 20: Auto-start Raspberry Pi Client Service Plan

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Goal

Prepare the Raspberry Pi client to run automatically after Raspberry Pi boot.

This phase is useful because the demo should not require manually typing this command every time:

```bash
python3 raspberry_pi/pi_client.py
```

Instead, the Raspberry Pi can start the client automatically using a system service.

## Current Service Mode

The service file is prepared here:

```text
raspberry_pi/smart-classroom-pi-client.service.example
```

The installer script is prepared here:

```text
raspberry_pi/install_pi_client_service.sh
```

## Service Environment

Current expected environment values:

```text
SMART_CLASSROOM_BACKEND_URL=http://10.86.94.199:8000
SMART_CLASSROOM_ENABLE_CAMERA=1
SMART_CLASSROOM_AUTO_ANALYZE=1
SMART_CLASSROOM_CAMERA_INTERVAL=20
SMART_CLASSROOM_SESSION_ID=10
```

Important:

If the laptop IP address or active session ID changes, update the service file before installing/restarting the service.

## Install Steps on Raspberry Pi

```bash
cd ~/Smart-Classroom-AI-V2
git pull
chmod +x raspberry_pi/install_pi_client_service.sh
./raspberry_pi/install_pi_client_service.sh
```

## Start Service

```bash
sudo systemctl start smart-classroom-pi-client.service
```

## Check Service Status

```bash
sudo systemctl status smart-classroom-pi-client.service
```

Expected status:

```text
active (running)
```

## View Live Logs

```bash
journalctl -u smart-classroom-pi-client.service -f
```

Expected log examples:

```text
Heartbeat sent | Status: Online
Camera snapshot uploaded | URL: /static/uploads/iot_snapshots/...
Auto AI analysis | Person count: ... | Occupancy sync: True | Light: ON/OFF
```

## Stop Service

```bash
sudo systemctl stop smart-classroom-pi-client.service
```

## Disable Auto-start

```bash
sudo systemctl disable smart-classroom-pi-client.service
```

## Phase Status

```text
Phase 20: READY FOR TESTING
```

## Safety Notes

- Start the laptop backend first.
- Make sure the laptop IP is correct.
- Make sure the active session ID is correct.
- Do not unplug Raspberry Pi directly while the service is running.
- Stop the service or safely shut down Raspberry Pi first.
