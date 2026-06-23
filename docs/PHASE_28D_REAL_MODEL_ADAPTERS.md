# Phase 28D — Real Model Selection and Adapter Skeleton

## Scope

Phase 28D adds dependency-free interfaces for future behavior-recognition
models. It does not install model runtimes, download weights, or activate
sleeping, attention, or emotion predictions. The current YOLO object detector
remains the only active model layer and continues to provide person and phone
object results.

Every optional adapter reports `model_required`, returns no predictions, and
runs in safe mode until a validated implementation is deliberately connected.

## Why a person box is not behavior evidence

A person bounding box identifies an image region. It does not describe head
pitch, shoulder geometry, eye state, face direction, expression, or how those
signals change over time. A student may look down while writing or reading; a
small or occluded face may appear tired due to blur; and one frame cannot
separate a brief movement from sustained behavior.

For those reasons, the decision engine preserves current object-based labels
but never derives sleeping, emotion, or attention labels from a person box.

## Proposed model layers

### 1. YOLO / object detector — active

Responsibilities:

- person boxes;
- phone-object boxes;
- current possible-phone-usage association;
- input regions for later adapters.

This layer remains active and unchanged.

### 2. Pose / head-landmark model — planned

A future pose adapter should produce validated body and head landmarks plus
input-quality measurements. It may support a cautious possible-head-down
candidate, but only when the person occupies enough pixels and the required
landmarks are visible.

Possible future implementations include a lightweight pose model or a YOLO
pose variant. Selection must consider backend latency and classroom distance;
Phase 28D does not select or install a dependency yet.

### 3. Face-emotion model — planned and conditional

Emotion classification requires reliable face detection, adequate face pixel
size, and careful bias/accuracy review. It should be skipped for distant,
blurred, angled, or occluded faces. Labels such as happy, laughing, sad, or
tired must not be presented as facts about a student's internal state.

This layer should only be attempted if camera quality consistently supports
usable faces across the intended seats.

### 4. Head-orientation model — planned

Validated face/head landmarks can support yaw, pitch, and roll estimates. A
future adapter may produce looking-around or possible-inattentive candidates,
but a direction estimate is not itself proof of inattention.

### 5. Temporal smoothing — planned

Optional-model candidates must be confirmed across at least three samples.
Low-confidence, missing, or contradictory inputs reset the candidate state.
Cooldowns then prevent repeated reports for one sustained condition.

## Adapter contract

Adapters live in `app/services/model_adapters` and expose:

- `is_available()` — whether a validated implementation is loaded;
- `analyze(image_bytes, detections)` — predictions or a safe empty result;
- `capability_status()` — availability, planned outputs, and requirements.

The current pose, head-orientation, and face-emotion adapters all return:

- `available: false`;
- `status: model_required`;
- no predictions;
- no generated behavior labels;
- an explanation of the future model requirement.

`behavior_decision_engine.py` combines these adapter results with the existing
object analysis. It deep-copies and preserves object overlay fields, publishes
capability details, and records that optional adapters generated no behavior
labels.

## Recommended implementation order

### Candidate selection for evaluation (not installed)

The first engineering spike should compare candidates rather than committing to
weights in the repository:

| Layer | First candidate to evaluate | Why | Decision gate |
| --- | --- | --- | --- |
| Pose/head landmarks | A small Ultralytics pose model in the same backend model family, with MediaPipe Pose as a benchmark | Reuses familiar detection tooling and provides person keypoints | Accuracy for distant seated students and acceptable backend latency |
| Head orientation | A lightweight face-landmark model plus OpenCV `solvePnP` yaw/pitch/roll estimation | Produces explainable geometry instead of a direct attention claim | Minimum face size, stable landmarks, and classroom-angle validation |
| Face emotion | A small ONNX emotion classifier only after reliable face crops are proven | Keeps inference separable and optional | Bias review, face-quality rejection, and strong false-positive testing |
| Temporal smoothing | In-process per-track counters before adding another framework | Simple, testable three-sample confirmation | Cross-frame tracking stability and cooldown correctness |

These are evaluation candidates, not active selections. No dependency or weight
should be added until the associated decision gate passes.

1. **Pose/head-down prototype**
   - select a lightweight pose/head-landmark model;
   - reject undersized or incomplete person regions;
   - validate possible-head-down thresholds against writing and reading.
2. **Head direction / looking around**
   - add face/head landmarks and yaw/pitch/roll estimation;
   - keep wording probabilistic and test across camera positions.
3. **Face emotion only when image quality supports it**
   - define minimum face quality;
   - review bias and false interpretations;
   - disable the layer when faces are too small or occluded.
4. **Temporal confirmation**
   - require three or more consecutive qualified samples;
   - reset on missing or conflicting evidence;
   - apply event-specific cooldowns.
5. **Evidence saving after sustained behavior**
   - retain only policy-qualified alerts;
   - store model/version, confidence, reason, and input-quality metadata;
   - keep normal samples temporary.

## Capability status

The capability payload now reports:

- object detector active;
- pose model inactive;
- head-orientation model inactive;
- face-emotion model inactive;
- temporal smoothing inactive;
- safe mode enabled;
- detailed adapter status for each optional model layer.

This status is intentionally operational rather than aspirational: an adapter
becomes active only when `is_available()` is backed by a real loaded and
validated implementation.

## Non-goals for Phase 28D

- no heavy dependency installation;
- no model weights;
- no Raspberry Pi service changes;
- no database migration;
- no behavior evidence saving;
- no sleeping or emotion claims;
- no changes to current phone evidence or object overlay decisions.
