# Phase 24B - Raspberry Pi Live Stream Auto-Start Service

## Purpose

Phase 24B runs the real Raspberry Pi live video stream automatically after the Pi boots. The tested systemd unit is:

```text
smart-classroom-pi-live-stream.service
```

The repository includes a reusable service template at:

```text
raspberry_pi/systemd/smart-classroom-pi-live-stream.service
```

The template uses the tested `sopheak` user, repository location, port `8081`, resolution `640x480`, frame rate `10 FPS`, and JPEG quality `70`.

## Avoiding Camera Conflicts

The old snapshot camera client service was disabled because only one process should control the Raspberry Pi camera at a time:

```bash
sudo systemctl disable --now smart-classroom-pi-client.service
```

`smart-classroom-pi-client.service` should remain disabled while the live stream service uses the camera. Running both camera services can prevent Picamera2 from starting or cause unreliable video.

## Install and Enable the Service

From the project directory on the Raspberry Pi:

```bash
cd ~/Smart-Classroom-AI-V2
sudo cp raspberry_pi/systemd/smart-classroom-pi-live-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smart-classroom-pi-live-stream.service
```

The `enable --now` command starts the service immediately and enables it for future boots.

## Check Service Status

```bash
sudo systemctl status smart-classroom-pi-live-stream.service --no-pager
```

Expected state:

```text
Active: active (running)
```

Useful log command:

```bash
sudo journalctl -u smart-classroom-pi-live-stream.service -n 50 --no-pager
```

## Health Test on Raspberry Pi

```bash
curl http://127.0.0.1:8081/health
```

The tested health response reported:

```json
{
  "camera_backend": "Picamera2",
  "frame_available": true,
  "last_error": null
}
```

Additional fields such as resolution, FPS, JPEG quality, and frame number may also be present.

## Test from the Laptop

With the tested Raspberry Pi IP address:

- Health: `http://10.86.94.200:8081/health`
- Stream: `http://10.86.94.200:8081/stream.mjpg`

The laptop and Raspberry Pi must be connected to the same network, and port `8081` must be reachable.

## Dashboard Test

Start the FastAPI backend on the laptop, then open:

```text
http://127.0.0.1:8000/ai-monitoring
```

Expected result:

- The **Real Live Camera** card displays moving video from the Raspberry Pi.
- The source badge changes to **Live from Pi**.
- The backend snapshot fallback remains available if the Pi stream cannot be reached.

## Reboot Test Result

Phase 24B was manually tested on the Raspberry Pi. After reboot:

- `smart-classroom-pi-live-stream.service` remained active.
- `camera_backend` reported `Picamera2`.
- `frame_available` reported `true`.
- `last_error` reported `null`.
- The live stream was reachable again without manually starting the Python script.

## Updating the Service Template

After changing the repository copy, reinstall and restart it:

```bash
sudo cp raspberry_pi/systemd/smart-classroom-pi-live-stream.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart smart-classroom-pi-live-stream.service
sudo systemctl status smart-classroom-pi-live-stream.service --no-pager
```

If the Raspberry Pi username or project directory changes, update `User`, `WorkingDirectory`, and `ExecStart` before installing the unit.

## Limitation

The current live stream process owns the Raspberry Pi camera. The old `smart-classroom-pi-client.service` must remain disabled while this service is active, so its camera-based snapshot upload loop cannot run concurrently.

## Next Phase Recommendation

Phase 25 should combine live streaming and AI snapshot sampling through one camera owner. The live stream process can expose or periodically forward selected in-memory frames for AI analysis, avoiding multiple processes competing for Picamera2 while keeping sampling frequency and CPU use controlled.
