# Architecture

Smart Classroom AI Monitoring V2 is a clean FastAPI project designed around the classroom session lifecycle.

## Core Flow

Teacher + Subject + Class + Day + Time + Room -> WeeklySchedule -> Session -> Attendance + AI Events -> Reports

## Layers

- `app/core`: shared configuration and database setup.
- `app/models`: SQLAlchemy database models, one model per file.
- `app/routers`: FastAPI route modules.
- `app/services`: business workflow services.
- `app/ai`: future OpenCV-based camera and detection modules.
- `app/templates`: Jinja2 pages.
- `app/static`: CSS and JavaScript assets.

## Current Scope

This foundation only includes the dashboard route and basic models. CRUD, QR scanning, AI detection, device integrations, and PDF reports are intentionally deferred.
