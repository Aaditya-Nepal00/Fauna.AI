from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: str
    filename: str
    triage: Optional[str] = None
    flank: Optional[str] = None
    flank_confidence: Optional[float] = None
    species: Optional[str] = None
    species_confidence: Optional[float] = None
    fg_confidence: Optional[float] = None
    captured_at: Optional[datetime] = None
    is_night: bool = False
    blur_score: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    camera_label: str = ""
    image_url: str = ""

    model_config = {"from_attributes": True}


class ReviewSubmit(BaseModel):
    decision: str
    notes: str
