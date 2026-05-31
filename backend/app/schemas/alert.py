from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.alert import AnomalyType, Severity


class AlertResponse(BaseModel):
    id: str
    camera_id: str
    survey_id: str
    species: str
    alert_type: AnomalyType
    severity: Severity
    detected_at: datetime
    resolved: bool
    resolved_at: Optional[datetime]
    last_confirmed_sighting: Optional[datetime]
    baseline_avg_visits: Optional[float]
    current_visits: Optional[float]
    z_score: Optional[float]
    recommended_action: str

    model_config = {"from_attributes": True}


class AlertResolve(BaseModel):
    notes: str
