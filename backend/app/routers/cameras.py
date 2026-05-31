from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraResponse

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("/{survey_id}", response_model=List[CameraResponse])
async def list_cameras(survey_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Camera).where(Camera.survey_id == survey_id)
    cameras = (await db.execute(stmt)).scalars().all()
    return [CameraResponse.model_validate(c) for c in cameras]


@router.post("/", response_model=CameraResponse, status_code=201)
async def create_camera(body: CameraCreate, db: AsyncSession = Depends(get_db)):
    camera = Camera(**body.model_dump())
    db.add(camera)
    await db.commit()
    await db.refresh(camera)
    return CameraResponse.model_validate(camera)
