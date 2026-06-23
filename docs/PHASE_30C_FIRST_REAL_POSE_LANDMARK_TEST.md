# Phase 30C: Download / Install MediaPipe Pose Model and First Real Landmark Test

## Purpose

Phase 30C runs the first real MediaPipe Pose Landmarker test on saved Raspberry Pi snapshots.

This phase is still sandbox-only:

- no dashboard integration
- no database writes
- no report evidence saving
- no Raspberry Pi service changes
- no fake sleeping or emotion labels

The goal is only to verify whether the model can detect useful pose landmarks from the current camera angle and image quality.

## Official model information

MediaPipe Pose Landmarker detects landmarks of human bodies in images and videos. It can be used to identify body locations, analyze posture, and categorize movement. The task outputs body pose landmarks in image coordinates and 3D world coordinates.

The official model bundle includes a pose detection model and a pose landmarker model. The landmarker estimates 33 three-dimensional body landmarks.

Recommended first model:

```text
pose_landmarker_lite.task
```

Why lite first:

- smallest model option
- better starting point for laptop/Raspberry Pi feasibility
- enough for first landmark visibility testing

## What was added

```text
tools/download_pose_model.py
tools/pose_sandbox.py
```

`download_pose_model.py` downloads the model into `models/`.

`pose_sandbox.py` runs the model on a saved image and returns JSON.

The `models/` folder and `*.task` files are ignored by Git so model weights are not committed.

## Step 1: Make sure you are on the phase branch

```powershell
git fetch origin
git switch phase-30c-mediapipe-pose-first-test
git pull
```

## Step 2: Install MediaPipe locally

Install MediaPipe only in the laptop virtual environment:

```powershell
pip install mediapipe
```

Do not add MediaPipe to `requirements.txt` yet. This is still a sandbox dependency.

## Step 3: Download the lite model

```powershell
python tools\download_pose_model.py --variant lite --pretty
```

Expected result:

```json
{
  "ok": true,
  "status": "downloaded",
  "variant": "lite",
  "path": "models\\pose_landmarker_lite.task"
}
```

If it already exists, `status` may be `already_exists`, which is also fine.

## Step 4: Choose latest Raspberry Pi snapshot

```powershell
$latest = Get-ChildItem app\static\uploads\iot_snapshots -Filter *.jpg |
Sort-Object LastWriteTime -Descending |
Select-Object -First 1

$latest.FullName
```

## Step 5: Run first real pose landmark test

```powershell
python tools\pose_sandbox.py --image "$($latest.FullName)" --model models\pose_landmarker_lite.task --pretty
```

Good result example:

```json
{
  "ok": true,
  "phase": "30C",
  "status": "completed",
  "pose_count": 1,
  "pose_summaries": [
    {
      "pose_index": 0,
      "landmark_count": 33,
      "average_visibility": 0.71
    }
  ],
  "generated_behavior_labels": []
}
```

No behavior labels should be generated in Phase 30C.

## How to judge the result

### Good

```text
pose_count >= 1
landmark_count = 33
average_visibility >= 0.50
```

This means we can continue toward a head-down candidate prototype.

### Weak

```text
pose_count >= 1
average_visibility < 0.50
```

This means pose is detected but may be unstable. Test more snapshots.

### Not good

```text
pose_count = 0
```

This means the current image angle, distance, or lighting may not support pose-based behavior detection.

## Testing matrix

Test at least these snapshots:

1. person close to camera
2. person far from camera
3. back view
4. side view
5. leaning forward
6. normal sitting
7. low light
8. partial body
9. multiple people
10. phone usage position

Record each result with:

```text
filename
pose_count
average_visibility
camera condition
notes
```

## Safety note

Even if pose landmarks are found, this phase must not claim:

- sleeping
- sad
- happy
- laughing
- cheating
- not paying attention

Phase 30C only proves model feasibility.

## Recommended next phase

If landmarks are stable enough, continue to:

```text
Phase 30D: Head-Down Candidate Prototype
```

Phase 30D should produce careful labels only:

- possible_head_down_candidate
- insufficient_pose_quality
- model_required

Real alerts should still wait for temporal confirmation.
