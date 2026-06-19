# Production Roadmap Before Flutter

Smart Classroom AI Monitoring - Production Direction

## Purpose

This document defines the production roadmap before continuing to the Flutter mobile application.

The goal is to make the core Smart Classroom system more realistic, stable, and hardware-ready before building the mobile app.

## Current Status

The current final demo version is already completed and tested.

Completed core demo features:

- Web Dashboard
- AI Monitoring page
- AI Events / Reports
- Raspberry Pi real device connection
- Raspberry Pi Online/Offline status
- Raspberry Pi IP address display
- Heartbeat system
- Software light control demo
- Occupancy auto light sync
- Final rehearsal test passed
- Demo checklist and presentation documents

## Why Production First Before Flutter

Before building Flutter, the backend, Raspberry Pi, AI, and IoT logic should be more stable.

If Flutter is built too early, the mobile app may only become another interface for unfinished features.

The recommended direction is:

```text
Core System Stability
        ↓
Raspberry Pi Camera + AI
        ↓
Real Hardware Prototype
        ↓
Auto-start + Reliability
        ↓
Security + API Readiness
        ↓
Flutter Mobile App
```

## Production Version Target

A production-ready Smart Classroom version should support:

1. Raspberry Pi camera capture.
2. Camera snapshot upload to backend.
3. AI detection from real camera data.
4. Real hardware light prototype using safe low-voltage output first.
5. Raspberry Pi client auto-start on boot.
6. Stable backend API for web and mobile.
7. Teacher/admin login and basic security.
8. Reliable reports and monitoring history.
9. Clear deployment and recovery guide.

## Phase 15: Production Roadmap and Requirements

Goal:

Define what production version means for this project.

Tasks:

- Define production requirements.
- List hardware requirements.
- List software requirements.
- List security requirements.
- List safety limitations.
- Decide what must be completed before Flutter.

Deliverable:

```text
docs/PRODUCTION_ROADMAP_BEFORE_FLUTTER.md
```

Status:

```text
Started
```

## Phase 16: Raspberry Pi Camera Test

Goal:

Confirm that the Raspberry Pi camera works correctly before adding AI logic.

Tasks:

- Check camera connection.
- Test camera detection on Raspberry Pi OS.
- Capture a test image.
- Save test image locally.
- Document camera commands.

Expected result:

```text
Raspberry Pi can capture an image successfully.
```

Notes:

- Do not start AI detection until the camera capture works reliably.
- If camera is not detected, check ribbon cable direction and Raspberry Pi camera connector.

## Phase 17: Camera Snapshot Upload to Backend

Goal:

Allow Raspberry Pi to send a real camera snapshot to the FastAPI backend.

Tasks:

- Add backend API endpoint for snapshot upload.
- Add snapshot storage folder.
- Update Raspberry Pi client to capture image.
- Upload image to backend.
- Show latest snapshot on AI Monitoring dashboard.

Expected result:

```text
Pi camera image appears on the web dashboard.
```

## Phase 18: Real AI Detection from Camera

Goal:

Use real camera data for AI monitoring.

Tasks:

- Start with a simple detection target.
- Use camera image as AI input.
- Save AI event result.
- Show event result on dashboard.
- Add snapshot link to AI event.

Recommended first detection goal:

```text
Person/classroom occupancy detection
```

Reason:

Occupancy detection is easier and directly supports auto light logic.

After occupancy works, improve toward:

- Student attention status
- Phone usage detection
- Face/attendance integration

## Phase 19: Safe Hardware Light Prototype

Goal:

Move from software light demo to real safe hardware output.

Important safety rule:

Do not connect directly to real classroom AC 220V lights without proper relay hardware and electrical safety support.

Recommended first prototype:

```text
Raspberry Pi GPIO -> LED / low-voltage module
```

Then later:

```text
Raspberry Pi GPIO -> relay module -> real light circuit
```

Tasks:

- Choose GPIO pin mapping.
- Test LED ON/OFF from Python.
- Connect LED state to backend light state.
- Add hardware mode in Pi client.
- Document wiring diagram.

Expected result:

```text
Dashboard button can turn a low-voltage LED ON/OFF through Raspberry Pi GPIO.
```

## Phase 20: Raspberry Pi Auto-start Service

Goal:

Make the Raspberry Pi client start automatically when the Pi boots.

Tasks:

- Update service file with correct project path.
- Set backend URL.
- Install systemd service.
- Enable service.
- Reboot test.
- Check dashboard Online status after reboot.

Expected result:

```text
After power on, Raspberry Pi automatically connects to backend without manual SSH command.
```

Note:

Only enable auto-start after the network/backend IP strategy is stable.

## Phase 21: Stable Network Strategy

Goal:

Reduce network problems during demo or production use.

Options:

1. Use the same phone hotspot.
2. Use router Wi-Fi.
3. Set static IP for laptop and Raspberry Pi.
4. Run backend on Raspberry Pi itself.
5. Deploy backend to local server or cloud server.

Recommended short-term approach:

```text
Use the same hotspot and always check laptop IP with ipconfig.
```

Recommended production approach:

```text
Use a stable router or local server with fixed IP.
```

## Phase 22: Security and Teacher Login

Goal:

Prepare the system for real teacher/admin usage.

Tasks:

- Add login page.
- Add admin/teacher account.
- Protect dashboard routes.
- Protect important API endpoints.
- Add logout.
- Add basic password security.

Expected result:

```text
Only authorized users can access dashboard and control features.
```

## Phase 23: Report Improvement

Goal:

Make AI reports more useful for teacher review.

Tasks:

- Improve report list page.
- Add filters by date/session/class.
- Add AI event summary.
- Add export option if needed.
- Add clear report layout for printing or PDF export later.

Expected result:

```text
Teacher can review classroom activity history more easily.
```

## Phase 24: API Readiness for Flutter

Goal:

Prepare backend APIs before building Flutter app.

Tasks:

- Confirm dashboard features have API endpoints.
- Add JSON endpoints for mobile app.
- Document API response format.
- Add authentication token strategy.
- Test API with simple requests.

Expected result:

```text
Flutter can use stable backend APIs without changing the backend structure too much.
```

## Phase 25: Flutter Mobile App

Goal:

Build mobile app after the core system is stable.

Recommended Flutter features:

- Login screen
- Dashboard summary
- Raspberry Pi device status
- Light control page
- AI events list
- Reports page
- Notifications later if needed

Important note:

Flutter should be built after camera, IoT, and backend APIs are stable enough.

## Priority Order

Recommended order from now:

```text
1. Phase 16 - Raspberry Pi Camera Test
2. Phase 17 - Camera Snapshot Upload to Backend
3. Phase 18 - Real AI Detection from Camera
4. Phase 19 - Safe Hardware Light Prototype
5. Phase 20 - Raspberry Pi Auto-start Service
6. Phase 21 - Stable Network Strategy
7. Phase 22 - Security and Teacher Login
8. Phase 23 - Report Improvement
9. Phase 24 - API Readiness for Flutter
10. Phase 25 - Flutter Mobile App
```

## What Not to Do Yet

Do not do these too early:

- Do not connect to real AC classroom light directly.
- Do not enable auto-start before backend IP/network is stable.
- Do not build Flutter before core APIs are stable.
- Do not add too many AI features at the same time.
- Do not change demo-stable code without testing.

## Next Immediate Step

The next immediate production step is:

```text
Phase 16: Raspberry Pi Camera Test
```

Success condition:

```text
Raspberry Pi can capture a real image from the camera module.
```

After that, continue to snapshot upload and real AI detection.

## Final Direction

The correct direction before Flutter is:

```text
Make the hardware + backend + AI core reliable first.
Then build Flutter as a mobile interface on top of the stable system.
```
