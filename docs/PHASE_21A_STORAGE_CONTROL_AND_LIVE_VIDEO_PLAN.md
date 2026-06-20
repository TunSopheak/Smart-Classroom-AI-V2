# Phase 21A: Storage Control and Live Video Plan

Smart Classroom AI Monitoring

## Problem Found

The Raspberry Pi client can upload many snapshots in a short time.

This is useful for near-live testing, but it can create too many image files in:

```text
app/static/uploads/iot_snapshots
```

If not controlled, it can affect:

```text
Storage usage
Project folder management
Backup size
Git/file explorer cleanliness
Long-term reliability
```

## Immediate Fix Added

The backend now limits saved Raspberry Pi snapshots.

Default setting:

```text
SMART_CLASSROOM_SNAPSHOT_MAX_FILES=30
```

Meaning:

```text
Keep only the latest 30 snapshot files.
Older snapshot files are cleaned automatically after a new upload.
```

This keeps the current near-live system usable without letting the snapshot folder grow forever.

## Why This Is Not the Final Camera Architecture

For a real classroom monitoring system, saving every frame or every snapshot is not a good design.

A better production design is:

```text
Live video for viewing
AI frame sampling for analysis
Event snapshots only when something important happens
```

## Recommended Future Architecture

```text
Raspberry Pi Camera
    -> Live video stream for dashboard viewing
    -> Backend samples frames every few seconds for AI
    -> Save image only when important event is detected
```

Important events can include:

```text
Person count changes
Empty classroom detected
Light auto turned ON
Light auto turned OFF
Phone detected
Unknown/abnormal behavior detected
Attendance mismatch detected
```

## Recommended Next Phases

```text
Phase 21A: Storage control - DONE
Phase 21B: Snapshot cleanup test
Phase 22A: MJPEG live video stream preview
Phase 22B: AI frame sampling from live stream
Phase 22C: Event-based snapshot saving only
```

## Current Phase Status

```text
Phase 21A: IMPLEMENTED / READY FOR TESTING
```
