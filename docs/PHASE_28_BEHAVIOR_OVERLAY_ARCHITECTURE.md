# Phase 28A/28B: Real-Time Behavior Overlay Architecture

## Goal

Move the AI Monitoring overlay from simple object labels such as `person 85%` toward a behavior-aware overlay that can show classroom states such as:

- Monitoring Person
- Possible Phone Usage
- Phone Object
- Future: Possible Head Down
- Future: Possible Inattentive

This phase prepares a shared overlay schema for both Raspberry Pi camera input and browser/computer camera input.

## Current implementation

The project now has a unified behavior overlay service:

```text
app/services/behavior_overlay_service.py
```

It enriches ordinary YOLO detections with fields the frontend can draw consistently:

```json
{
  "track_id": 1,
  "student_label": "Student 1",
  "label": "person",
  "behavior": "possible_phone_usage",
  "behavior_label": "Possible Phone Usage",
  "overlay_label": "Possible Phone Usage 86%",
  "overlay_color": "#ef4444",
  "risk": "high",
  "behavior_reason": "Phone-like object detected near this person region.",
  "box": [100, 80, 360, 460],
  "confidence": 0.86
}
```

## Supported camera sources

The same schema is designed for:

1. Raspberry Pi live stream / sampled snapshots
2. Browser or computer camera analysis

This keeps behavior logic reusable instead of duplicating one logic path for Pi and another path for the laptop camera.

## What works now

- Person boxes can display a behavior-friendly label: `Monitoring Person`.
- Phone objects can display: `Phone Object`.
- If a phone-like object is detected inside or near a person region, the person can be marked as `Possible Phone Usage`.
- Overlay color can change by risk:
  - Green/teal = normal monitoring
  - Orange = warning object
  - Red = high-risk possible behavior
- Reports and evidence saving remain separate from overlay drawing.

## What is not claimed yet

This phase does **not** claim reliable sleeping/head-down detection.

Reliable sleeping/head-down detection needs additional model support such as:

- Pose estimation
- Head landmarks
- Face/head orientation
- Temporal confirmation across multiple samples
- Higher-resolution camera testing for distant students

The project should continue to use careful labels such as:

- Possible Head Down
- Possible Inattentive
- Prototype only

Avoid absolute claims such as:

- Student is sleeping
- Student is cheating
- Student is inattentive

unless a validated model and real tests support that conclusion.

## Next recommended phases

### Phase 28C: Pi and Computer Camera Unified Input Test

Confirm both sources return the same enriched schema.

### Phase 28D: True tracking foundation

Replace frame-local left-to-right IDs with cross-frame tracking IDs.

### Phase 28E: Pose/head model integration

Add a validated pose or head-landmark model for head-down and looking-around behavior.

### Phase 28F: Sustained behavior alerting

Only save behavior evidence after 3 or more consecutive samples to reduce false alerts.
