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
