# Phase 28C: Multi-Behavior / Emotion Model Integration Plan

## Purpose

The project goal is to move beyond simple labels such as `person` and toward a classroom monitoring overlay that can show behavior-aware labels, for example:

- Monitoring Person
- Possible Phone Usage
- Possible Head Down
- Looking Around
- Sleepy / Drowsy
- Happy / Smile
- Laughing
- Sad / Tired

This phase prepares the model-adapter architecture. It does not pretend that all behaviors are active today.

## Current active capability

The current active AI capability is still object-first:

- person detection
- phone-like object detection
- possible phone usage when a phone-like object is detected near a person region
- behavior-ready overlay fields for Raspberry Pi and browser/computer camera inputs

## New architecture files

```text
app/services/multibehavior_model_service.py
app/services/behavior_overlay_service.py
```

`multibehavior_model_service.py` defines the future model requirements for each behavior. The model status is explicit so the UI can say what is active and what still needs a model.

## Behavior groups

### Object behavior

Active now:

- Monitoring Person
- Phone Object
- Possible Phone Usage

### Pose / posture behavior

Planned, not active yet:

- Possible Head Down
- Looking Around
- Sleepy / Drowsy

Required future models:

- pose model
- head landmark model
- face/head orientation model
- temporal smoothing

### Face / emotion behavior

Planned, not active yet:

- Happy / Smile
- Laughing
- Sad / Tired

Required future models:

- face-emotion model
- face landmark model
- temporal smoothing

## Safety rule

Do not claim a student is sleeping, sad, happy, or inattentive from a person bounding box alone.

Use careful labels:

- Possible Head Down
- Possible Inattentive
- Model Required
- Prototype Only

## Recommended future phases

### Phase 28D: Model research and selection

Choose lightweight models that can work on a laptop backend and possibly Raspberry Pi constraints.

### Phase 28E: Pose/head adapter prototype

Add a pose or head-landmark adapter that returns safe normalized signals:

```json
{
  "track_id": 1,
  "head_down_score": 0.78,
  "looking_around_score": 0.65,
  "confidence": 0.82
}
```

### Phase 28F: Face/emotion adapter prototype

Add a face-emotion adapter that returns careful labels such as smile or neutral only when confidence is high.

### Phase 28G: Temporal smoothing

Require 3 to 5 consecutive samples before saving evidence to reports.

### Phase 28H: Real classroom camera testing

Validate distance, camera angle, lighting, and false positives before making strong claims.
