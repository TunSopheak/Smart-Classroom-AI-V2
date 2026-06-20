# Phase 22C: Event-Based Snapshot Saving Plan

Smart Classroom AI Monitoring

## Status and Scope

This phase is planning only. No application code, database schema, route, or Raspberry Pi configuration is changed in Phase 22C.

The goal is to keep ordinary Raspberry Pi snapshots temporary while preserving a small amount of visual evidence for important, explicitly defined classroom events.

## Current Storage Paths

The current system has two different snapshot purposes:

```text
app/static/uploads/iot_snapshots
    Temporary Raspberry Pi uploads used by latest snapshot, MJPEG, and sampling

app/static/uploads/ai_snapshots
    Existing browser-camera phone/attention event snapshots
```

Phase 22C should add a separate Raspberry Pi event-evidence path:

```text
app/static/uploads/iot_events
```

The existing `ai_snapshots` behavior should remain unchanged during the first implementation. A later migration may unify both event-evidence sources after database and report compatibility is proven.

## Recommended Architecture

```text
Raspberry Pi uploads temporary snapshot
    -> temporary file enters iot_snapshots
    -> cleanup keeps at most 30 temporary files
    -> MJPEG repeats latest temporary file for display only
    -> AI sampler analyzes a unique temporary file
    -> existing occupancy and auto-light logic runs
    -> event policy evaluates the AI result and state transition
        -> no important event: save nothing permanently
        -> important event: deduplicate and copy the source bytes once
            -> app/static/uploads/iot_events
            -> create event metadata and optional AIEvent relationship
            -> run event retention cleanup
    -> dashboard and reports show the event and evidence link
```

The MJPEG generator must never create events or save files. Opening more dashboards must not increase event creation.

## What Counts as an Important Event

Event policy should be explicit, configurable, and conservative. A high-confidence ordinary detection alone should not automatically become permanent evidence.

| Event | Proposed prototype rule | Deduplication/cooldown |
|---|---|---|
| Unexpected presence | One or more people detected when the configured room is expected to be empty, confirmed by two consecutive samples | One event per room/device per 60 seconds while presence continues |
| Phone detected | At least one `cell phone` detection at confidence `>= 0.60`; preferably confirmed in two consecutive samples during early testing | Reuse the existing 60-second phone cooldown per session |
| Sudden occupancy change | Stable person count changes by at least 3 people or 50%, then remains changed for two samples | One event per direction/change window, 30-second cooldown |
| Light auto-off | Existing light state actually transitions from ON/Auto Mode to OFF after empty-room delay | Save once for the state transition, never once per poll |
| High-confidence qualifying detection | Confidence exceeds an event-specific threshold and another event rule is satisfied | Does not create an event by itself |
| Sleeping/inattentive behavior | Future model confirms the same warning in at least two of three sampled frames | Suggested 2-5 minute cooldown per session and event type |

Important safeguards:

- Do not treat every person detection as an important event during a normal active class.
- Do not label presence as unexpected without schedule/room context.
- Do not use a low-confidence result as permanent behavioral evidence.
- Keep prototype language such as "possible" or "warning" in reports; AI output does not prove student behavior.
- If no valid source frame is available, log the event without a snapshot rather than attaching an unrelated image.

## Event Evaluation Order

Use one event-policy function after a successful sampled analysis:

1. Validate detector availability and the sampled filename.
2. Load session, schedule, room, occupancy, and current light context.
3. Compare the result with prior stable sampled state.
4. Identify state transitions and candidate event types.
5. Apply confidence, consecutive-sample, and cooldown requirements.
6. Build a deterministic deduplication key.
7. Create the event only if the deduplication key is new.
8. Copy the exact sampled source bytes once into `iot_events`.
9. Link the evidence metadata to the event.
10. Run retention cleanup after the event is safely recorded.

Event evaluation must reuse the existing AI result, occupancy synchronization, and auto-light decisions. It must not run YOLO a second time.

## Connection to Existing Features

### Snapshot upload

`POST /iot/camera/snapshot` remains the temporary image source. Upload should not create a permanent event snapshot before AI evaluation. The existing 30-file temporary cleanup remains active.

### MJPEG live preview

`GET /iot/camera/live.mjpg` remains display-only. It repeatedly reads the latest temporary snapshot and has no event-policy, database, or file-writing responsibility.

### AI frame sampler

The sampler is the preferred trigger for Raspberry Pi event evaluation. It already analyzes unique filenames at a controlled interval. Phase 22C should pass the sampled filename, bytes, session ID, result, occupancy, and light context to the event policy after analysis succeeds.

Upload `auto_analyze` and manual analysis should use the same event-policy entry point if event saving is enabled. The shared analysis lock and database deduplication key must prevent duplicate evidence when triggers overlap.

### AI result dashboard

Keep the latest AI result card unchanged. Add event evidence later as a separate recent-events item with event type, time, confidence/count summary, retention status, and a **View Snapshot** link when a retained file exists.

### Occupancy synchronization

Normal sampled counts continue updating occupancy. Event saving observes meaningful changes but must not perform a second occupancy update.

### Auto light

Existing auto-light logic remains authoritative. A light event is eligible only after the existing logic confirms a real state transition. For delayed auto-off, preserve the sampled empty-frame identity that contributed to the decision. If that file has disappeared, record the transition without attaching an arbitrary latest frame.

### Future reports

AI event lists, CSV, and PDF reports should include an optional event snapshot URL and evidence metadata. Expired evidence must display as expired/unavailable while the textual event record remains valid.

## File Naming and Safe Writes

Recommended filename format:

```text
{event_type}_{utc_timestamp}_{session_or_room}_{source_hash_8}.jpg
```

Example:

```text
phone_usage_warning_20260620_104500_session_12_a1b2c3d4.jpg
```

Safe write procedure:

1. Validate that the source is the exact sampled file and an allowed image type.
2. Calculate SHA-256 from the source bytes.
3. Write to a temporary file inside `iot_events`.
4. Atomically rename the completed temporary file to its final name.
5. Commit database metadata.
6. If the database commit fails, remove only the newly created unreferenced file.

Do not annotate or recompress the image in the first implementation. Copying the original sampled bytes reduces CPU use and preserves an auditable source hash.

## Avoiding Duplicate Event Snapshots

Use several protections together:

### Source-frame identity

Track the Raspberry Pi snapshot filename and SHA-256. The same sampled file must not create the same event type twice.

### Deterministic deduplication key

Suggested key inputs:

```text
device_or_room | session_id_or_none | event_type | source_hash | event_window
```

Store the key with a database unique constraint. An in-memory cooldown alone is insufficient when the backend restarts or uses multiple workers.

### Event cooldown

Apply a per-event cooldown, such as the existing 60 seconds for phone warnings. A continuing condition should update no file until its cooldown expires and the policy explicitly allows another event.

### State-transition rules

Save `light_auto_off` only when the light changes to OFF. Save sudden occupancy changes only after the new count becomes stable. Do not save on dashboard polling or repeated calls to `occupancy_context`.

### Shared analysis lock

Keep the Phase 22B analysis lock so scheduled, manual, and upload auto-analysis cannot evaluate the same frame concurrently. The database unique key remains the final protection.

## Recommended Database Structure

The current `AIEvent` table requires a session and stores snapshot URLs inside text descriptions. Keep that behavior for compatibility, but use normalized metadata for new Raspberry Pi evidence.

Recommended new table: `iot_event_snapshots`

```text
id                       primary key
ai_event_id              nullable foreign key to ai_events
session_id               nullable foreign key to sessions
device_name              nullable string
room                     nullable string
event_type               indexed string
severity                 string
source_snapshot_filename string
event_snapshot_filename  string
event_snapshot_url       nullable string
source_sha256            string
dedupe_key               unique indexed string
confidence               nullable decimal
person_count             nullable integer
phone_count              nullable integer
metadata_json            nullable text/JSON
detected_at              datetime
expires_at               datetime
file_status              retained | expired | missing
created_at               datetime
```

Why `session_id` and `ai_event_id` are nullable:

- Unexpected presence can happen when no class session is active.
- Existing session-linked reports can still join through `ai_event_id`.
- Evidence metadata remains auditable even after retention removes the physical file.

For active sessions, create the `AIEvent` and evidence row together. Continue adding the snapshot URL to the existing AI event description during the compatibility period so current dashboard/report parsing does not break.

Do not store image bytes in SQLite. Store files on disk and keep structured metadata in the database.

## Retention Policy

Recommended prototype policy combines time and count limits:

```text
Keep event snapshots for at most 7 days.
Also keep at most the latest 100 event snapshot files.
Whichever limit removes a file first wins.
```

Cleanup order:

1. Never touch `iot_snapshots` or `ai_snapshots` from the new event cleanup function.
2. Delete event files whose `expires_at` is older than the current UTC time.
3. If more than 100 retained files remain, delete the oldest until 100 remain.
4. Mark database metadata as `expired`, clear or disable the active URL, and keep the event text.
5. Ignore the file currently being written.
6. Catch individual file errors, log them, and continue safely.

Run cleanup after a successful event save and once during application startup. Avoid a fast background cleanup loop.

Configuration proposed for implementation:

```text
SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED=0
SMART_CLASSROOM_EVENT_SNAPSHOT_MAX_FILES=100
SMART_CLASSROOM_EVENT_SNAPSHOT_RETENTION_DAYS=7
```

Event saving should be disabled by default for the first rollout.

## Privacy and Access Safety

Classroom images may contain identifiable students and should be treated as sensitive data.

- Restrict event creation to valid configured devices and sessions/rooms.
- Use unpredictable filenames and never accept a client-provided destination path.
- Do not expose local filesystem paths in API responses.
- Limit retention and document who may review evidence.
- Avoid permanent images for ordinary attendance or normal presence.
- Record thresholds and prototype limitations in reports.
- For production, store event images outside public static files and serve them through an authenticated authorization-checked endpoint. `app/static/uploads/iot_events` is acceptable only for the current local prototype.

## Recommended Implementation Steps

1. Add disabled-by-default event-snapshot configuration and validate retention values.
2. Add an event policy module with pure, testable rules for event eligibility, confidence, transitions, and cooldowns.
3. Add normalized `iot_event_snapshots` metadata with a unique deduplication key and nullable session/event relationships.
4. Add an `iot_events` storage service with validated filenames, hashing, atomic writes, and isolated cleanup.
5. Pass sampled filename, bytes, session, AI result, occupancy, and light transition context from the shared Phase 22B analysis path.
6. Reuse existing phone, occupancy-empty, and light event cooldown/state logic rather than creating parallel rules.
7. Save evidence only after a policy accepts an important event; never save for every sampled frame.
8. Preserve current `AIEvent.description` snapshot-link compatibility while adding normalized metadata.
9. Add retention cleanup after successful saves and at startup.
10. Add recent-event snapshot links and expired/missing states to the dashboard and reports.
11. Add focused unit, integration, concurrency, retention, and rollback tests.
12. Enable only in a controlled prototype environment after storage and privacy review.

## Safe Testing Checklist

### Feature-off regression

- [ ] Start with `SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED=0`.
- [ ] Confirm snapshot upload, MJPEG, manual analysis, upload auto-analysis, and scheduled sampling still work.
- [ ] Confirm no `iot_events` file or database row is created.
- [ ] Confirm temporary snapshots still stay at 30 files or fewer.

### Event-policy tests

- [ ] Normal person detection during an active class creates no permanent snapshot.
- [ ] Low-confidence phone detection creates no event snapshot.
- [ ] A qualifying phone event creates exactly one file and one metadata row.
- [ ] Repeating the same filename/hash creates no duplicate.
- [ ] A second backend worker/process is rejected by the database unique key.
- [ ] Sudden occupancy change requires the configured stable-sample confirmation.
- [ ] Light auto-off creates evidence only on the actual transition.
- [ ] No valid source file logs the event without attaching another frame.
- [ ] Missing/invalid session never updates or attaches evidence to the wrong session.

### Retention tests

- [ ] Create 105 isolated test event files and confirm only the newest 100 remain.
- [ ] Create files older than 7 days and confirm they expire.
- [ ] Confirm temporary `iot_snapshots` and existing `ai_snapshots` are untouched.
- [ ] Confirm database rows remain with `file_status=expired` after file removal.
- [ ] Confirm reports show expired/unavailable instead of a broken active link.
- [ ] Confirm a cleanup failure does not crash upload, sampling, or dashboard routes.

### Hardware/integration tests

- [ ] Start the backend with one worker and event saving disabled; verify the baseline first.
- [ ] Start the Raspberry Pi service and confirm upload, MJPEG, sampler, occupancy, and software light behavior.
- [ ] Enable event saving with a 7-day/100-file limit.
- [ ] Trigger only controlled, consented prototype scenarios.
- [ ] Confirm qualifying sampled filename and event evidence hash match.
- [ ] Confirm multiple open dashboards do not create extra event files.
- [ ] Monitor CPU, disk use, logs, and database consistency for at least 10 minutes.
- [ ] Stop the Raspberry Pi service safely after testing.

## Risks and Mitigations

### False or harmful behavioral conclusions

Use conservative thresholds, consecutive-sample confirmation, neutral wording, and human review. Never treat the snapshot as proof of misconduct.

### Privacy exposure

Minimize saved events, enforce retention, restrict reviewers, and plan authenticated file delivery before production.

### Storage growth

Use both 7-day and 100-file limits, cleanup after saves/startup, and expose storage status for monitoring.

### Duplicate files and events

Combine frame identity, SHA-256, cooldowns, transition rules, a shared lock, and a database unique key.

### File/database inconsistency

Use atomic file writes, compensate on database failure, preserve metadata after expiry, and detect missing files in status/report rendering.

### Wrong snapshot attached to delayed events

Carry the source sampled filename through occupancy/light state. If it is unavailable, save no snapshot rather than using the latest unrelated frame.

### Multiple workers

Do not rely only on in-memory state. Use a unique database deduplication key and test concurrent event creation.

## Rollback Plan

1. Set `SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED=0` and restart the backend.
2. Keep snapshot upload, MJPEG, Phase 22B sampling, occupancy, and auto-light running unchanged.
3. Stop creating new `iot_events` files and metadata while leaving existing evidence readable for review.
4. Do not mass-delete evidence during rollback. Apply the documented retention job or an explicitly approved cleanup later.
5. Hide new dashboard/report controls if their metadata is unavailable, while preserving existing AI event rendering.
6. Keep new database columns/table backward-compatible; do not drop schema during an emergency rollback.
7. Restore from a database backup only if a migration failure affected existing data.

## Acceptance Criteria for Future Implementation

- Ordinary uploads, MJPEG responses, and non-event sampled frames create no permanent evidence.
- Important-event rules are explicit, configurable, and tested.
- Each qualifying source frame/event window creates at most one event snapshot.
- Event images are stored separately from temporary snapshots.
- Temporary cleanup remains capped at 30 files.
- Event cleanup enforces both 7 days and 100 files without touching other folders.
- Event metadata remains usable after its physical image expires.
- Occupancy and auto-light logic execute once and remain authoritative.
- Reports link the correct retained evidence and clearly handle expired/missing files.
- Disabling the feature restores the Phase 22B behavior without data loss.

## Phase Status

```text
Phase 22C: PLAN COMPLETE / NO CODE IMPLEMENTED
```
