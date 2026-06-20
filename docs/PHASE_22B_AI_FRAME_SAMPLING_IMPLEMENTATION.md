# Phase 22B: Backend AI Frame Sampling Implementation

Smart Classroom AI Monitoring

## Goal

Add a safe backend task that can analyze the latest unique Raspberry Pi snapshot at a controlled interval without analyzing MJPEG response frames or saving extra image copies.

## Default Configuration

The sampler is disabled by default:

```text
SMART_CLASSROOM_AI_SAMPLING_ENABLED=0
SMART_CLASSROOM_AI_SAMPLE_INTERVAL=10
```

The minimum accepted interval is 5 seconds. Invalid interval values fall back to 10 seconds, and values below 5 are raised to 5.

## Status Endpoint

```text
GET /iot/camera/sampler/status
```

Example disabled response:

```json
{
  "ok": true,
  "sampler": {
    "enabled": false,
    "running": false,
    "interval_seconds": 10,
    "min_interval_seconds": 5,
    "last_sampled_file": null,
    "last_sampled_at": null,
    "last_error": null,
    "skipped_reason": "AI frame sampling is disabled."
  }
}
```

## Sampling Flow

When enabled, one sampler task starts with the FastAPI application and stops during application shutdown.

```text
Wait for configured interval
    -> read latest snapshot metadata
    -> skip if no snapshot exists
    -> skip if filename was already analyzed
    -> skip if another AI analysis holds the shared lock
    -> read the existing snapshot file into memory
    -> run the existing camera analysis logic
    -> reuse existing occupancy and software auto-light synchronization
    -> update sampler and existing AI result state
```

The snapshot upload now retains its optional `session_id` in latest-snapshot metadata. Sampled detection can therefore synchronize occupancy only for the supplied valid session. It does not guess a session.

## Compatibility and Safety

- `POST /iot/camera/snapshot` keeps its existing `auto_analyze` behavior.
- Upload auto-analysis and manual latest-snapshot analysis use the same inference lock as the sampler.
- A frame successfully handled by upload auto-analysis or manual analysis is marked so the sampler does not analyze that filename again.
- `GET /iot/camera/live.mjpg` remains display-only and contains no AI calls.
- Sampled analysis reads the existing uploaded file and creates no analyzed-frame copy.
- Existing cleanup continues to keep at most 30 uploaded snapshots.
- A missing or unreadable latest file records a safe status instead of stopping the application.
- The initial implementation should use one Uvicorn worker because sampler state and locking are process-local.

When sampling is enabled on the backend, configure the Raspberry Pi with upload auto-analysis disabled to make scheduled sampling the automatic owner:

```text
SMART_CLASSROOM_AUTO_ANALYZE=0
```

Backward-compatible `auto_analyze=true` requests are still supported.

## Disabled-by-Default Test

On the backend laptop:

```powershell
cd D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2
.\.venv\Scripts\Activate.ps1
Remove-Item Env:SMART_CLASSROOM_AI_SAMPLING_ENABLED -ErrorAction SilentlyContinue
Remove-Item Env:SMART_CLASSROOM_AI_SAMPLE_INTERVAL -ErrorAction SilentlyContinue
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/sampler/status | ConvertTo-Json -Depth 4
Invoke-WebRequest http://127.0.0.1:8000/ai-monitoring -UseBasicParsing | Select-Object StatusCode
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/latest | ConvertTo-Json -Depth 6
(Get-ChildItem app\static\uploads\iot_snapshots -File).Count
```

Expected sampler values are `enabled: false`, `running: false`, and no sampled filename or timestamp. Waiting longer than 10 seconds must not change them.

## Enabled Sampling Test

Stop the backend, then start it with one worker and a 10-second interval:

```powershell
$env:SMART_CLASSROOM_AI_SAMPLING_ENABLED="1"
$env:SMART_CLASSROOM_AI_SAMPLE_INTERVAL="10"
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Start the Raspberry Pi client with camera upload enabled and upload auto-analysis disabled. After a new upload, check the status twice:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/sampler/status | ConvertTo-Json -Depth 4
Start-Sleep -Seconds 12
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/sampler/status | ConvertTo-Json -Depth 4
Invoke-RestMethod http://127.0.0.1:8000/iot/camera/latest | ConvertTo-Json -Depth 6
```

Expected results:

- `enabled` and `running` are true.
- `last_sampled_file` matches the latest uploaded filename.
- `last_sampled_at` is populated.
- A repeated cycle with no new upload reports that the latest snapshot was already analyzed.
- AI result, occupancy, and software light state use the existing response fields.
- The dashboard and MJPEG preview remain available.
- The snapshot count remains at or below 30.

## Raspberry Pi Service Test

```bash
cd ~/Smart-Classroom-AI-V2
sudo systemctl start smart-classroom-pi-client.service
sudo journalctl -u smart-classroom-pi-client.service -f
```

After testing:

```bash
sudo systemctl stop smart-classroom-pi-client.service
sudo systemctl status smart-classroom-pi-client.service --no-pager
```

## Phase Status

```text
Phase 22B: IMPLEMENTED / DISABLED BY DEFAULT / READY FOR HARDWARE TESTING
```
