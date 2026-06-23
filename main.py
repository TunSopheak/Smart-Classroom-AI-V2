from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.core.schema import ensure_development_schema
from app.models import (
    ai_event,
    attendance,
    class_group,
    device,
    enrollment,
    session,
    student,
    subject,
    teacher,
    weekly_schedule,
)
from app.routers import (
    ai_monitoring,
    ai_reports,
    attendance as attendance_router,
    classes,
    dashboard,
    devices,
    enrollments,
    iot,
    schedules,
    sessions,
    students,
    subjects,
    teachers,
)

Base.metadata.create_all(bind=engine)
ensure_development_schema()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    iot.start_ai_frame_sampler()
    try:
        yield
    finally:
        await iot.stop_ai_frame_sampler()


app = FastAPI(
    title="Smart Classroom AI Monitoring V2",
    description="Clean FastAPI foundation for Smart Classroom academic, attendance, AI monitoring, and IoT workflows.",
    version="2.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(dashboard.router)
app.include_router(students.router)
app.include_router(classes.router)
app.include_router(enrollments.router)
app.include_router(teachers.router)
app.include_router(subjects.router)
app.include_router(schedules.router)
app.include_router(sessions.router)
app.include_router(attendance_router.router)
app.include_router(attendance_router.qr_router)
app.include_router(ai_monitoring.router)
app.include_router(ai_reports.router)
app.include_router(ai_reports.reports_router)
app.include_router(devices.router)
app.include_router(iot.router)
