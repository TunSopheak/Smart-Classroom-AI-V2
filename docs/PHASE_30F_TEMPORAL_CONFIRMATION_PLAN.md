# Phase 30F: Temporal Confirmation Plan

## Purpose

Phase 30F adds a safe temporal-confirmation plan for posture candidates.

The goal is to prevent false alerts from a single image. A posture candidate should repeat across multiple frames before it is even considered for teacher review.

This phase is still sandbox-only.

## What was added

```text
app/services/temporal_confirmation_service.py
tools/temporal_confirmation_sandbox.py
tests/test_temporal_confirmation_service.py
```

## Why temporal confirmation is needed

Phase 30C proved that pose landmarks work on clear human images.

Phase 30D proved that nose/shoulder landmarks can create a cautious posture candidate.

Phase 30E showed that current Raspberry Pi classroom snapshots are not reliable enough yet: 10 out of 10 Pi snapshots returned `pose_count = 0`.

Because of this, live posture alerts must not be enabled yet.

## Safe rule

A candidate can become `confirmed_for_review` only when:

```text
same target candidate appears at least 3 times
inside a recent 5-frame window
with confidence >= 0.50
```

Default target:

```text
possible_head_low_candidate
```

## Important wording

Even when temporal confirmation passes, this is still not a final alert.

The system returns:

```text
confirmed_for_review
```

It does not return:

```text
sleeping
not paying attention
cheating
```

## Safety outputs

The service always keeps these disabled in Phase 30F:

```json
{
  "should_show_dashboard_alert": false,
  "should_save_evidence": false,
  "should_update_database": false,
  "generated_behavior_labels": []
}
```

## Run demo

```powershell
python tools\temporal_confirmation_sandbox.py --demo --pretty
```

Expected important fields:

```json
{
  "phase": "30F",
  "status": "confirmed_for_review",
  "confirmed_for_review": true,
  "should_show_dashboard_alert": false,
  "should_save_evidence": false
}
```

## Run manual sequence

```powershell
python tools\temporal_confirmation_sandbox.py --label possible_head_low_candidate --label normal_upright_candidate --label possible_head_low_candidate --label possible_head_low_candidate --pretty
```

## Not ready cases

### No frames

```text
status: no_frames
```

### Not enough frames

```text
status: needs_more_frames
```

### Unstable result

```text
status: unstable_candidate
```

### Bad pose quality

```text
status: insufficient_pose_quality
```

### No pose detected

```text
status: pose_not_detected
```

## Integration decision

Do not connect Phase 30F to dashboard alerts yet.

The next practical requirement is to improve camera placement and lighting, then repeat Phase 30E on new Raspberry Pi snapshots.

## Recommended next phase

```text
Phase 30G: Camera Angle and Lighting Improvement Plan
```

Goal: improve Raspberry Pi snapshot quality until pose detection works reliably from the classroom camera position.
