from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Band(str, Enum):
    CONFIRMED = "CONFIRMED"
    REVIEW = "REVIEW"
    EMPTY = "EMPTY"


class TriageCategory(str, Enum):
    """Hierarchical triage classification from FrameGuard."""
    TIGER = "TIGER"
    OTHER_WILDLIFE = "OTHER_WILDLIFE"
    HUMAN = "HUMAN"
    NON_OBJECT = "NON_OBJECT"
    BLUR = "BLUR"


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"))
    filename: Mapped[str]
    file_path: Mapped[str]
    captured_at: Mapped[Optional[datetime]]
    is_night: Mapped[bool] = mapped_column(default=False)
    blur_score: Mapped[Optional[float]]
    band: Mapped[Optional[Band]]
    triage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    flank: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "LEFT" or "RIGHT"
    width: Mapped[Optional[int]]
    height: Mapped[Optional[int]]

    camera: Mapped["Camera"] = relationship(back_populates="images")
    predictions: Mapped[List["Prediction"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    species_tags: Mapped[List["SpeciesTag"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id"))
    layer: Mapped[str]
    label: Mapped[str]
    confidence: Mapped[float]
    processed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    model_version: Mapped[str] = mapped_column(default="v1.0")
    reviewed_decision: Mapped[Optional[str]]
    reviewed_notes: Mapped[Optional[str]]

    image: Mapped["Image"] = relationship(back_populates="predictions")


class SpeciesTag(Base):
    __tablename__ = "species_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id"))
    species: Mapped[str]
    confidence: Mapped[float]
    count_estimate: Mapped[int] = mapped_column(default=1)
    bbox_json: Mapped[Optional[str]]

    image: Mapped["Image"] = relationship(back_populates="species_tags")
