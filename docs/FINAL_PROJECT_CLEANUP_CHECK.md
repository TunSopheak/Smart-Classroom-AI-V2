# Final GitHub / Project Cleanup Check

Smart Classroom AI Monitoring - Final Cleanup Review

## Cleanup Goal

The purpose of this cleanup check is to make sure the project is ready for final demo and teacher review.

This document checks the repository structure, important demo files, Raspberry Pi setup guide, final presentation documents, and possible risk points before the final presentation.

## Repository Status

```text
Repository: TunSopheak/Smart-Classroom-AI-V2
Default branch: main
Project type: FastAPI + Web Dashboard + AI Monitoring + Raspberry Pi IoT Client
```

## Important Files Checked

### Application Entry Point

```text
main.py
```

Checked result:

- FastAPI app is created.
- Static files are mounted.
- Main routers are included.
- AI Monitoring router is included.
- AI Reports router is included.
- IoT router is included.

### Python Requirements

```text
requirements.txt
```

Checked result:

- Backend dependencies are listed.
- FastAPI and Uvicorn are included.
- SQLAlchemy and Jinja2 are included.
- OpenCV and Ultralytics are included for AI-related work.

Note:

- Raspberry Pi client uses `requests`.
- For Raspberry Pi, the guide uses `sudo apt install -y python3-requests`.

### Raspberry Pi Client

```text
raspberry_pi/pi_client.py
```

Checked result:

- Reads backend URL from `SMART_CLASSROOM_BACKEND_URL`.
- Default backend URL is `http://127.0.0.1:8000`.
- Sends heartbeat to `/iot/device/heartbeat`.
- Reads light state from `/iot/light/status`.
- Prints Light 1 and Light 2 updates when changed.
- Runs continuously until stopped with `Ctrl + C`.
- Current mode is safe software-only demo.

### Raspberry Pi Demo Guide

```text
raspberry_pi/README.md
```

Checked result:

- Network setup is included.
- Laptop backend command is included.
- Laptop IP checking command is included.
- SSH command is included.
- Raspberry Pi client command is included.
- Safe shutdown command is included.
- Troubleshooting is included.
- First-time Raspberry Pi setup steps were added during cleanup.

### Auto-Start Service Example

```text
raspberry_pi/smart-classroom-pi-client.service.example
```

Checked result:

- Service file example exists.
- It can be used later for auto-starting the Pi client.
- It should not be enabled yet unless the network/IP is stable.

### Final Demo Checklist

```text
docs/FINAL_DEMO_CHECKLIST.md
```

Checked result:

- Equipment checklist is included.
- Start demo steps are included.
- Backend command is included.
- Raspberry Pi command is included.
- Live demo script is included.
- Troubleshooting is included.
- Safe shutdown is included.

### Final Presentation Script

```text
docs/FINAL_PRESENTATION_SCRIPT.md
```

Checked result:

- Introduction is included.
- Problem statement is included.
- Objectives are included.
- System architecture is included.
- Technology used is included.
- Live demo speech is included.
- Limitations and future improvements are included.
- Short version and Q&A preparation are included.

### Final Report Summary

```text
docs/FINAL_REPORT_SUMMARY.md
```

Checked result:

- Project overview is included.
- Completed features are included.
- API endpoints are included.
- Raspberry Pi client summary is included.
- Limitations and future improvements are included.
- Short teacher summary is included.

## Search / Cleanup Results

Checked for common cleanup issues:

```text
TODO / FIXME: No result found
Merge conflict marker <<<<<<< HEAD: No result found
```

Result:

```text
No obvious TODO/FIXME or merge conflict marker was found during cleanup search.
```

## Demo Readiness Checklist

Before final demo, confirm these points:

- [ ] Laptop has latest code from GitHub.
- [ ] Raspberry Pi has latest code from GitHub.
- [ ] Phone hotspot or Wi-Fi is ready.
- [ ] Laptop and Raspberry Pi are connected to the same network.
- [ ] Laptop IP address is checked with `ipconfig`.
- [ ] Backend starts with `--host 0.0.0.0`.
- [ ] Browser can open `/dashboard`.
- [ ] Browser can open `/ai-monitoring`.
- [ ] SSH into Raspberry Pi works.
- [ ] Raspberry Pi client runs without connection error.
- [ ] Dashboard shows Raspberry Pi Online.
- [ ] Dashboard shows Raspberry Pi IP address.
- [ ] Light 1 ON/OFF works.
- [ ] Light 2 ON/OFF works.
- [ ] Raspberry Pi terminal prints light state updates.
- [ ] Safe shutdown command is remembered.

## Final Demo Commands

### Laptop Backend

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Laptop IP

```powershell
ipconfig
```

Use the IPv4 address under:

```text
Wireless LAN adapter Wi-Fi
```

### SSH into Raspberry Pi

```powershell
ssh sopheak@smart-classroom-pi.local
```

### Raspberry Pi Client

```bash
cd Smart-Classroom-AI-V2
git pull
export SMART_CLASSROOM_BACKEND_URL="http://<LAPTOP_IP>:8000"
python3 raspberry_pi/pi_client.py
```

### Dashboard Links

```text
http://127.0.0.1:8000/dashboard
http://127.0.0.1:8000/ai-monitoring
```

### Safe Shutdown

```bash
sudo shutdown now
```

## Current Known Limitations

- Light control is software-only at this stage.
- Real relay module is not connected yet.
- Raspberry Pi camera AI detection is not fully integrated yet.
- Flutter mobile app is not fully integrated into final demo yet.
- Laptop IP may change when hotspot/Wi-Fi changes.

## Recommendation Before Demo

Recommended final preparation:

1. Do one full rehearsal using the same hotspot.
2. Take screenshots of successful Raspberry Pi Online status.
3. Take screenshots of Light 1 and Light 2 state changes.
4. Keep `FINAL_DEMO_CHECKLIST.md` open during the demo.
5. Keep `FINAL_PRESENTATION_SCRIPT.md` ready as speaking support.
6. Bring charger/power bank for phone hotspot and laptop.
7. Do not enable auto-start service unless the backend IP/network is stable.

## Final Status

```text
Project cleanup check completed.
Repository documents are ready for final demo preparation.
The project is ready for final rehearsal.
```
