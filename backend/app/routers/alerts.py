from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import AnomalyAlert, Severity
from app.schemas.alert import AlertResponse

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/{survey_id}", response_model=List[AlertResponse])
async def list_alerts(survey_id: str, db: AsyncSession = Depends(get_db)):
    severity_order = case(
        (AnomalyAlert.severity == Severity.HIGH, 0),
        (AnomalyAlert.severity == Severity.MEDIUM, 1),
        else_=2,
    )
    stmt = (
        select(AnomalyAlert)
        .where(AnomalyAlert.survey_id == survey_id)
        .order_by(severity_order, AnomalyAlert.detected_at.desc())
    )
    alerts = (await db.execute(stmt)).scalars().all()
    return [AlertResponse.model_validate(a) for a in alerts]


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AnomalyAlert).where(AnomalyAlert.id == alert_id)
    alert = (await db.execute(stmt)).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)
