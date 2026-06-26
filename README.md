# Smart Classroom AI Monitoring V2

This is a new Version 2 project for Smart Classroom AI Monitoring.

Version 2 starts from a clean FastAPI architecture. It does not copy the messy Version 1 backend structure, and it avoids a single huge `main.py`.

## Vision

Teacher + Subject + Class + Day + Time + Room -> WeeklySchedule -> Session -> Attendance + AI Events -> Reports

The system is designed so academic scheduling, attendance, AI monitoring, and IoT device status can grow together.

## Current Demo Status

Smart Classroom AI Monitoring Version 2 currently supports a real Raspberry Pi
live stream, periodic snapshot uploads, backend AI sampling, person/phone object
overlays, alert evidence reports, and demo-safe device reliability status. The
behavior architecture includes safe adapters for future pose, head orientation,
face emotion, and temporal models; those optional models are planned and are
not active in the current demo.

## Original Foundation Scope

The original clean-slate milestone included:

- FastAPI application foundation.
- SQLite development database setup.
- SQLAlchemy models split into separate files.
- Dashboard routes:
  - `GET /`
  - `GET /dashboard`
- Jinja2 templates and static assets.
- Architecture and planning documentation.

Deferred from that original milestone and implemented in later phases where noted:

- CRUD screens or APIs.
- QR attendance scanning.
- AI detection.
- PDF report generation.
- IoT device integrations.

## Project Structure

```text
app/
  core/
  models/
  schemas/
  routers/
  services/
  ai/
  templates/
  static/
docs/
tests/
main.py
requirements.txt
```

## Run Locally

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Start the development server:

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

FastAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

## Stage 1 Face Attendance Demo

Face attendance uses OpenCV Haar face detection plus LBPH recognition from
`opencv-contrib-python`. It does not use heavy `dlib` or `face_recognition`
dependencies. If the app logs `LBPH face recognition is unavailable`, reinstall
dependencies with `pip install -r requirements.txt` and restart the server.

Dataset folder format:

```text
models/
  face_dataset/
    S001/
      image_01.jpg
      image_02.jpg
      image_03.jpg
    S002/
      image_01.jpg
      image_02.jpg
```

The folder name should match an existing `students.student_code`. A folder like
`S001_StudentName` also works because the system uses the first `_` segment as a
fallback student code.

To train 10 group members for the demo:

1. Create 10 student records in the app and enroll them in the demo class.
2. Create one folder per student under `models/face_dataset/`.
3. Add 8-15 clear face images per student with different angles and lighting.
4. Start an active class session.
5. Open `/ai-monitoring`, select the session, start the camera, then start
   backend AI analysis. The first analysis trains and saves
   `models/face_lbph_model.yml` automatically.

Laptop webcam demo:

```powershell
$env:CAMERA_BACKEND="opencv"
$env:CAMERA_SOURCE="0"
uvicorn main:app --reload
```

Raspberry Pi camera switch later:

```powershell
$env:CAMERA_BACKEND="picamera"
$env:CAMERA_SOURCE="pi"
uvicorn main:app --reload
```

After adding/changing dataset images, delete the model `.yml` and `.labels.json`
files to retrain.

Stage 1 records face attendance into the existing attendance table. The existing
`recorded_at` field is used as the first seen time, QR attendance remains as a
backup, duplicate face attendance is skipped per active session, and closing a
session still marks missing enrolled students absent.
