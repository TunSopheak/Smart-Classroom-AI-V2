from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(30), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    weekly_schedules = relationship("WeeklySchedule", back_populates="subject")
