import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.camera import Camera
from app.models.image import Image, Prediction, SpeciesTag
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.image import ImageResponse, ReviewSubmit

logger = logging.getLogger(__name__)

# No prefix — these routes span /api/surveys/... and /api/images/...
router = APIRouter(tags=["images"])


def get_orchestrator(request: Request) -> PipelineOrchestrator:
    return request.app.state.orchestrator


@router.post("/api/surveys/{survey_id}/upload")
async def upload_images(
    survey_id: str,
    camera_id: str = Form(...),
    files: List[UploadFile] = File(...),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
):
    raw_dir = Path(settings.DATA_RAW_DIR) / survey_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[str] = []
    for file in files:
        dest = raw_dir / file.filename
        content = await file.read()
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)
        saved_paths.append(str(dest))

    async def generate_sse():
        async with AsyncSessionLocal() as db:
            async for event in orchestrator.process_batch(
                saved_paths, camera_id, survey_id, db
            ):
                data = json.dumps(event["data"])
                yield f"event: {event['event']}\ndata: {data}\n\n"

    return StreamingResponse(generate_sse(), media_type="text/event-stream")


@router.get("/api/surveys/{survey_id}/results", response_model=List[ImageResponse])
async def list_results(
    survey_id: str,
    triage: Optional[str] = None,
    flank: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    # Query images + camera — one row per image, no SpeciesTag join to avoid row multiplication
    images_stmt = (
        select(Image, Camera.label.label("camera_label"))
        .join(Camera, Image.camera_id == Camera.id)
        .where(Camera.survey_id == survey_id)
    )
    if triage:
        images_stmt = images_stmt.where(Image.triage == triage)
    if flank:
        images_stmt = images_stmt.where(Image.flank == flank)

    rows = (await db.execute(images_stmt)).all()
    if not rows:
        return []

    image_ids = [r[0].id for r in rows]

    # Fetch best (highest confidence) SpeciesTag per image in a separate query
    tags_stmt = select(SpeciesTag).where(SpeciesTag.image_id.in_(image_ids))
    best_tags: Dict[str, SpeciesTag] = {}
    for tag in (await db.execute(tags_stmt)).scalars().all():
        if tag.image_id not in best_tags or tag.confidence > best_tags[tag.image_id].confidence:
            best_tags[tag.image_id] = tag

    # Fetch FRAME_GUARD prediction confidence per image
    preds_stmt = select(Prediction).where(
        Prediction.image_id.in_(image_ids),
        Prediction.layer == "FRAME_GUARD",
    )
    fg_preds: Dict[str, float] = {}
    for pred in (await db.execute(preds_stmt)).scalars().all():
        fg_preds[pred.image_id] = pred.confidence

    return [
        ImageResponse(
            id=img.id,
            filename=img.filename,
            triage=img.triage,
            flank=img.flank,
            flank_confidence=None,
            species=best_tags[img.id].species if img.id in best_tags else None,
            species_confidence=best_tags[img.id].confidence if img.id in best_tags else None,
            fg_confidence=fg_preds.get(img.id),
            captured_at=img.captured_at,
            is_night=img.is_night,
            blur_score=img.blur_score,
            width=img.width,
            height=img.height,
            camera_label=camera_label or "",
            image_url=f"/api/images/{img.id}/file",
        )
        for img, camera_label in rows
    ]


@router.get("/api/surveys/{survey_id}/summary")
async def get_survey_summary(survey_id: str, db: AsyncSession = Depends(get_db)):
    # Count images by triage — single pass, no joins that multiply rows
    triage_stmt = (
        select(Image.triage, func.count(Image.id))
        .join(Camera, Image.camera_id == Camera.id)
        .where(Camera.survey_id == survey_id)
        .group_by(Image.triage)
    )
    triage_counts = {"TIGER": 0, "OTHER_WILDLIFE": 0, "HUMAN": 0, "NON_OBJECT": 0, "BLUR": 0}
    total = 0
    for triage_val, count in (await db.execute(triage_stmt)).all():
        if triage_val in triage_counts:
            triage_counts[triage_val] = count
        total += count

    # Count flanks for tiger images only
    flank_stmt = (
        select(Image.flank, func.count(Image.id))
        .join(Camera, Image.camera_id == Camera.id)
        .where(Camera.survey_id == survey_id, Image.triage == "TIGER")
        .group_by(Image.flank)
    )
    flank_counts = {"LEFT": 0, "RIGHT": 0, "UNCERTAIN": 0}
    for flank_val, count in (await db.execute(flank_stmt)).all():
        if flank_val in flank_counts:
            flank_counts[flank_val] = count

    return {"total": total, "triage": triage_counts, "flank": flank_counts}


@router.get("/api/images/{image_id}/file")
async def get_image_file(image_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Image).where(Image.id == image_id)
    image = (await db.execute(stmt)).scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = Path(image.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    return FileResponse(str(file_path))


@router.post("/api/images/{image_id}/review", response_model=ImageResponse)
async def review_image(
    image_id: str,
    body: ReviewSubmit,
    db: AsyncSession = Depends(get_db),
):
    pred_stmt = select(Prediction).where(
        Prediction.image_id == image_id,
        Prediction.layer == "SPECIES_ID",
    )
    pred = (await db.execute(pred_stmt)).scalar_one_or_none()
    if not pred:
        raise HTTPException(
            status_code=404,
            detail="No SPECIES_ID prediction found for this image",
        )

    pred.reviewed_decision = body.decision
    pred.reviewed_notes = body.notes
    await db.commit()

    img_stmt = (
        select(Image, Camera.label.label("camera_label"))
        .join(Camera, Image.camera_id == Camera.id)
        .where(Image.id == image_id)
    )
    row = (await db.execute(img_stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    img, camera_label = row
    tag_stmt = (
        select(SpeciesTag)
        .where(SpeciesTag.image_id == image_id)
        .order_by(SpeciesTag.confidence.desc())
    )
    tag = (await db.execute(tag_stmt)).scalars().first()

    fg_stmt = select(Prediction).where(
        Prediction.image_id == image_id,
        Prediction.layer == "FRAME_GUARD",
    )
    fg_pred = (await db.execute(fg_stmt)).scalar_one_or_none()

    return ImageResponse(
        id=img.id,
        filename=img.filename,
        triage=img.triage,
        flank=img.flank,
        flank_confidence=None,
        species=tag.species if tag else None,
        species_confidence=tag.confidence if tag else None,
        fg_confidence=fg_pred.confidence if fg_pred else None,
        captured_at=img.captured_at,
        is_night=img.is_night,
        blur_score=img.blur_score,
        width=img.width,
        height=img.height,
        camera_label=camera_label or "",
        image_url=f"/api/images/{image_id}/file",
    )
