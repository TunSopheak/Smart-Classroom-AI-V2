# Phase 22B: AI Frame Sampling Plan

Smart Classroom AI Monitoring

## Status and Scope

This phase is planning only. No application code is changed in Phase 22B.

The goal is to analyze selected Raspberry Pi frames at a controlled interval instead of running AI for every MJPEG response or every uploaded snapshot.

Out of scope:

- Parsing the MJPEG stream for AI input
- Saving every analyzed frame
- Event-based snapshot retention, which remains planned for Phase 22C
- Changes to the YOLO model or detection rules
- Real GPIO or classroom AC light control

## Recommended Design

Use a backend sampling loop with a default interval of **10 seconds**. Allow configuration between 5 and 10 seconds, but do not permit an interval below 5 seconds during the first implementation.

```text
Raspberry Pi camera
    -> capture and upload snapshot
    -> backend saves latest snapshot and keeps at most 30 files
    -> MJPEG endpoint repeatedly displays the latest snapshot
    -> AI sampler wakes every 10 seconds
    -> sampler analyzes only a new, not-yet-analyzed snapshot
    -> latest AI result is stored in the existing in-memory analysis state
    -> dashboard polls and displays the latest result
    -> valid session result updates occupancy and auto-light state
```

The sampler should read the same latest uploaded snapshot used by `/iot/camera/latest` and `/iot/camera/live.mjpg`. It should not request or decode the MJPEG endpoint because that endpoint repeats the same file for display.

## Why 10 Seconds Is Recommended

A 10-second interval provides a safe starting balance:

- It greatly reduces laptop CPU and YOLO workload compared with analyzing each MJPEG response.
- It is frequent enough for a classroom occupancy demonstration.
- It allows the dashboard, which currently polls AI state every 10 seconds, to remain aligned with analysis updates.
- It reduces repeated occupancy and light updates caused by nearly identical frames.

Five seconds can be tested later if inference completes comfortably before the next cycle and the backend remains responsive. The sampler must never start a new inference while the previous inference is still running.

## Snapshot Upload Behavior

Keep `POST /iot/camera/snapshot` as the only source of Raspberry Pi image data.

Each successful upload should continue to:

- Write one snapshot file completely before publishing it as the latest frame.
- Update latest snapshot metadata.
- Run the existing cleanup and keep at most 30 files.
- Accept `device_name`, `session_id`, and `auto_analyze` for backward compatibility.

For sampling mode, the upload should record the associated `session_id` in latest-frame metadata so the later sampling cycle knows which session may receive occupancy updates. If the session ID is missing or invalid, detection may still run, but occupancy and auto-light synchronization must be skipped with a clear status message. The backend must not guess a session.

The Raspberry Pi upload interval and AI sampling interval are separate settings. A useful test configuration is an upload every 5 seconds and AI sampling every 10 seconds. With the existing 30-second upload default, the sampler should simply wait for the next unique upload rather than reanalyzing the same image.

## MJPEG Live Preview Behavior

`GET /iot/camera/live.mjpg` should remain display-only.

- Continue repeating the latest uploaded snapshot at the current 0.75-second MJPEG delay.
- Do not run AI inside the MJPEG generator.
- Do not save MJPEG response frames.
- Multiple dashboard viewers must not increase the AI sampling rate.

This keeps live-preview load separate from AI inference load.

## Auto Analyze Compatibility

The current upload route can analyze immediately when `auto_analyze=true`. Running that mode together with the new sampler would duplicate inference.

Recommended transition:

1. Keep `auto_analyze` supported so existing manual and Raspberry Pi workflows do not break.
2. When backend sampling is enabled, configure the Raspberry Pi with `SMART_CLASSROOM_AUTO_ANALYZE=0`.
3. Make the sampler the single owner of scheduled automatic analysis.
4. Add a shared analysis lock and an analyzed-frame identity check so manual analysis, upload auto-analysis, and scheduled sampling cannot analyze the same file concurrently.
5. Reuse the existing `run_camera_analysis` logic instead of creating a second occupancy/light implementation.

The latest snapshot filename, or a stable combination of filename and upload timestamp, should be the frame identity. The sampler should remember `last_analyzed_filename` and skip the cycle when the latest filename has not changed.

## AI Result State and Dashboard

The existing `/iot/camera/latest` response and dashboard polling should remain the source for the latest AI result.

The analysis state should eventually include:

```text
available
status: idle | pending | analyzing | completed | failed
analyzed_at
analyzed_filename
latest_snapshot_filename
is_stale
analysis
occupancy
occupancy_synced
occupancy_error
light
```

A new upload should not erase the last successful AI result. Instead, it should mark that result as stale or pending until the sampler analyzes the new filename. This prevents the dashboard from losing the last known result between upload and sampling cycles.

The existing manual **Analyze Latest Snapshot** button should remain available. Manual analysis should use the same lock, result state, and frame identity as scheduled analysis.

## Occupancy and Auto-Light Flow

After a successful sampled analysis:

1. Read `person_count` from the existing detector result.
2. Validate the snapshot's session ID using the existing session lookup.
3. Call the existing occupancy update function once for that sampled frame.
4. Let the existing occupancy logic update the occupancy status and software light state.
5. Store the resulting occupancy and light data in the existing camera analysis state.
6. Let dashboard polling render the new state.

Do not add separate light rules inside the sampler. Existing auto-on, empty-room cooldown, auto-off, and event deduplication must remain authoritative.

Because detection can fluctuate, testing should confirm that a single incorrect zero-person result does not cause unsafe rapid light switching. Keep the existing delayed auto-off behavior. Requiring consecutive empty samples can be considered later if real tests show unstable detection.

## Storage Control

Sampled inference should read the latest snapshot bytes from the existing upload folder and process them in memory.

- Do not create a copy for each sampled analysis.
- Do not save annotated frames by default.
- Do not change the 30-file snapshot cleanup limit.
- Keep only compact AI result metadata in the latest analysis state.
- Leave permanent event-image decisions for Phase 22C.

The sampler should handle a file disappearing during cleanup by skipping that cycle and retrying the latest state on the next cycle. It must not crash the backend worker.

## Proposed Configuration

Suggested environment variables for the implementation phase:

```text
SMART_CLASSROOM_AI_SAMPLING_ENABLED=0
SMART_CLASSROOM_AI_SAMPLE_INTERVAL=10
```

Sampling should initially be disabled by default for a safe rollout. Validate the interval at startup and clamp or reject values below 5 seconds.

Only one sampler may run. If the backend is later started with multiple Uvicorn workers, an in-process loop in every worker would duplicate analysis. The first implementation should document and enforce a single backend worker, or later move scheduling to a dedicated worker with a cross-process lock.

## Recommended Implementation Steps

1. Extend snapshot metadata with the uploaded `session_id` and a stable frame identity.
2. Extend analysis metadata with status, analyzed filename, latest filename, and stale state.
3. Refactor the existing camera-analysis call just enough for upload, manual, and sampled triggers to share one guarded function.
4. Add a single backend sampling task with clean application startup and shutdown behavior.
5. Give the task a fresh database session for each sampling cycle and always close it.
6. Add a non-blocking lock so overlapping inference is skipped rather than queued.
7. Read the latest unique snapshot, run the existing detector, and update occupancy/light only when the session is valid.
8. Preserve the last successful result while a newer frame is pending or a cycle fails.
9. Update the dashboard with sampling status and stale/pending feedback without removing manual analysis.
10. Update the Raspberry Pi service configuration to disable upload `auto_analyze` when sampling mode is enabled.
11. Add focused tests before enabling sampling by default.

## Risks and Mitigations

### CPU overload or slow responses

YOLO inference can be expensive. Start at 10 seconds, prevent overlap, and verify that heartbeat, uploads, MJPEG, and dashboard APIs remain responsive.

### Duplicate analysis

Upload auto-analysis, manual analysis, and the sampler can collide. Use one shared lock and frame identity, and disable Pi upload auto-analysis during sampling tests.

### Reanalyzing a repeated MJPEG frame

The MJPEG endpoint repeats the latest file. Sample by unique uploaded filename, not by MJPEG response count.

### Wrong session synchronization

Never apply occupancy to a guessed session. Record and validate the upload session ID; report unsynchronized analysis when it is absent or invalid.

### Stale or deleted files

The 30-file cleanup may remove older files. Read only the currently published latest filename, catch file errors, and retry on the next cycle.

### Multiple backend workers

Each process could start its own sampler. Use one Uvicorn worker for the initial phase and plan a distributed lock or dedicated worker before scaling.

### Detection fluctuation

False zero/person counts can affect occupancy and lighting. Preserve delayed auto-off, monitor consecutive results, and keep all light testing software-only or on a safe low-voltage LED.

### Backend restart

In-memory sampler and analysis state will reset. Startup should wait for a valid latest upload and must not analyze or switch lights based on missing state.

## Safe Testing Plan

1. Back up the current environment configuration and leave sampling disabled.
2. Start the backend with one worker and confirm all Phase 22A and Phase 21B checks still pass.
3. Start the Raspberry Pi service with camera upload enabled and upload auto-analysis disabled.
4. Confirm snapshot upload, MJPEG preview, heartbeat, and light status still work before enabling sampling.
5. Enable a 10-second sample interval and restart the backend cleanly.
6. Confirm no analysis occurs before the first valid snapshot.
7. Confirm each unique filename is analyzed at most once and analysis timestamps are not closer than the configured interval.
8. Confirm repeated MJPEG frames and multiple open dashboards do not create extra inference runs.
9. Confirm the latest AI result remains visible while a newer snapshot is pending.
10. Test with a valid selected session and confirm occupancy and software light synchronization.
11. Test without a session ID and confirm AI results appear but occupancy and light are not incorrectly synchronized.
12. Use the manual analysis button and confirm it does not overlap scheduled inference.
13. Temporarily stop Raspberry Pi uploads and confirm the sampler waits without reanalyzing or crashing.
14. Confirm the snapshot folder stays at 30 files or fewer and no new analyzed-frame folder grows.
15. Monitor laptop CPU, memory, API response time, backend logs, and Pi service logs for at least 10 minutes.
16. Stop the Pi service safely and disable sampling if any regression appears.

## Acceptance Criteria for the Future Implementation

- AI runs no more often than the configured 5-10 second interval.
- The same uploaded filename is not automatically analyzed twice.
- Only one inference runs at a time.
- MJPEG viewing does not trigger AI analysis.
- Snapshot upload and cleanup still keep at most 30 files.
- Analyzed frames are not permanently copied or saved.
- The last successful result remains available with clear stale/pending status.
- Valid session results update occupancy and software auto-light through existing logic.
- Missing or invalid sessions never update another session.
- Upload auto-analysis and scheduled sampling do not run concurrently.
- Manual analysis remains functional.
- No-snapshot, deleted-file, detector-error, and backend-restart cases do not crash the service.

## Phase Status

```text
Phase 22B: PLAN COMPLETE / NO CODE IMPLEMENTED
```
