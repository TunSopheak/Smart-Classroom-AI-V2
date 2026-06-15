from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Time, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("weekly_schedules.id"), nullable=False, index=True)
    weekly_schedule_id = Column(Integer, nullable=True)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    session_date = Column(Date, nullable=False)
    title = Column(String(255), nullable=False)
    start_time = Column(Time, nullable=False)
    late_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=False)
    room = Column(String(100), nullable=False)
    status = Column(String(30), default="scheduled", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    weekly_schedule = relationship("WeeklySchedule", back_populates="sessions", foreign_keys=[schedule_id])
    class_group = relationship("ClassGroup")
    teacher = relationship("Teacher")
    subject = relationship("Subject")
    attendance_records = relationship("Attendance", back_populates="session")
    ai_events = relationship("AIEvent", back_populates="session")
