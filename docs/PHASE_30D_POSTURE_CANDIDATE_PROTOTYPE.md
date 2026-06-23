# Phase 30D: Safe Posture Candidate Prototype

## Purpose

Phase 30D converts Phase 30C pose landmarks into cautious single-image posture candidates.

This phase is still a sandbox and research phase. It does not create classroom alerts.

## What was added

```text
app/services/posture_candidate_service.py
tools/posture_candidate_sandbox.py
tests/test_posture_candidate_service.py
```

## Why this phase is cautious

Phase 30C proved that MediaPipe can detect a real human pose from a clear image, but the Raspberry Pi classroom snapshots still produced `pose_count: 0` in the first tests.

Because of that, Phase 30D must not claim that a student is sleeping or not paying attention.

## Candidate labels

Allowed sandbox labels:

```text
normal_upright_candidate
possible_head_low_candidate
insufficient_pose_quality
model_required
pose_not_detected
```

These are not final behavior labels and are not saved as evidence.

## Simple landmark idea

MediaPipe image landmark `y` grows downward.

Phase 30D compares:

```text
nose_y
shoulder_mid_y = (left_shoulder_y + right_shoulder_y) / 2
nose_to_shoulder_delta = nose_y - shoulder_mid_y
```

Interpretation:

```text
nose clearly above shoulders -> normal_upright_candidate
nose close to / below shoulder midpoint -> possible_head_low_candidate
missing nose or shoulder landmarks -> insufficient_pose_quality
```

This is only a first research heuristic.

## Run the sandbox

Use a clear image first:

```powershell
python tools\posture_candidate_sandbox.py --image "D:\test_pose.jpg" --model models\pose_landmarker_full.task --pretty
```

Expected good result:

```json
{
  "ok": true,
  "phase": "30D",
  "pose_status": "completed",
  "pose_count": 1,
  "candidate_result": {
    "status": "completed",
    "posture_candidates": [
      {
        "label": "normal_upright_candidate",
        "safe_mode": true,
        "generated_behavior_labels": []
      }
    ]
  }
}
```

## Important safety rules

Phase 30D must not:

- connect to the dashboard
- update attendance
- write database rows
- save AI report evidence
- trigger lights or IoT actions
- claim sleeping
- claim emotion
- claim real attention status

## When can this become real?

Only after future phases add:

1. stronger Raspberry Pi camera angle
2. better light
3. multiple-frame temporal confirmation
4. repeated candidate agreement
5. teacher review wording

## Recommended next phase

If Phase 30D works on clear images, continue to:

```text
Phase 30E: Pose Quality Testing Matrix
```

Phase 30E should test multiple real classroom snapshots and record whether pose quality is reliable enough for future integration.
