from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    survey_id: Mapped[str] = mapped_column(ForeignKey("surveys.id"))
    label: Mapped[str]
    gps_lat: Mapped[Optional[float]]
    gps_lng: Mapped[Optional[float]]
    habitat_type: Mapped[Optional[str]]
    elevation_m: Mapped[Optional[float]]

    survey: Mapped["Survey"] = relationship(back_populates="cameras")
    images: Mapped[List["Image"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan"
    )
