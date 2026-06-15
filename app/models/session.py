from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    weekly_schedule_id = Column(Integer, ForeignKey("weekly_schedules.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    status = Column(String(30), default="planned", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    weekly_schedule = relationship("WeeklySchedule", back_populates="sessions")
    attendance_records = relationship("Attendance", back_populates="session")
    ai_events = relationship("AIEvent", back_populates="session")
