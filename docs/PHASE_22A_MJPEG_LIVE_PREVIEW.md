# Phase 22A: MJPEG Live Video Preview

Smart Classroom AI Monitoring

## Goal

Show a simple live camera preview on the AI Monitoring dashboard without permanently saving additional live frames.

## Implementation

The backend provides:

```text
GET /iot/camera/live.mjpg
```

This endpoint uses `multipart/x-mixed-replace` to repeatedly stream the latest snapshot already uploaded by the Raspberry Pi. It waits 0.75 seconds between frames to limit CPU usage. If no snapshot is available, the stream stays open and waits safely for a future upload.

The dashboard now shows both:

```text
Latest Raspberry Pi Camera Snapshot
Live Camera Preview
```

The live preview uses:

```html
<img src="/iot/camera/live.mjpg">
```

## Storage Behavior

The MJPEG endpoint only reads the latest uploaded snapshot. It does not create or save another image.

The existing snapshot upload cleanup remains unchanged and keeps at most 30 files in:

```text
app/static/uploads/iot_snapshots
```

AI frame sampling and event-based snapshot saving are not included in this phase.

## Test Procedure

On the backend laptop:

```powershell
cd D:\IT\IT-RUPP\Y3\CN\Project\Smart-Classroom-AI-V2
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

On the Raspberry Pi:

```bash
cd ~/Smart-Classroom-AI-V2
sudo systemctl start smart-classroom-pi-client.service
sudo journalctl -u smart-classroom-pi-client.service -f
```

Open the dashboard:

```text
http://10.86.94.199:8000/ai-monitoring
```

Confirm that the latest snapshot remains visible, the live preview updates when new snapshots arrive, AI results and occupancy/light state still update, and the snapshot folder remains at 30 files or fewer.

Check the backend snapshot count:

```powershell
(Get-ChildItem app\static\uploads\iot_snapshots -File).Count
```

After testing, stop the Raspberry Pi service safely:

```bash
sudo systemctl stop smart-classroom-pi-client.service
sudo systemctl status smart-classroom-pi-client.service --no-pager
```

## Phase Status

```text
Phase 22A: IMPLEMENTED / READY FOR HARDWARE TESTING
```
