from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SurveyStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str]
    location_name: Mapped[str]
    lat: Mapped[Optional[float]]
    lng: Mapped[Optional[float]]
    start_date: Mapped[Optional[datetime]]
    end_date: Mapped[Optional[datetime]]
    status: Mapped[SurveyStatus] = mapped_column(default=SurveyStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    cameras: Mapped[List["Camera"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )
