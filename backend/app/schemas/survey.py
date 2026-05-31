from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.survey import SurveyStatus


class SurveyCreate(BaseModel):
    name: str
    location_name: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class SurveyResponse(BaseModel):
    id: str
    name: str
    location_name: str
    lat: Optional[float]
    lng: Optional[float]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: SurveyStatus
    created_at: datetime
    camera_count: int = 0

    model_config = {"from_attributes": True}
