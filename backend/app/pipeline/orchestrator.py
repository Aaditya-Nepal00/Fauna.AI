import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional
from uuid import uuid4

import cv2

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import AnomalyAlert
from app.models.camera import Camera
from app.models.image import Band, Image, Prediction, SpeciesTag, TriageCategory
from app.pipeline.frame_guard import FrameGuard, FrameGuardResult
from app.pipeline.pulse_scan import PulseScan
from app.pipeline.species_id import SpeciesID, SpeciesIDResult

# Map triage → legacy Band for backward compatibility with existing queries.
_TRIAGE_TO_BAND = {
    TriageCategory.TIGER:         Band.CONFIRMED,
    TriageCategory.OTHER_WILDLIFE: Band.CONFIRMED,
    TriageCategory.HUMAN:         Band.CONFIRMED,
    TriageCategory.NON_OBJECT:    Band.EMPTY,
    TriageCategory.BLUR:          Band.EMPTY,
}


@dataclass
class ProcessingResult:
    """Result of processing a single image through all pipeline layers."""
    image_id: str
    filename: str
    triage: str                        # "TIGER" | "OTHER_WILDLIFE" | "HUMAN" | "NON_OBJECT" | "BLUR"
    flank: Optional[str]               # "LEFT" or "RIGHT"
    flank_confidence: Optional[float]
    species_hint: Optional[str]        # ImageNet top-1 label from FrameGuard
    has_person: bool
    fg_confidence: float
    species: Optional[str]             # From SpeciesID (OTHER_WILDLIFE only)
    species_confidence: Optional[float]
    count_estimate: Optional[int]
    top3: Optional[list]
    is_night: bool
    blur_score: float
    processing_ms: int
    model_mode: str                    # "DEMO" or "REAL" (from SpeciesID, "N/A" otherwise)


class PipelineOrchestrator:
    """
    Coordinates all three pipeline layers for a batch of images.
    Single instance shared across requests — models loaded once at startup.

    Flow per image:
      1. FrameGuard  → hierarchical triage (TIGER / OTHER_WILDLIFE / HUMAN / NON_OBJECT / BLUR)
      2. SpeciesID   → species classification (only for OTHER_WILDLIFE)
      3. Persist     → Image + Prediction + SpeciesTag records to DB

    After full batch:
      4. PulseScan   → temporal anomaly detection across all cameras
      5. Persist     → AnomalyAlert records to DB
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.frame_guard = FrameGuard()
        self.species_id = SpeciesID(
            weights_path=str(Path(settings.MODEL_DIR) / "species_id.pt")
        )
        self.pulse_scan = PulseScan()
        self.logger.info("PipelineOrchestrator ready — all three layers loaded")

    def _extract_exif_datetime(self, image_path: str) -> Optional[datetime]:
        """Extract capture timestamp from EXIF data if available."""
        try:
            from PIL import Image as PILImage
            from PIL.ExifTags import TAGS
            img = PILImage.open(image_path)
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    if TAGS.get(tag_id) == "DateTimeOriginal":
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass
        return None

    async def _persist_image_result(
        self,
        db: AsyncSession,
        camera_id: str,
        fg_result: FrameGuardResult,
        sid_result: Optional[SpeciesIDResult],
        captured_at: Optional[datetime],
    ) -> str:
        """
        Write Image + Prediction + optional SpeciesTag records to DB.
        Returns the new image UUID.

        SpeciesTag is created for:
          TIGER         — species="Bengal Tiger", confidence from fg_result
          HUMAN         — species="Human", confidence from fg_result
          OTHER_WILDLIFE — species + confidence from SpeciesID result
        """
        image_id = str(uuid4())
        filename = Path(fg_result.image_path).name

        image = Image(
            id=image_id,
            camera_id=camera_id,
            filename=filename,
            file_path=fg_result.image_path,
            captured_at=captured_at or datetime.utcnow(),
            is_night=fg_result.is_night,
            blur_score=round(fg_result.blur_score, 2),
            band=_TRIAGE_TO_BAND.get(fg_result.triage, Band.EMPTY),
            triage=fg_result.triage.value,
            flank=fg_result.flank,
            width=fg_result.width,
            height=fg_result.height,
        )
        db.add(image)

        fg_pred = Prediction(
            image_id=image_id,
            layer="FRAME_GUARD",
            label=fg_result.triage.value,
            confidence=fg_result.fg_confidence,
            model_version="yolo26n-imagenet",
        )
        db.add(fg_pred)

        if fg_result.triage == TriageCategory.TIGER:
            db.add(SpeciesTag(
                image_id=image_id,
                species="Tiger",
                confidence=fg_result.fg_confidence,
                count_estimate=1,
                bbox_json=None,
            ))

        elif fg_result.triage == TriageCategory.HUMAN:
            db.add(SpeciesTag(
                image_id=image_id,
                species="Human",
                confidence=fg_result.fg_confidence,
                count_estimate=1,
                bbox_json=None,
            ))

        elif sid_result is not None:
            # OTHER_WILDLIFE — use ImageNet species_hint if confidence is sufficient,
            # otherwise fall back to sid_result (suppressing DEMO invented names)
            imagenet_label = None
            if (fg_result.species_hint and fg_result.species_confidence is not None
                    and fg_result.species_confidence >= 0.30):
                # Take the substring before the first comma, then Title Case it
                # e.g. "sloth bear" -> "Sloth Bear"; "tiger, Panthera tigris" -> "Tiger"
                raw_hint = fg_result.species_hint.split(",")[0].strip()
                imagenet_label = raw_hint.title()

            display_species = (
                imagenet_label
                if imagenet_label
                else (
                    "Wildlife (unidentified)" if sid_result.model_mode == "DEMO"
                    else sid_result.species
                )
            )
            db.add(Prediction(
                image_id=image_id,
                layer="SPECIES_ID",
                label=display_species,
                confidence=sid_result.confidence,
                model_version=f"efficientnet-b4-{sid_result.model_mode.lower()}",
            ))
            db.add(SpeciesTag(
                image_id=image_id,
                species=display_species,
                confidence=sid_result.confidence,
                count_estimate=sid_result.count_estimate,
                bbox_json=None,
            ))

        await db.commit()
        return image_id

    async def process_image(
        self,
        image_path: str,
        camera_id: str,
        db: AsyncSession,
    ) -> ProcessingResult:
        """Process a single image through all layers and persist results."""
        start = time.monotonic()

        fg_result = await asyncio.get_event_loop().run_in_executor(
            None, self.frame_guard.process, image_path
        )

        # SpeciesID only runs for OTHER_WILDLIFE — tiger and human are resolved by FrameGuard
        sid_result: Optional[SpeciesIDResult] = None
        if fg_result.triage == TriageCategory.OTHER_WILDLIFE:
            sid_result = await asyncio.get_event_loop().run_in_executor(
                None, self.species_id.predict, image_path
            )

        captured_at = self._extract_exif_datetime(image_path)
        image_id = await self._persist_image_result(
            db, camera_id, fg_result, sid_result, captured_at
        )

        if fg_result.triage == TriageCategory.TIGER and fg_result.crop_image is not None:
            crops_dir = Path(settings.DATA_RAW_DIR).parent / "crops"
            crops_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(crops_dir / f"{image_id}.jpg"), fg_result.crop_image)

        return ProcessingResult(
            image_id=image_id,
            filename=Path(image_path).name,
            triage=fg_result.triage.value,
            flank=fg_result.flank,
            flank_confidence=fg_result.flank_confidence,
            species_hint=fg_result.species_hint,
            has_person=fg_result.has_person,
            fg_confidence=fg_result.fg_confidence,
            species=(
                # Mirror the imagenet_label logic from _persist_image_result
                (
                    fg_result.species_hint.split(",")[0].strip().title()
                    if (sid_result and fg_result.species_hint
                        and fg_result.species_confidence is not None
                        and fg_result.species_confidence >= 0.30)
                    else (
                        "Wildlife (unidentified)" if (sid_result and sid_result.model_mode == "DEMO")
                        else (sid_result.species if sid_result else None)
                    )
                )
            ),
            species_confidence=sid_result.confidence if sid_result else None,
            count_estimate=sid_result.count_estimate if sid_result else None,
            top3=sid_result.top3 if sid_result else None,
            is_night=fg_result.is_night,
            blur_score=round(fg_result.blur_score, 2),
            processing_ms=int((time.monotonic() - start) * 1000),
            model_mode=sid_result.model_mode if sid_result else "N/A",
        )

    async def process_batch(
        self,
        image_paths: list[str],
        camera_id: str,
        survey_id: str,
        db: AsyncSession,
    ) -> AsyncGenerator[dict, None]:
        """
        Process all images sequentially, yielding a progress SSE event after each.
        After all images, runs PulseScan and yields a final analysis_complete event.

        Yields dicts formatted for SSE streaming:
          {"event": "image_processed", "data": {...}}
          {"event": "analysis_complete", "data": {...}}
        """
        total = len(image_paths)
        tiger = wildlife = human = non_object = blur = 0

        for idx, path in enumerate(image_paths):
            try:
                result = await self.process_image(path, camera_id, db)

                if result.triage == "TIGER":
                    tiger += 1
                elif result.triage == "OTHER_WILDLIFE":
                    wildlife += 1
                elif result.triage == "HUMAN":
                    human += 1
                elif result.triage == "NON_OBJECT":
                    non_object += 1
                elif result.triage == "BLUR":
                    blur += 1

                yield {
                    "event": "image_processed",
                    "data": {
                        "index": idx + 1,
                        "total": total,
                        "percent": round((idx + 1) / total * 100, 1),
                        "image_id": result.image_id,
                        "filename": result.filename,
                        "triage": result.triage,
                        "fg_confidence": result.fg_confidence,
                        "species": result.species,
                        "species_confidence": result.species_confidence,
                        "species_hint": result.species_hint,
                        "flank": result.flank,
                        "flank_confidence": result.flank_confidence,
                        "has_person": result.has_person,
                        "count_estimate": result.count_estimate,
                        "is_night": result.is_night,
                        "model_mode": result.model_mode,
                    },
                }
            except Exception as exc:
                self.logger.error(f"Failed to process {path}: {exc}")
                yield {
                    "event": "image_error",
                    "data": {"filename": Path(path).name, "error": str(exc)},
                }

        alerts = await self._run_pulse_scan(db, survey_id)
        yield {
            "event": "analysis_complete",
            "data": {
                "total_processed": total,
                "tiger": tiger,
                "wildlife": wildlife,
                "human": human,
                "non_object": non_object,
                "blur": blur,
                "alerts_generated": len(alerts),
                "high_alerts": sum(1 for a in alerts if a.severity.value == "HIGH"),
            },
        }

    async def _run_pulse_scan(self, db: AsyncSession, survey_id: str) -> list:
        """Query DB detections for this survey and run PulseScan analysis."""
        stmt = (
            select(
                SpeciesTag.species,
                SpeciesTag.count_estimate,
                Image.captured_at,
                Camera.id.label("camera_id"),
                Camera.label.label("camera_label"),
            )
            .join(Image, SpeciesTag.image_id == Image.id)
            .join(Camera, Image.camera_id == Camera.id)
            .where(Camera.survey_id == survey_id)
        )
        rows = (await db.execute(stmt)).all()

        if not rows:
            return []

        df = pd.DataFrame(
            rows,
            columns=["species", "count_estimate", "captured_at", "camera_id", "camera_label"],
        )
        camera_labels = {r.camera_id: r.camera_label for r in rows}

        windows = self.pulse_scan.group_into_windows(df)
        camera_species_pairs = df[["camera_id", "species"]].drop_duplicates()
        baselines = {
            (row.camera_id, row.species): self.pulse_scan.build_baseline(
                windows, row.camera_id, row.species
            )
            for _, row in camera_species_pairs.iterrows()
        }

        alerts = self.pulse_scan.detect_anomalies(windows, baselines, camera_labels, survey_id)

        for alert in alerts:
            db_alert = AnomalyAlert(
                camera_id=alert.camera_id,
                survey_id=alert.survey_id,
                species=alert.species,
                alert_type=alert.anomaly_type,
                severity=alert.severity,
                last_confirmed_sighting=alert.last_confirmed_sighting,
                baseline_avg_visits=alert.baseline_avg_visits,
                current_visits=alert.current_visits,
                z_score=alert.z_score,
                recommended_action=alert.recommended_action,
            )
            db.add(db_alert)
        await db.commit()
        return alerts
