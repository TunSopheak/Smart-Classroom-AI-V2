# Phase 17: Camera Snapshot Upload and Dashboard Result

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Test Date

2026-06-19

## Goal

Make the Raspberry Pi capture a real camera image, upload it to the FastAPI backend, and show the latest uploaded snapshot on the AI Monitoring dashboard.

## Completed Work

### Backend

New backend support was added for Raspberry Pi camera snapshots.

Endpoints added:

- POST /iot/camera/snapshot
- GET /iot/camera/latest
- POST /iot/camera/reset

The backend can now receive an uploaded image, save it inside the static upload folder, and return the latest snapshot information.

### Dashboard

A new card was added to the AI Monitoring page.

Dashboard card name:

```text
Raspberry Pi Camera Snapshot
```

The card displays:

- Snapshot Status
- Uploaded At
- Device
- File Size
- Latest snapshot image preview
- Refresh Snapshot button

## Test Result

The test was successful.

Confirmed results:

- Raspberry Pi camera image upload worked.
- Backend saved the uploaded image.
- Browser could open the uploaded image.
- AI Monitoring dashboard displayed the latest snapshot.
- Snapshot status showed Available.
- Device showed Raspberry Pi 5.
- File size showed around 582 KB.

## Status

```text
Phase 17A: Camera Snapshot Upload to Backend - PASSED
Phase 17B: Show Latest Camera Snapshot on Dashboard - PASSED
Phase 17: COMPLETED
```

## Next Phase

Next step:

```text
Phase 18: Real AI Detection from Camera
```

Recommended first AI target:

```text
Person / classroom occupancy detection from Raspberry Pi camera snapshot
```

This is the best next step because it directly supports the auto light logic and is easier to verify than complex attention detection.
