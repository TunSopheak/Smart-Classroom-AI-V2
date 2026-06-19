# Phase 18: Real AI Detection from Camera Result

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Test Date

2026-06-19

## Goal

Test real AI detection using an image captured from the Raspberry Pi camera and uploaded to the backend.

## Test Image

Latest uploaded snapshot used for YOLO detection:

```text
app/static/uploads/iot_snapshots/pi_snapshot_20260619_101517_fefb71b4.jpg
```

## Detection Result

The backend YOLO detector successfully analyzed the Raspberry Pi camera snapshot.

Output:

```text
Available: True
Message: Backend AI analysis completed.
Person count: 2
Phone count: 0
Image size: 2592 x 1944
```

Detections:

```text
1. person | confidence: 0.747 | box: [434.54, 88.57, 1811.36, 1937.1]
2. person | confidence: 0.350 | box: [393.91, 61.44, 2503.46, 1944.0]
```

## Interpretation

The result confirms that the system can perform real AI detection on a Raspberry Pi camera image.

Important result:

```text
Person detection from Raspberry Pi camera snapshot: PASSED
```

The second person detection has lower confidence, so future improvement should add a confidence threshold to reduce duplicate or weak detections.

## Phase Status

```text
Phase 18A: Real AI Detection Test from Pi Camera Snapshot - PASSED
```

## Recommended Next Step

Next phase:

```text
Phase 18B: Add AI Detection Result to Dashboard
```

Goal:

Show AI detection results on the AI Monitoring dashboard, including:

- Person count
- Phone count
- Detection status
- Latest analyzed image
- Optional detection details

## Future Improvement

To improve reliability:

- Add confidence threshold for person detection.
- Avoid duplicate detection boxes.
- Update occupancy automatically from AI person count.
- Connect person count to auto light logic.
