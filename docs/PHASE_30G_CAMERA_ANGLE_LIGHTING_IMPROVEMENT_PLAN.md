# Phase 30G: Camera Angle and Lighting Improvement Plan

## Purpose

Phase 30G focuses on improving Raspberry Pi classroom snapshots so pose detection can work reliably later.

This phase is not a live AI integration phase. It is a measurement and improvement phase.

## Why Phase 30G is needed

Phase 30E tested 10 Raspberry Pi snapshots and produced:

```text
total_images: 10
pose_detected_images: 0
not_detected_images: 10
```

The MediaPipe model worked on a clear human photo, but not on the current Raspberry Pi classroom snapshots.

This means the model is not the main problem. The main issue is likely camera angle, distance, lighting, or body visibility.

## What was added

```text
app/services/camera_quality_service.py
tools/camera_quality_check.py
tests/test_camera_quality_service.py
```

The new tool checks simple image-quality signals:

```text
resolution
brightness
contrast
sharpness
```

It does not run dashboard alerts, write the database, or save AI evidence.

## Run camera quality check on Pi snapshots

```powershell
python tools\camera_quality_check.py --dir app\static\uploads\iot_snapshots --limit 10 --pretty
```

## Export CSV

```powershell
python tools\camera_quality_check.py --dir app\static\uploads\iot_snapshots --limit 10 --csv reports\camera_quality_matrix.csv --pretty
```

## Recommended camera placement

For pose detection, the Raspberry Pi camera should see:

```text
head
shoulders
upper body
some arm position
clear front or side-front view
```

Avoid:

```text
back view only
face/body too far away
student cut off by frame edge
camera too low or too high
strong backlight from window
dark blue/purple lighting
motion blur
```

## Practical classroom setup

Recommended first setup:

```text
Camera height: around chest to eye level when seated
Camera angle: 20-45 degrees from the front side
Distance: close enough to see head and shoulders clearly
Light: front/side light, not only backlight
Resolution: at least 640x480
```

## Improvement checklist

1. Move camera closer to the student/demo subject.
2. Raise or lower camera until head and shoulders are visible.
3. Avoid full back view.
4. Turn on room light or add a desk lamp from the front/side.
5. Avoid pointing the camera directly at bright windows.
6. Keep the camera stable.
7. Clean the camera lens.
8. Retake 10 snapshots.
9. Run Phase 30G camera-quality check.
10. Run Phase 30E pose-quality matrix again.

## Quality thresholds

The Phase 30G tool uses these simple thresholds:

```text
minimum resolution: 640x480
brightness_mean: 60 to 190
contrast_std: at least 25
sharpness_laplacian_var: at least 50
```

These thresholds are not final research truth. They are practical demo-quality checks.

## Acceptance criteria before live pose integration

Do not connect posture candidates to dashboard alerts until:

```text
at least 7 out of 10 realistic Pi snapshots have pose_count >= 1
head + shoulder landmarks are stable
lighting is repeatable
camera angle is repeatable
false alerts are still disabled until temporal confirmation is validated
```

## Safe report wording

```text
After testing, the pose model worked on clear human images, but current Raspberry Pi classroom snapshots did not provide enough body visibility for reliable pose detection. A camera angle and lighting improvement plan was created before attempting any live alert integration.
```

## Recommended next phase

After changing camera setup, repeat:

```text
Phase 30G: camera quality check
Phase 30E: pose quality matrix
```

Only then continue toward future integration.
