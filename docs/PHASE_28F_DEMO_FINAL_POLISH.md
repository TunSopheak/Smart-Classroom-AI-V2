# Phase 28F — Demo Final Polish and Presentation Readiness

## Purpose

Phase 28F prepares Smart Classroom AI Monitoring Version 2 for a clear,
low-risk teacher demonstration. It adds no model, dependency, schema, or
Raspberry Pi service changes. The work consolidates existing operational
signals so the presenter can quickly explain what is ready, what is waiting,
and what remains planned.

## AI Monitoring presentation status

The AI Monitoring page now presents a compact Demo Checklist containing:

- backend running;
- Raspberry Pi stream state;
- snapshot upload freshness;
- AI sampling completion;
- active session selection;
- occupancy/session sync readiness;
- Behavior AI safe mode;
- report availability.

The checklist initially renders from backend state and then updates from the
existing browser polling and stream events. Detailed camera, device, AI sample,
behavior, occupancy, and report sections remain unchanged below it.

## What is real now

- A real Raspberry Pi MJPEG live stream can be viewed in the browser.
- The Pi uploads temporary snapshots to the FastAPI backend.
- The backend samples snapshots and runs the current object detector.
- Person and phone-object results can be drawn by the behavior overlay schema.
- Qualified phone alert evidence can be retained in AI Reports.
- Device status can become Online from recent snapshot uploads without the old
  heartbeat client.
- Session/occupancy sync reports Active, Skipped, or Not Active separately from
  AI analysis success.
- Optional-model adapters expose honest capability status and remain in safe
  mode.

## What remains planned

- a validated pose/head-down model;
- a validated head-orientation model;
- face-emotion inference only if camera face quality supports it;
- temporal smoothing and cross-frame tracking;
- behavior evidence after sustained validated signals;
- physical relay integration for classroom lights.

The application must not claim that sleeping, emotion, or attention detection
is active until those models and policies are validated.

## Suggested teacher explanation

> This page combines the real Raspberry Pi stream with sampled backend AI. The
> object detector currently recognizes people and phone-like objects. The red,
> amber, and teal overlays are explainable object-based monitoring labels. The
> Behavior AI architecture is prepared for pose, head direction, and emotion
> models, but those optional models are deliberately inactive so the demo does
> not present unvalidated behavior claims. Normal samples remain temporary;
> only qualified alert evidence is retained in reports.

## Presentation flow

1. Open `/ai-monitoring` and review the Demo Checklist.
2. Confirm the Pi Stream becomes Online.
3. Confirm Snapshot Upload becomes Online and its age updates.
4. Select an active session if occupancy synchronization is part of the demo.
5. Click **Analyze Latest Sample** in the AI sample section.
6. Explain person and phone-object boxes on the live camera.
7. Point out Behavior AI Safe Mode ON and the planned optional models.
8. Open `/ai-reports` and explain temporary samples versus retained evidence.

## Guardrails preserved

- No database schema change.
- No Raspberry Pi systemd change.
- No new dependency or weight file.
- No modification to live stream, upload, overlay, attendance, or report logic.
- No fake sleeping or emotion output.
- No automatic commit.
