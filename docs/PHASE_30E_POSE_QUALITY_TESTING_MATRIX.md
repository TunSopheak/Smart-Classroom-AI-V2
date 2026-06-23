# Phase 30E: Pose Quality Testing Matrix

## Purpose

Phase 30E tests whether pose detection is reliable across many images before any dashboard integration.

This phase stays in sandbox mode:

- no dashboard integration
- no database writes
- no attendance updates
- no report evidence saving
- no Raspberry Pi service changes
- no final behavior alerts

## What was added

```text
tools/pose_quality_matrix.py
tests/test_pose_quality_matrix.py
```

The matrix tool runs the Phase 30D posture-candidate sandbox on multiple images and summarizes the results.

## Why this phase matters

Phase 30C proved that MediaPipe pose landmarks can work on a clear human image.

Phase 30D proved that a cautious posture candidate can be generated from nose and shoulder landmarks.

However, early Raspberry Pi classroom snapshots produced `pose_count: 0`, so the camera angle, distance, lighting, and body visibility still need testing before any live integration.

## Run on latest Raspberry Pi snapshots

```powershell
python tools\pose_quality_matrix.py --dir app\static\uploads\iot_snapshots --model models\pose_landmarker_full.task --limit 10 --pretty
```

## Export CSV report

```powershell
python tools\pose_quality_matrix.py --dir app\static\uploads\iot_snapshots --model models\pose_landmarker_full.task --limit 10 --csv reports\pose_quality_matrix.csv --pretty
```

## Run on selected clear photos

```powershell
python tools\pose_quality_matrix.py --image "D:\test_pose.jpg" --model models\pose_landmarker_full.task --pretty
```

You can pass multiple images:

```powershell
python tools\pose_quality_matrix.py --image "D:\test_pose.jpg" --image "D:\another_pose.jpg" --model models\pose_landmarker_full.task --pretty
```

## Result fields

```text
pose_status
pose_count
quality_label
candidate_label
candidate_confidence
nose_to_shoulder_delta
```

## Quality labels

```text
not_detected       pose_count = 0
unknown_visibility pose_count > 0 but visibility not exposed in matrix summary
good               average_visibility >= 0.50
weak               average_visibility >= 0.30 and < 0.50
poor               average_visibility < 0.30
```

## How to judge readiness

### Ready for future prototype integration

```text
At least 70% of realistic classroom snapshots have pose_count >= 1.
Most detected poses have stable nose + shoulder keypoints.
Camera angle and lighting are repeatable.
```

### Not ready yet

```text
Most Raspberry Pi snapshots have pose_count = 0.
People are too far, back-facing, cropped, or dark.
Landmarks are unstable.
```

## Recommended testing set

Test at least 10 images:

1. clear front upper-body image
2. normal sitting position
3. leaning forward
4. side-front view
5. back view
6. far classroom position
7. low light
8. multiple people
9. partial body
10. real Raspberry Pi snapshot from final camera position

## Safe conclusion wording

Use this wording in report/demo:

```text
Pose-based posture detection was tested in sandbox mode. The model can detect landmarks from clear human images, but Raspberry Pi classroom snapshots require further camera-angle and lighting validation before live alert integration.
```

## Recommended next phase

```text
Phase 30F: Temporal Confirmation Plan
```

Future integration should require repeated candidate agreement across multiple frames before saving evidence or showing alerts.
