from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=True, index=True)
    schedule_id = Column(Integer, ForeignKey("weekly_schedules.id"), nullable=True, index=True)
    status = Column(String(30), default="present", nullable=False)
    source = Column(String(30), default="manual", nullable=False)
    method = Column(String(30), default="manual", nullable=False)
    note = Column(String(500), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="attendance_records")
    student = relationship("Student", back_populates="attendance_records")
    class_group = relationship("ClassGroup")
    weekly_schedule = relationship("WeeklySchedule")
