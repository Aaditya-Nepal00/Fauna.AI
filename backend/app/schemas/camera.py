from typing import Optional

from pydantic import BaseModel


class CameraCreate(BaseModel):
    survey_id: str
    label: str
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    habitat_type: Optional[str] = None
    elevation_m: Optional[float] = None


class CameraResponse(BaseModel):
    id: str
    survey_id: str
    label: str
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    habitat_type: Optional[str]
    elevation_m: Optional[float]

    model_config = {"from_attributes": True}
