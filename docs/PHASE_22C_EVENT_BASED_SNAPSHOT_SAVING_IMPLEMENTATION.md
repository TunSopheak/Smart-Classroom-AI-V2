# Phase 22C: Event-Based Snapshot Saving Implementation

Smart Classroom AI Monitoring

## Goal

Preserve Raspberry Pi evidence only for conservative events accepted after scheduled backend AI sampling. Ordinary uploads, MJPEG frames, dashboard views, manual analysis, and upload `auto_analyze` do not create Phase 22C evidence files.

## Default Configuration

Event evidence is disabled by default:

```text
SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED=0
SMART_CLASSROOM_EVENT_SNAPSHOT_RETENTION_DAYS=7
SMART_CLASSROOM_EVENT_SNAPSHOT_MAX_FILES=100
SMART_CLASSROOM_EVENT_COOLDOWN_SECONDS=60
SMART_CLASSROOM_PHONE_EVENT_CONFIDENCE=0.60
```

Invalid integer settings use their defaults and are clamped to at least 1. Phone confidence is clamped between 0 and 1.

## Evidence Folder

When the feature is enabled, the backend creates:

```text
app/static/uploads/iot_events
```

The folder is separate from:

```text
app/static/uploads/iot_snapshots
app/static/uploads/ai_snapshots
```

The feature does not create the event folder or any event file while disabled.

## Implemented Event Rules

### Phone detected

Evidence is eligible only when:

- The sampled analysis is available.
- The snapshot has a session ID.
- A `cell phone`/`phone` detection has confidence at or above the configured threshold.
- The event cooldown for the event type, session, and device has expired.

### Light auto-off

Evidence is eligible only when the existing software light state changes from at least one light ON to both lights OFF during sampled analysis. Event storage does not change the light state itself.

### Unexpected presence

This rule is intentionally not enabled. The current sampler does not yet provide reliable scheduled-empty-room context, so the backend does not guess.

## Sampling Integration

The Phase 22B sampler performs YOLO analysis once and returns the existing analysis, occupancy, and light results. Phase 22C then evaluates those returned values and the original sampled bytes.

```text
Unique temporary snapshot
    -> existing YOLO analysis (once)
    -> existing occupancy and auto-light logic
    -> event eligibility evaluation
    -> optional atomic evidence copy
```

No second YOLO call is made. MJPEG and dashboard routes contain no Phase 22C save calls.

## Atomic Storage and Deduplication

For a qualifying source frame, the service:

1. Computes SHA-256 from the original sampled bytes.
2. Writes those bytes to a temporary file in `iot_events`.
3. Atomically renames the completed temporary file.
4. Stores simple in-memory event metadata.
5. Applies retention cleanup.

One source filename can create at most one evidence file. If the same frame qualifies for phone and light events, the single metadata record lists both event types. Cooldowns are maintained independently per event type, session, and device.

In-memory metadata includes event type(s), evidence URL, source filename/hash, session, device, counts, confidence, and creation time. Metadata resets when the backend restarts; retained files remain visible in the total file count.

## Retention

After every successful evidence save and during enabled startup:

- Files older than the configured retention days are removed.
- If the folder exceeds the configured maximum, the oldest files are removed.
- Temporary Pi snapshots and existing browser AI snapshots are never touched by this cleanup.
- Individual file failures are recorded without crashing the sampler.

## Status Endpoint

```text
GET /iot/camera/events/status
```

The response includes:

```text
enabled
event_folder
event_url_prefix
max_files
retention_days
cooldown_seconds
phone_confidence_threshold
total_event_files
recent_events
last_error
```

## Disabled-Mode Test

On the backend laptop:

```powershell
cd D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2
.\.venv\Scripts\Activate.ps1

Remove-Item Env:SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED -ErrorAction SilentlyContinue
Remove-Item Env:SMART_CLASSROOM_EVENT_SNAPSHOT_RETENTION_DAYS -ErrorAction SilentlyContinue
Remove-Item Env:SMART_CLASSROOM_EVENT_SNAPSHOT_MAX_FILES -ErrorAction SilentlyContinue
Remove-Item Env:SMART_CLASSROOM_EVENT_COOLDOWN_SECONDS -ErrorAction SilentlyContinue
Remove-Item Env:SMART_CLASSROOM_PHONE_EVENT_CONFIDENCE -ErrorAction SilentlyContinue

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In another PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/events/status |
    ConvertTo-Json -Depth 6

Invoke-RestMethod http://127.0.0.1:8000/iot/camera/sampler/status |
    ConvertTo-Json -Depth 4

Invoke-WebRequest http://127.0.0.1:8000/ai-monitoring -UseBasicParsing |
    Select-Object StatusCode

if (Test-Path app\static\uploads\iot_events) {
    (Get-ChildItem app\static\uploads\iot_events -File |
        Where-Object Extension -In '.jpg', '.jpeg', '.png').Count
} else {
    0
}
```

Expected event status is `enabled: false`; the event image count remains unchanged after uploads, MJPEG viewing, and waiting through sampler intervals.

## Enabled-Mode Test

Stop the backend, then use one worker:

```powershell
$env:SMART_CLASSROOM_AI_SAMPLING_ENABLED="1"
$env:SMART_CLASSROOM_AI_SAMPLE_INTERVAL="10"
$env:SMART_CLASSROOM_EVENT_SNAPSHOTS_ENABLED="1"
$env:SMART_CLASSROOM_EVENT_SNAPSHOT_RETENTION_DAYS="7"
$env:SMART_CLASSROOM_EVENT_SNAPSHOT_MAX_FILES="100"
$env:SMART_CLASSROOM_EVENT_COOLDOWN_SECONDS="60"
$env:SMART_CLASSROOM_PHONE_EVENT_CONFIDENCE="0.60"

uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Configure the Raspberry Pi service with camera upload enabled, upload auto-analysis disabled, and a valid active session ID:

```text
SMART_CLASSROOM_ENABLE_CAMERA=1
SMART_CLASSROOM_AUTO_ANALYZE=0
SMART_CLASSROOM_SESSION_ID=<ACTIVE_SESSION_ID>
```

Then start and monitor the Pi:

```bash
cd ~/Smart-Classroom-AI-V2
sudo systemctl start smart-classroom-pi-client.service
sudo journalctl -u smart-classroom-pi-client.service -f
```

Check status on the laptop:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/events/status |
    ConvertTo-Json -Depth 6

Invoke-RestMethod http://127.0.0.1:8000/iot/camera/sampler/status |
    ConvertTo-Json -Depth 4

Invoke-RestMethod http://127.0.0.1:8000/iot/camera/latest |
    ConvertTo-Json -Depth 6

(Get-ChildItem app\static\uploads\iot_snapshots -File).Count
(Get-ChildItem app\static\uploads\iot_events -File |
    Where-Object Extension -In '.jpg', '.jpeg', '.png').Count
```

Use only a controlled, consented prototype scene to test phone confidence. Repeated evaluation of the same uploaded filename must not increase the event file count. A new qualifying frame inside the 60-second cooldown also must not create another phone evidence file.

Open the dashboard and verify MJPEG independently:

```text
http://10.86.94.199:8000/ai-monitoring
http://10.86.94.199:8000/iot/camera/live.mjpg
```

Stop the Pi safely after testing:

```bash
sudo systemctl stop smart-classroom-pi-client.service
sudo systemctl status smart-classroom-pi-client.service --no-pager
```

## Expected Results

- Disabled mode creates no event evidence.
- Enabled mode saves the exact original sampled bytes for qualifying events.
- A source filename creates no more than one evidence file.
- Phone cooldown prevents repeated evidence for 60 seconds by default.
- Light evidence requires a real ON-to-OFF transition.
- Unexpected presence creates no evidence in this implementation.
- MJPEG and dashboard viewing create no event files.
- Sampler errors and event-storage errors remain isolated.
- Temporary snapshot cleanup remains capped at 30 files.
- Event retention remains capped at 100 files and 7 days by default.

## Phase Status

```text
Phase 22C: IMPLEMENTED / DISABLED BY DEFAULT / READY FOR HARDWARE TESTING
```
