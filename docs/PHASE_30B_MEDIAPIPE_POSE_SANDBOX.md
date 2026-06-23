# Phase 30B: MediaPipe Pose Laptop Sandbox

## Purpose

Phase 30B creates a safe laptop-only sandbox for testing real pose landmarks on saved classroom snapshots.

This phase does **not** connect pose results to the live dashboard, attendance, reports, database, Raspberry Pi service, or evidence saving.

The goal is to answer one question first:

> Can a real pose model see useful posture landmarks from our saved Raspberry Pi classroom snapshots?

## What was added

```text
tools/pose_sandbox.py
```

The sandbox tool accepts one saved image and an optional MediaPipe Pose Landmarker model path, then returns JSON.

## Why sandbox first?

Real behavior detection must be validated before being shown as an alert.

A person box alone cannot detect:

- sleeping
- sadness
- happiness
- laughing
- looking around
- head-down posture

The system should test pose landmarks first, then later create careful candidate labels only when confidence is good.

## Safe behavior rules

Phase 30B follows these rules:

- No fake sleeping labels
- No emotion labels
- No dashboard integration
- No database writes
- No report evidence saving
- No Raspberry Pi service changes
- No new required dependency in `requirements.txt`
- Optional MediaPipe only in the laptop sandbox

## Run without a model file

This is the first safe test. It should return `model_required`, not crash.

```powershell
python tools\pose_sandbox.py --image app\static\uploads\iot_snapshots\YOUR_SNAPSHOT.jpg --pretty
```

Expected result:

```json
{
  "ok": true,
  "phase": "30B",
  "status": "model_required",
  "safe_mode": true,
  "generated_behavior_labels": []
}
```

## Run with a model file later

After downloading a MediaPipe Pose Landmarker `.task` model into a local `models/` folder, run:

```powershell
python tools\pose_sandbox.py --image app\static\uploads\iot_snapshots\YOUR_SNAPSHOT.jpg --model models\pose_landmarker.task --pretty
```

Expected successful result:

```json
{
  "ok": true,
  "phase": "30B",
  "status": "completed",
  "pose_count": 1,
  "pose_summaries": [
    {
      "pose_index": 0,
      "landmark_count": 33,
      "average_visibility": 0.73
    }
  ],
  "generated_behavior_labels": []
}
```

## Important note about dependencies

MediaPipe is optional in this phase. Do not add it to the main project requirements yet.

Install it only in the local laptop sandbox environment when ready:

```powershell
pip install mediapipe
```

If MediaPipe is not installed and a model path is provided, the tool returns `dependency_required` safely.

## What to test

Test multiple snapshot types:

1. Close person
2. Far person
3. Side body
4. Back view
5. Low light
6. One person sitting
7. Person leaning forward
8. Multiple people
9. Partial body
10. Camera from Raspberry Pi real classroom position

Record whether pose landmarks are stable.

## Pass / fail criteria

### Pass

Pose landmarks are detected with useful visibility on classroom snapshots.

### Risky

Landmarks appear only on close-up views, but not from classroom distance.

### Fail

No stable pose landmarks from Raspberry Pi snapshots.

If the phase fails, do not force pose behavior detection into the live system.

## Recommended next phase

If pose landmarks are useful, continue to:

```text
Phase 30C: Head-Down Candidate Prototype
```

Phase 30C should still produce only candidate labels such as:

- possible_head_down_candidate
- insufficient_pose_quality
- model_required

It should not save evidence until temporal confirmation is implemented.
