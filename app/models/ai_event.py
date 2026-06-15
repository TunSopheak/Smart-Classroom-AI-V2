from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIEvent(Base):
    __tablename__ = "ai_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    schedule_id = Column(Integer, ForeignKey("weekly_schedules.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(30), default="info", nullable=False)
    message = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="ai_events")
    class_group = relationship("ClassGroup")
    teacher = relationship("Teacher")
    subject = relationship("Subject")
    weekly_schedule = relationship("WeeklySchedule")
