# Smart Classroom AI — Demo Checklist

## Before the presentation

- [ ] Connect the presentation computer and Raspberry Pi to the expected
      network.
- [ ] Confirm the configured Pi stream URL is reachable from the presentation
      computer.
- [ ] Confirm the Pi is uploading a snapshot approximately every 10 seconds.
- [ ] Start or select an active classroom session if occupancy sync will be
      demonstrated.
- [ ] Open AI Monitoring and wait for one fresh snapshot after any backend
      restart.
- [ ] Open AI Reports once to confirm the page loads.

## 1. Start the backend

From the project directory and activated virtual environment:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

For development only, `--reload` may be added. Keep the terminal visible enough
to notice startup or request errors.

## 2. Check the Raspberry Pi stream

Open:

```text
http://127.0.0.1:8000/ai-monitoring
```

The **Pi Stream** checklist item should become **Online** and the camera badge
should show **Live Stream Online**. If direct MJPEG fails, the page may use the
snapshot fallback; explain that fallback honestly rather than calling it live
video.

## 3. Check snapshot and device health

The **Snapshot Upload** checklist item should become Online when the latest
upload is no older than 45 seconds. The device card should show:

- Online, Stale, or Offline;
- Snapshot Upload, Heartbeat, both, or No Fresh Signal;
- latest snapshot age;
- Raspberry Pi IP address;
- a friendly status message.

After restarting the backend, wait for the next Pi snapshot. In-memory device
state is intentionally rebuilt from new activity.

## 4. Analyze the latest sample

Scroll to **Latest AI Sample Analysis** and click **Analyze Latest Sample**.
Expected results:

- AI Sampling becomes Completed when the detector returns successfully;
- person and phone counts update;
- overlay detections list their object-based behavior labels;
- Session Sync shows Active, Skipped, or Not Active;
- analysis can complete even when occupancy sync is skipped.

## 5. What to explain to the teacher

### Real now

- real Raspberry Pi live camera;
- periodic snapshot upload;
- backend AI sampling;
- person and phone-object detection;
- object-based behavior overlay schema;
- device health from snapshot upload or heartbeat;
- retained alert evidence and AI Reports;
- safe optional-model adapter architecture.

### Planned, not active

- pose/head-down model;
- head-orientation and looking-around model;
- face-emotion model if face quality is sufficient;
- temporal smoothing and cross-frame tracking;
- validated sustained behavior alerts;
- real relay hardware control.

Behavior AI must remain described as a safe prototype. Do not say the system
currently knows that a student is sleeping, inattentive, happy, or sad.

## 6. Reports demonstration

Open:

```text
http://127.0.0.1:8000/ai-reports
```

Explain that normal monitoring samples are temporary. Only qualified alert
evidence is retained. A phone must be visible to the object detector and pass
its configured confidence threshold before phone evidence can be created.

## Common demo issues

### Device is Offline after backend restart

Wait for the next Pi snapshot upload. The device should become Online from
Snapshot Upload without requiring the legacy heartbeat service.

### Snapshot Upload is Stale

Check network reachability, the Pi upload loop, backend terminal errors, and the
latest snapshot age. A snapshot older than 45 seconds is intentionally stale.

### Occupancy sync is Skipped or Not Active

AI analysis can still be successful. Select or start an active session, then
analyze the next sample. A stale snapshot session ID is reported honestly and
does not make the detector fail.

### Phone is not detected

Move the phone into a clear, well-lit camera view. Detection depends on object
size, angle, occlusion, and model confidence. Do not manufacture an alert.

### Behavior labels remain generic

This is expected. Pose, head-orientation, face-emotion, and temporal models are
planned but not active. Safe Mode ON prevents unvalidated labels.

### Direct stream fails

Verify the configured Pi MJPEG URL and network route. Use the snapshot fallback
only as a fallback and state that clearly during the demo.

## Final 60-second readiness check

- [ ] Backend page loads.
- [ ] Pi Stream shows Online.
- [ ] Snapshot Upload shows Online and a recent age.
- [ ] AI Sampling shows Completed or is ready for manual analysis.
- [ ] Active session is selected if occupancy is being shown.
- [ ] Behavior AI shows Safe Mode ON.
- [ ] AI Reports opens successfully.
- [ ] Presenter can explain real versus planned capabilities.
