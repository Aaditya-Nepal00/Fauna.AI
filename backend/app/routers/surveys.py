from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.camera import Camera
from app.models.survey import Survey
from app.schemas.camera import CameraResponse
from app.schemas.survey import SurveyCreate, SurveyResponse

router = APIRouter(prefix="/api/surveys", tags=["surveys"])


def _to_survey_response(survey: Survey, camera_count: int) -> SurveyResponse:
    return SurveyResponse(
        id=survey.id,
        name=survey.name,
        location_name=survey.location_name,
        lat=survey.lat,
        lng=survey.lng,
        start_date=survey.start_date,
        end_date=survey.end_date,
        status=survey.status,
        created_at=survey.created_at,
        camera_count=camera_count,
    )


@router.get("/", response_model=List[SurveyResponse])
async def list_surveys(db: AsyncSession = Depends(get_db)):
    camera_count_subq = (
        select(func.count(Camera.id))
        .where(Camera.survey_id == Survey.id)
        .correlate(Survey)
        .scalar_subquery()
    )
    stmt = (
        select(Survey, camera_count_subq.label("camera_count"))
        .order_by(Survey.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [_to_survey_response(row[0], row[1]) for row in rows]


@router.post("/", response_model=SurveyResponse, status_code=201)
async def create_survey(body: SurveyCreate, db: AsyncSession = Depends(get_db)):
    survey = Survey(**body.model_dump())
    db.add(survey)
    await db.commit()
    await db.refresh(survey)
    return _to_survey_response(survey, 0)


@router.get("/{survey_id}")
async def get_survey(survey_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Survey)
        .where(Survey.id == survey_id)
        .options(selectinload(Survey.cameras))
    )
    survey = (await db.execute(stmt)).scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return {
        **_to_survey_response(survey, len(survey.cameras)).model_dump(),
        "cameras": [CameraResponse.model_validate(c).model_dump() for c in survey.cameras],
    }


@router.delete("/{survey_id}", status_code=204)
async def delete_survey(survey_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Survey).where(Survey.id == survey_id)
    survey = (await db.execute(stmt)).scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.delete(survey)
    await db.commit()
