# Phase 27C — Behavior AI Expansion Plan

## Purpose and safety boundary

Phase 27C establishes a conservative foundation for possible head-down and
inattentive behavior monitoring. It does not claim that a student is sleeping,
disengaged, or behaving incorrectly. Those conclusions require validated pose,
head-orientation, camera-placement, and temporal evidence that the current
object detector does not provide.

The current production path continues to support person and phone-object
detection, occupancy synchronization, and qualified alert evidence. Behavior
alerts remain disabled by default.

## Why behavior detection is harder than object detection

Object detection answers a relatively bounded question: whether a known object
class appears in an image and where its box is located. Behavior interpretation
depends on relationships that a box alone cannot explain:

- head position relative to shoulders and torso;
- face direction and visibility;
- pose over time rather than in one frame;
- occlusion by desks, other students, or classroom objects;
- camera perspective, distance, image resolution, and lighting;
- legitimate actions such as reading, writing, or looking down briefly.

A person bounding box is therefore not evidence that a student is sleeping or
inattentive. Phase 27C explicitly rejects behavior alerts when pose/head inputs
are missing or confidence is insufficient.

## Far-distance monitoring constraints

Students farther from the camera occupy fewer pixels. Small faces, heads, and
limbs make pose and gaze estimates unstable even when person detection still
works. A future deployment should validate:

1. higher capture resolution while keeping inference latency acceptable;
2. camera height and angle that preserve head/shoulder visibility;
3. sufficient, even classroom lighting;
4. lens field of view appropriate for the room depth;
5. minimum pixel size for a person before behavior analysis is attempted;
6. representative testing across seats, body types, uniforms, and occlusion.

Increasing resolution alone does not guarantee reliable behavior detection.
Camera placement and model validation matter equally.

## Recommended processing pipeline

### 1. Person detection

Use the existing detector to find candidate people. If no person is detected,
skip behavior evaluation. Very small or heavily occluded person boxes should
also be excluded by a future quality gate.

### 2. Pose and head-landmark estimation

Run a validated pose/head model on each eligible person region. Useful inputs
may include shoulders, nose/eyes/ears, neck orientation, face visibility, and a
head-pitch estimate. Looking-away analysis additionally needs validated face or
head orientation; it should not be inferred from a person box.

The Phase 27C service accepts a future `behavior_signals` adapter but the
current YOLO result does not populate it.

### 3. Temporal smoothing over at least three samples

One frame can capture writing, reading, motion blur, or a temporary occlusion.
An alert candidate must be supported by at least three consecutive sampled
results. A missing, low-confidence, or contradictory result resets the relevant
counter. The default configuration is:

- `SMART_CLASSROOM_BEHAVIOR_ALERTS_ENABLED=0`
- `SMART_CLASSROOM_BEHAVIOR_REQUIRED_SAMPLES=3`
- `SMART_CLASSROOM_HEAD_DOWN_EVENT_COOLDOWN_SECONDS=120`

The required sample count has a safety minimum of three. Behavior evidence
must remain disabled until a real landmark model and classroom validation are
available.

### 4. Sustained alert evidence only

After the temporal rule and cooldown both pass, a future integration may emit
an evidence candidate. The report wording must remain probabilistic:

- Possible head-down behavior detected
- Possible inattentive behavior detected
- Possible phone usage detected

The Phase 27C prototype can construct an event candidate in memory for tests,
but it is intentionally not connected to snapshot saving or database logging.

## Explainable event payload

A future behavior event should record:

- the probable event type and cautious title;
- confidence and the supporting landmark-based reason;
- required and observed consecutive sample counts;
- source snapshot filename and capture time;
- model/version and input-quality details;
- cooldown state;
- the evidence image only after the policy passes.

This makes a demo alert reviewable without presenting AI output as proof of a
student's intent or condition.

## Storage policy

Normal Raspberry Pi snapshots and AI samples remain temporary monitoring input.
Person detections do not create permanent behavior evidence. Only qualified,
sustained alert evidence may be retained in AI Reports. Existing phone usage and
light auto-off evidence behavior remains separate and unchanged.

When behavior alerts are eventually enabled, their images and metadata should
use the existing event-evidence retention, file-limit, and cooldown controls.

## Validation checklist before enabling behavior alerts

- Select and version a pose/head model suitable for the backend hardware.
- Define minimum person/face pixel sizes and reject insufficient input.
- Validate head-down and looking-away thresholds with classroom footage.
- Measure false positives for reading, writing, note-taking, and occlusion.
- Confirm three-or-more-sample smoothing under the configured sampling rate.
- Confirm cooldown prevents repeated reports for one sustained condition.
- Review wording, privacy, retention, and teacher-facing explanations.
- Test every seating distance and document unsupported camera zones.
- Enable alerts only after the evidence quality is acceptable.

## Future behavior timeline

A later phase can build a timeline from validated event candidates rather than
from every sample. It should show alert windows, confidence trends, review
status, and evidence links while keeping normal samples temporary. Aggregate
reporting should communicate uncertainty and must not rank or label students
without a separately reviewed policy and validated identity model.
