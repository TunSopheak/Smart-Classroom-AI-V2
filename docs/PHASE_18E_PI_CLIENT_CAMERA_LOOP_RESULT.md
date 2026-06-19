# Phase 18E: Raspberry Pi Client Camera Loop Result

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Test Date

2026-06-19

## Goal

Integrate Raspberry Pi camera snapshot upload into the existing Raspberry Pi client loop so one client process can handle:

```text
Heartbeat
Light status monitoring
Camera snapshot capture
Camera snapshot upload
```

## Implementation Summary

The Raspberry Pi client was updated to support optional camera upload mode.

Environment variables:

```text
SMART_CLASSROOM_BACKEND_URL
SMART_CLASSROOM_ENABLE_CAMERA
SMART_CLASSROOM_CAMERA_INTERVAL
SMART_CLASSROOM_CAMERA_PATH
```

Recommended run command:

```bash
export SMART_CLASSROOM_BACKEND_URL="http://10.86.94.199:8000"
export SMART_CLASSROOM_ENABLE_CAMERA="1"
export SMART_CLASSROOM_CAMERA_INTERVAL="20"
python3 raspberry_pi/pi_client.py
```

## Expected Client Flow

```text
Start Raspberry Pi client
    -> Send heartbeat every 5 seconds
    -> Read light state from backend
    -> Capture camera snapshot every configured interval
    -> Upload snapshot to backend
    -> Dashboard can refresh and show latest snapshot
```

## Test Result

The feature was tested successfully.

Confirmed result:

```text
Pi client loop works with camera snapshot upload enabled.
```

## Phase Status

```text
Phase 18E: COMPLETED / PASSED
```

## Production Value

This step is important because the Raspberry Pi no longer needs separate manual commands for heartbeat and camera upload.

The system is now closer to a production-style device client:

```text
One Raspberry Pi client process
    -> device online status
    -> light status sync
    -> camera snapshot upload
```

## Next Recommended Phase

Next step:

```text
Phase 18F: Auto Analyze Latest Snapshot After Upload
```

Goal:

After the Raspberry Pi uploads a new snapshot, the backend or dashboard should automatically analyze the latest snapshot and update occupancy/light status without manually clicking the Analyze button.

Alternative next step:

```text
Phase 19: Safe Hardware Light Prototype
```

Goal:

Move from software light demo to safe low-voltage LED/GPIO hardware output.
