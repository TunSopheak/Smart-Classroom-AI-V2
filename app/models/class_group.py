from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ClassGroup(Base):
    __tablename__ = "class_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    academic_year = Column(String(20), nullable=True)
    semester = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    enrollments = relationship("Enrollment", back_populates="class_group")
    weekly_schedules = relationship("WeeklySchedule", back_populates="class_group")
