# Phase 25 - Live Stream with Snapshot Upload

## Purpose

Phase 25 combines real Raspberry Pi MJPEG video and periodic backend snapshot upload in one process. This allows the dashboard live stream and backend AI sampling to work together without two services competing for Picamera2.

The active service remains:

```text
smart-classroom-pi-live-stream.service
```

The old camera client must remain disabled:

```bash
sudo systemctl disable --now smart-classroom-pi-client.service
```

## Why One Camera Owner Avoids Conflicts

Picamera2 should be controlled by one process. Previously, the live stream service and snapshot client would both try to open the camera, causing startup failures or unreliable capture.

Phase 25 keeps `pi_live_stream.py` as the only camera owner:

1. The camera capture thread produces JPEG frames at the configured live-stream FPS.
2. The latest JPEG is held in memory for MJPEG viewers.
3. An optional uploader thread reads the same immutable in-memory JPEG every configured interval.
4. The uploader sends that JPEG to the existing FastAPI snapshot endpoint.
5. No second camera connection is opened and no snapshot file is written on the Pi.

## Upload Workflow

When snapshot upload is enabled, the live stream process sends:

```text
POST {SMART_CLASSROOM_BACKEND_URL}/iot/camera/snapshot
```

Multipart content:

- File field: `snapshot`
- Filename: `live_stream_snapshot.jpg`
- Content type: `image/jpeg`
- Form field: `device_name`
- Form field: `auto_analyze`
- Form field: `session_id` only when configured

The demo service uploads every 10 seconds with `auto_analyze=false`. The backend sampler remains responsible for scheduled AI analysis.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `SMART_CLASSROOM_BACKEND_URL` | `http://10.86.94.199:8000` | FastAPI backend reachable from the Pi |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_ENABLED` | `0` | Enables periodic upload when set to `1`, `true`, `yes`, or `on` |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_INTERVAL` | `10` | Seconds between upload attempts |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_DEVICE_NAME` | `Raspberry Pi 5 Live Stream` | Device label sent with snapshots |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_AUTO_ANALYZE` | `false` | Requests immediate upload-time analysis when enabled |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_SESSION_ID` | empty | Optional session associated with uploaded snapshots |
| `SMART_CLASSROOM_LIVE_SNAPSHOT_TIMEOUT` | `10` | Backend request timeout in seconds |

If upload remains disabled, live streaming behaves as it did in Phase 24.

## Demo Service Configuration

The repository service template enables uploads for the tested demo:

```ini
Environment=SMART_CLASSROOM_BACKEND_URL=http://10.86.94.199:8000
Environment=SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_ENABLED=1
Environment=SMART_CLASSROOM_LIVE_SNAPSHOT_UPLOAD_INTERVAL=10
Environment="SMART_CLASSROOM_LIVE_SNAPSHOT_DEVICE_NAME=Raspberry Pi 5 Live Stream"
Environment=SMART_CLASSROOM_LIVE_SNAPSHOT_AUTO_ANALYZE=false
Environment=SMART_CLASSROOM_LIVE_SNAPSHOT_SESSION_ID=11
Environment=SMART_CLASSROOM_LIVE_SNAPSHOT_TIMEOUT=10
```

Change the session ID when the active demo session changes. Leave it empty when snapshots should not be associated with a specific session.

## Update the Raspberry Pi Service

From the repository on the Raspberry Pi:

```bash
sudo cp raspberry_pi/systemd/smart-classroom-pi-live-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart smart-classroom-pi-live-stream.service
```

Check status and recent logs:

```bash
sudo systemctl status smart-classroom-pi-live-stream.service --no-pager
sudo journalctl -u smart-classroom-pi-live-stream.service -n 50 --no-pager
```

Expected logs include whether snapshot upload is enabled and the backend response status for successful uploads. Upload failures are logged without stopping live video.

## Health Check

On the Raspberry Pi:

```bash
curl http://127.0.0.1:8081/health
```

Phase 25 adds these fields:

```json
{
  "snapshot_upload_enabled": true,
  "snapshot_upload_interval": 10,
  "snapshot_upload_last_ok": true,
  "snapshot_upload_last_at": "2026-06-22T00:00:00+00:00",
  "snapshot_upload_last_error": null,
  "backend_url": "http://10.86.94.199:8000"
}
```

Before the first attempt, the last-result fields can be `null`.

## End-to-End Tests

### Laptop live stream

Open:

```text
http://10.86.94.200:8081/stream.mjpg
```

The video should continue moving while snapshot uploads occur.

### Backend latest snapshot

Open:

```text
http://127.0.0.1:8000/iot/camera/latest
```

The snapshot metadata and upload time should update approximately every 10 seconds.

### Backend sampler

Open:

```text
http://127.0.0.1:8000/iot/camera/sampler/status
```

When backend sampling is enabled, the sampler should process newly uploaded snapshots according to its configured interval.

## Backend Availability

The Raspberry Pi must be able to reach:

```text
http://10.86.94.199:8000
```

Start FastAPI with a network-accessible bind address, and ensure the laptop firewall allows port `8000`.

If the backend is offline or times out:

- The upload attempt is marked failed in `/health`.
- The error is printed in the systemd journal.
- The uploader waits for the next interval and tries again.
- The MJPEG server and live dashboard video continue running.

## Storage Behavior

The Raspberry Pi does not save periodic snapshots to disk. Uploads reuse the latest JPEG bytes already encoded for live streaming. Backend snapshot storage and retention continue to use the existing application behavior.

## Limitations

- `smart-classroom-pi-client.service` must remain disabled to preserve one camera owner.
- The service template contains demo network addresses and session ID `11`; update them when the network or active session changes.
- AI processing remains on the backend and depends on backend sampler configuration and laptop resources.
- Uploads use the most recently encoded live frame rather than a separate high-resolution still capture.
