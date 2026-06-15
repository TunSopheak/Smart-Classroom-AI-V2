from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Time, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class WeeklySchedule(Base):
    __tablename__ = "weekly_schedules"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_group_id = Column(Integer, ForeignKey("class_groups.id"), nullable=False)
    day_of_week = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room = Column(String(100), nullable=False)
    status = Column(String(30), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    teacher = relationship("Teacher", back_populates="weekly_schedules")
    subject = relationship("Subject", back_populates="weekly_schedules")
    class_group = relationship("ClassGroup", back_populates="weekly_schedules")
    sessions = relationship("Session", back_populates="weekly_schedule")
