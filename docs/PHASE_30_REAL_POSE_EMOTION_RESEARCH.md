# Phase 30: Real Pose / Emotion Model Research

## Purpose

Phase 30 researches how to move Smart Classroom AI Monitoring from safe object-based behavior overlay toward real pose, head-orientation, and expression-aware prototypes.

The current system can safely show:

- Monitoring Person
- Phone Object
- Possible Phone Usage
- Behavior overlay schema
- Model Required status for optional pose/head/emotion models

This phase does **not** install heavy dependencies, add model weights, or claim that sleeping/emotion detection is already working.

## Behaviors to research

Target behaviors requested for future work:

- Possible Head Down
- Looking Around
- Sleepy / Drowsy
- Happy / Smile
- Laughing
- Sad / Tired

## Safety rule

A person bounding box alone is not enough to say a student is sleeping, sad, happy, laughing, or inattentive.

Use careful labels:

- Possible Head Down
- Possible Inattentive
- Model Required
- Prototype Only
- Safe Mode ON

Evidence should only be saved after repeated confirmation, not from a single frame.

## Candidate model layers

### 1. Existing YOLO/object detector

Current role:

- person detection
- phone-like object detection
- possible phone usage when a phone-like object is near a person box

Recommended status:

- Keep active
- Keep as the first layer
- Do not use object detection alone for emotion or sleeping labels

### 2. MediaPipe Pose Landmarker

Recommended first real-model prototype.

Why it fits:

- Detects human body landmarks from images and video
- Outputs pose landmarks in image coordinates and 3D world coordinates
- Useful for posture analysis and movement categorization
- Has Python documentation and a Raspberry Pi example path

Possible future use:

- possible head-down posture candidate
- leaning posture candidate
- rough sitting posture analysis
- repeated posture confirmation

Limitations:

- Classroom distance and camera angle may reduce landmark quality
- Side-view or partial body views can reduce confidence
- It should output candidates, not strong claims, until validated

Official reference:

- https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python

### 3. YOLO Pose as an alternative

Alternative if the team wants one YOLO-style model family.

Why it may fit:

- Pose task predicts keypoints and bounding boxes
- It can be useful if the project later wants a YOLO-first pipeline
- It may integrate naturally with the existing YOLO object detection direction

Limitations:

- May be heavier depending on model size
- Needs testing on the laptop first before Raspberry Pi
- Still needs behavior rules and temporal confirmation

Official reference:

- https://docs.ultralytics.com/tasks/pose/

### 4. MediaPipe Face Landmarker

Recommended for face landmark and simple expression research only if face quality is good.

Possible future use:

- face landmarks
- smile/happy candidate
- expression blendshape signals
- face crop quality check before emotion analysis

Limitations:

- A classroom camera may be too far from student faces
- Side faces, low light, and occlusion can make results unreliable
- Sad/tired labels are sensitive and should stay experimental

Official reference:

- https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python

### 5. OpenCV solvePnP for head orientation

Useful for head direction estimation when enough reliable 2D face landmarks are available.

Possible future use:

- yaw / pitch / roll estimation
- looking left/right candidate
- looking down candidate
- possible inattentive candidate

Limitations:

- Needs reliable landmarks
- Needs camera assumptions/calibration or approximate camera matrix
- Should be combined with temporal smoothing

Official reference:

- https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html

### 6. Temporal smoothing layer

Required before alerting or saving evidence.

Rule recommendation:

- 1 frame: observation only
- 2 frames: candidate only
- 3 to 5 consecutive samples: possible behavior
- sustained behavior: save evidence if enabled

This reduces false positives and keeps teacher-demo output trustworthy.

## Recommended implementation order

### Phase 30A: Research document

Current phase. No dependencies and no model weights.

### Phase 30B: MediaPipe Pose laptop sandbox

Test on saved snapshots first.

Deliverable:

- `tools/pose_sandbox.py` or similar
- no integration into production overlay yet
- output JSON only

### Phase 30C: Head-down candidate prototype

Use pose/head landmarks to produce only candidate values:

```json
{
  "track_id": 1,
  "behavior_candidate": "possible_head_down",
  "confidence": 0.72,
  "model": "mediapipe_pose",
  "safe_mode": true
}
```

### Phase 30D: Head orientation prototype

Use face landmarks + OpenCV solvePnP to estimate yaw/pitch/roll.

Output only:

- looking_left_candidate
- looking_right_candidate
- looking_down_candidate
- face_too_small
- model_required / insufficient_quality

### Phase 30E: Smile/laugh prototype

Only attempt if camera quality supports visible faces.

Allowed safer labels:

- Smile Candidate
- Laugh Candidate
- Neutral / Unknown
- Face Too Small

Avoid strong emotional claims.

### Phase 30F: Temporal confirmation

Connect candidate results to the existing behavior decision engine.

Requirements:

- 3 to 5 consecutive samples
- cooldown rules
- evidence saving only after sustained behavior
- clear safe-mode status

## Testing plan

Test order:

1. Laptop only
2. Saved snapshots only
3. Close face and clear posture
4. Far face classroom-like distance
5. Side face
6. Low light
7. Occluded face
8. Multiple people
9. Live stream sampling
10. Evidence saving only after validation

## Recommended first real prototype

Start with MediaPipe Pose for Phase 30B because posture/head-down research is more useful for the classroom demo than trying to infer emotions from distant faces.

## Final recommendation

Use this model strategy:

- Keep YOLO/object detector for person and phone usage.
- Add MediaPipe Pose first for posture/head-down candidates.
- Add MediaPipe Face Landmarker only after checking face size and image quality.
- Use OpenCV solvePnP for head orientation after face landmarks are reliable.
- Keep emotion labels experimental and non-alerting until validated.
- Keep Safe Mode ON by default.
