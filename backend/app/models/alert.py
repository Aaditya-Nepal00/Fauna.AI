from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyType(str, Enum):
    SUDDEN_ABSENCE = "SUDDEN_ABSENCE"
    ACTIVITY_TIME_SHIFT = "ACTIVITY_TIME_SHIFT"
    GROUP_SIZE_COLLAPSE = "GROUP_SIZE_COLLAPSE"
    FREQUENCY_SPIKE = "FREQUENCY_SPIKE"
    NEW_SPECIES_APPEARANCE = "NEW_SPECIES_APPEARANCE"


class ActivityWindow(Base):
    __tablename__ = "activity_windows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"))
    survey_id: Mapped[str]
    window_start: Mapped[datetime]
    window_end: Mapped[datetime]
    species: Mapped[str]
    visit_count: Mapped[int]
    avg_group_size: Mapped[float]


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.id"))
    survey_id: Mapped[str]
    species: Mapped[str]
    alert_type: Mapped[AnomalyType]
    severity: Mapped[Severity]
    detected_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(default=False)
    resolved_at: Mapped[Optional[datetime]]
    last_confirmed_sighting: Mapped[Optional[datetime]]
    baseline_avg_visits: Mapped[Optional[float]]
    current_visits: Mapped[Optional[float]]
    z_score: Mapped[Optional[float]]
    recommended_action: Mapped[str]
