# Final Rehearsal Test Result

Smart Classroom AI Monitoring - Phase 13

## Test Date

2026-06-19

## Test Goal

Run the complete final demo flow before the real presentation.

Main flow tested:

```text
Laptop Backend + Web Dashboard
        |
        | Same Wi-Fi / Phone Hotspot
        |
Raspberry Pi IoT Client
```

## Network Information During Test

```text
Laptop IP: 10.86.94.199
Raspberry Pi IP: 10.86.94.200
Backend URL used by Raspberry Pi: http://10.86.94.199:8000
```

## Steps Completed

- Phone hotspot was used as the shared network.
- Laptop connected to the hotspot.
- Raspberry Pi was reimaged and configured with Wi-Fi and SSH.
- Raspberry Pi successfully connected to the hotspot.
- Laptop found Raspberry Pi through ARP table.
- SSH login to Raspberry Pi worked using IP address.
- Latest project code was cloned from GitHub to Raspberry Pi.
- Required Raspberry Pi packages were installed.
- FastAPI backend was started on laptop with `--host 0.0.0.0`.
- Raspberry Pi client was started with `SMART_CLASSROOM_BACKEND_URL`.
- Raspberry Pi sent heartbeat data to backend.
- Dashboard showed Raspberry Pi Online.
- Dashboard showed Raspberry Pi IP address.
- Light 1 ON was tested.
- Light 2 ON was tested.
- Light 1 OFF was tested.
- Light 2 OFF was tested.
- Raspberry Pi terminal printed updated light state.

## Successful Commands

### Laptop Backend

```powershell
cd "D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Raspberry Pi SSH

```powershell
ssh sopheak@10.86.94.200
```

### Raspberry Pi Setup After Reimage

```bash
sudo apt update
sudo apt install -y git python3-requests
git clone https://github.com/TunSopheak/Smart-Classroom-AI-V2.git
cd Smart-Classroom-AI-V2
```

### Raspberry Pi Client

```bash
export SMART_CLASSROOM_BACKEND_URL="http://10.86.94.199:8000"
python3 raspberry_pi/pi_client.py
```

## Expected Output Confirmed

The Raspberry Pi client printed heartbeat status similar to:

```text
Heartbeat sent | Status: Online
```

The light control test printed status similar to:

```text
Light state | Light 1: ON | Light 2: ON | Mode: Software Demo
Light state | Light 1: OFF | Light 2: OFF | Mode: Software Demo
```

## Dashboard Result

The AI Monitoring dashboard successfully showed:

- Raspberry Pi Device Status: Online
- Device Name: Raspberry Pi 5
- IP Address: 10.86.94.200
- Seconds since last seen: few seconds
- Light 1 status updated
- Light 2 status updated
- Updated time changed after button clicks

## Issue Found During Rehearsal

The hostname command did not resolve at first:

```powershell
ssh sopheak@smart-classroom-pi.local
```

The fix was to use the Raspberry Pi IP address directly:

```powershell
ssh sopheak@10.86.94.200
```

If needed, the Raspberry Pi IP can be found from the phone hotspot connected devices list or from laptop ARP table:

```powershell
arp -a
```

## Final Test Status

```text
Phase 13 Final Rehearsal Test: PASSED
Raspberry Pi Online Test: PASSED
Light ON Test: PASSED
Light OFF Test: PASSED
Backend-to-Pi Communication: PASSED
Dashboard Display: PASSED
```

## Recommendation for Real Demo

Before the real demo:

1. Use the same hotspot name and password.
2. Check laptop IP with `ipconfig`.
3. Use Raspberry Pi IP if `.local` hostname does not work.
4. Keep screenshots of the successful Online status and light state update.
5. Keep `FINAL_DEMO_CHECKLIST.md` open during demo.
6. Stop the Pi client and safely shut down Raspberry Pi after demo.

## Safe Shutdown Reminder

Stop Pi client:

```text
Ctrl + C
```

Shutdown Raspberry Pi:

```bash
sudo shutdown now
```

Stop laptop backend:

```text
Ctrl + C
```
