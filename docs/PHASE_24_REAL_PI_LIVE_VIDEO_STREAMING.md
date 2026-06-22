# Phase 24 - Real Raspberry Pi Live Video Streaming

## What Was Implemented

Phase 24 adds a standalone Raspberry Pi MJPEG service and connects the AI Monitoring dashboard directly to it.

- `raspberry_pi/pi_live_stream.py` runs a small threaded HTTP server.
- `GET /stream.mjpg` provides a multipart MJPEG stream.
- `GET /health` returns JSON camera and stream status.
- Picamera2 is preferred when available.
- OpenCV `VideoCapture(0)` is used as a safe fallback when Picamera2 cannot start.
- One bounded background capture loop produces JPEG frames for all connected browsers.
- Frames stay in memory and are never written to disk.
- The dashboard first attempts the configured direct Pi stream.
- If the direct stream fails or does not produce a frame promptly, the existing backend `/iot/camera/live.mjpg` latest-snapshot preview is used automatically.
- A **Retry Direct Stream** action allows the demo to reconnect after the Pi service starts.

Existing snapshot upload, snapshot preview, manual and automatic AI analysis, occupancy synchronization, auto-light behavior, event snapshots, and routes are unchanged.

## Why Direct Pi MJPEG

Direct MJPEG is intentionally simple and demo-friendly:

- The browser connects directly to the Pi, avoiding extra video traffic and encoding work on the FastAPI laptop.
- MJPEG works in a normal `<img>` element without a heavy frontend player or WebRTC stack.
- The frame rate, resolution, and JPEG quality are bounded for predictable CPU and network use.
- Multiple viewers share the same camera capture loop instead of opening the camera repeatedly.
- The backend remains focused on application data, AI sampling, events, occupancy, and light state.

## Raspberry Pi Setup

Install camera dependencies if they are not already present:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-opencv
```

Start the stream from the repository:

```bash
cd ~/Smart-Classroom-AI-V2
python3 raspberry_pi/pi_live_stream.py
```

Default service settings:

- Bind address: `0.0.0.0`
- Port: `8081`
- Resolution: `640x480`
- Frame rate: `10 FPS`
- JPEG quality: `70`

Expected startup output includes:

```text
Camera backend: Picamera2
Health: http://<raspberry-pi-ip>:8081/health
Stream: http://<raspberry-pi-ip>:8081/stream.mjpg
Frames are kept in memory and are not saved to disk.
```

Stop safely with `Ctrl+C`. The HTTP server, capture thread, and camera are closed before exit.

## Test URLs

With the demo Raspberry Pi address:

- Health: `http://10.86.94.200:8081/health`
- Live stream: `http://10.86.94.200:8081/stream.mjpg`

The laptop browser must be able to reach port `8081` on the Raspberry Pi. Both devices should be connected to the same network.

## Configuration

### Backend dashboard stream URL

Set this before starting FastAPI when the Raspberry Pi address changes:

```bash
export SMART_CLASSROOM_PI_STREAM_URL="http://10.86.94.200:8081/stream.mjpg"
```

PowerShell equivalent:

```powershell
$env:SMART_CLASSROOM_PI_STREAM_URL = "http://10.86.94.200:8081/stream.mjpg"
```

The default is `http://10.86.94.200:8081/stream.mjpg`.

### Raspberry Pi stream settings

```bash
export SMART_CLASSROOM_LIVE_STREAM_HOST="0.0.0.0"
export SMART_CLASSROOM_LIVE_STREAM_PORT="8081"
export SMART_CLASSROOM_LIVE_STREAM_WIDTH="640"
export SMART_CLASSROOM_LIVE_STREAM_HEIGHT="480"
export SMART_CLASSROOM_LIVE_STREAM_FPS="10"
export SMART_CLASSROOM_LIVE_STREAM_JPEG_QUALITY="70"
python3 raspberry_pi/pi_live_stream.py
```

For lower CPU or network use, reduce FPS, resolution, or JPEG quality. The script bounds FPS to 1-30 and JPEG quality to 30-95.

## Dashboard Behavior

The **Real Live Camera** card uses this order:

1. Load `SMART_CLASSROOM_PI_STREAM_URL` directly from the Raspberry Pi.
2. Show **Live from Pi** when the direct stream produces a frame.
3. On load failure or timeout, switch to `/iot/camera/live.mjpg` and show **Snapshot fallback**.
4. Use **Retry Direct Stream** after starting or reconnecting the Pi.

The fallback endpoint remains the existing backend preview based on the latest uploaded Raspberry Pi snapshot. It is not presented as high-frame-rate video.

## Storage and AI Sampling

The direct live server does not save frames or create a large image archive. It holds only the current encoded JPEG frame in memory for connected clients.

AI sampling remains separate from live display. The existing Raspberry Pi client can continue uploading snapshots, and backend AI sampling can still analyze the latest snapshot every 10 seconds. Occupancy, phone detection, auto-light updates, and event snapshot behavior continue through their existing workflows.

## Verification

```powershell
python -m compileall main.py app raspberry_pi
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Verify:

- `http://127.0.0.1:8000/ai-monitoring` returns HTTP 200.
- `http://127.0.0.1:8000/iot/camera/live.mjpg` still returns the existing multipart snapshot stream.
- The rendered page contains the configured Pi stream URL and backend fallback URL.
- On Raspberry Pi, `/health` returns JSON and `/stream.mjpg` displays moving camera frames.
- Disconnecting or stopping the Pi service causes the dashboard to select the snapshot fallback.

## Known Limitations

- Hardware streaming must be verified on the physical Raspberry Pi because Picamera2 and `/dev/video0` are not available on a normal Windows development machine.
- MJPEG uses more bandwidth than H.264/WebRTC at similar quality, so the defaults intentionally use 640x480 at 10 FPS.
- The browser must be able to reach the Raspberry Pi directly; client isolation on some hotspots or Wi-Fi networks can block device-to-device traffic.
- An HTTPS-hosted dashboard may block the default HTTP Pi stream as mixed content. The current local demo uses HTTP on both devices.
- The six-second dashboard fallback favors reliable demos. If the Pi starts slowly, use **Retry Direct Stream** once `/health` is ready.
