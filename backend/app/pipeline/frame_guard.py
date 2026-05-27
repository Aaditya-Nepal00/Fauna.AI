import logging
import sys
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import settings
from app.models.image import Band

# COCO class IDs that represent animals
ANIMAL_CLASS_IDS = {
    14, 15, 16, 17, 18, 19, 20, 21, 22, 23,  # bird → giraffe
    0,  # person — counted as detection, excluded from band scoring
}
WILDLIFE_CLASS_IDS = {14, 15, 16, 17, 18, 19, 20, 21, 22, 23}


@dataclass
class FrameGuardResult:
    image_path: str
    band: Band
    fg_confidence: float      # highest wildlife detection confidence (0.0 if none)
    is_night: bool
    blur_score: float         # Laplacian variance — higher = sharper
    is_blurry: bool           # blur_score < 100
    width: int
    height: int
    processing_ms: int
    detections_count: int     # total animal bounding boxes found


class FrameGuard:
    """
    Layer 1: Empty-frame elimination using YOLOv8n + CLAHE infrared preprocessing.
    Separates camera trap images into three confidence bands before species classification.
    Model is loaded once at init; process() is called per-image.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        model_file = model_path or "yolov8n.pt"
        # ultralytics YOLO auto-downloads yolov8n.pt if not found locally
        self.model = YOLO(model_file)
        self.model.fuse()  # fuse conv+bn layers for faster inference
        self.logger.info(f"FrameGuard loaded: {model_file}")

    def _is_night_image(self, img_gray: np.ndarray) -> bool:
        """Images with mean pixel intensity below 85 are treated as IR night captures."""
        return float(np.mean(img_gray)) < 85.0

    def _compute_blur_score(self, img_gray: np.ndarray) -> float:
        """Laplacian variance. Sharp images score high (>200). Blurry score low (<100)."""
        return float(cv2.Laplacian(img_gray, cv2.CV_64F).var())

    def _apply_clahe(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Contrast Limited Adaptive Histogram Equalization for IR night images.
        Dramatically improves YOLOv8 detection on low-contrast night frames.
        """
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        return cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2BGR)

    def _assign_band(self, confidence: float) -> Band:
        """
        Three-band confidence triage using thresholds from settings:
        > CONFIRMED threshold  → CONFIRMED (passes to SpeciesID automatically)
        > REVIEW_LOW threshold → REVIEW (queued for biologist verification)
        below both             → EMPTY (auto-archived, never deleted)
        """
        if confidence > settings.CONFIDENCE_FRAMEGUARD_CONFIRMED:
            return Band.CONFIRMED
        elif confidence > settings.CONFIDENCE_FRAMEGUARD_REVIEW_LOW:
            return Band.REVIEW
        return Band.EMPTY

    def process(self, image_path: str) -> FrameGuardResult:
        """
        Full single-image pipeline:
        load → night check → CLAHE if night → YOLOv8 → filter animal classes → band assignment
        """
        start = time.monotonic()

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Could not read image: {image_path}")

        h, w = img_bgr.shape[:2]
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        is_night = self._is_night_image(img_gray)
        blur_score = self._compute_blur_score(img_gray)

        img_for_inference = self._apply_clahe(img_bgr) if is_night else img_bgr

        # verbose=False suppresses per-image console spam
        results = self.model(img_for_inference, verbose=False)[0]

        wildlife_confs = []
        total_animal_detections = 0
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id in ANIMAL_CLASS_IDS:
                total_animal_detections += 1
            if cls_id in WILDLIFE_CLASS_IDS:
                wildlife_confs.append(conf)

        max_confidence = round(max(wildlife_confs, default=0.0), 2)
        band = self._assign_band(max_confidence)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        return FrameGuardResult(
            image_path=image_path,
            band=band,
            fg_confidence=max_confidence,
            is_night=is_night,
            blur_score=blur_score,
            is_blurry=blur_score < 100.0,
            width=w,
            height=h,
            processing_ms=elapsed_ms,
            detections_count=total_animal_detections,
        )

    def process_batch(self, image_paths: list[str]) -> list[FrameGuardResult]:
        """Process a list of images and return results. Logs band distribution summary."""
        results = []
        for path in image_paths:
            try:
                results.append(self.process(path))
            except Exception as e:
                self.logger.error(f"FrameGuard failed on {path}: {e}")

        confirmed = sum(1 for r in results if r.band == Band.CONFIRMED)
        review = sum(1 for r in results if r.band == Band.REVIEW)
        empty = sum(1 for r in results if r.band == Band.EMPTY)
        self.logger.info(
            f"Batch complete: {len(results)} images | "
            f"CONFIRMED={confirmed} REVIEW={review} EMPTY={empty}"
        )
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m app.pipeline.frame_guard <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    fg = FrameGuard()
    result = fg.process(image_path)

    print("\n── FrameGuard Result ──────────────────────────")
    print(f"  Image        : {result.image_path}")
    print(f"  Band         : {result.band.value}")
    print(f"  Confidence   : {result.fg_confidence:.2f}")
    print(f"  Detections   : {result.detections_count}")
    print(f"  Night image  : {result.is_night}")
    print(f"  Blur score   : {result.blur_score:.1f}  (blurry={result.is_blurry})")
    print(f"  Dimensions   : {result.width}×{result.height}")
    print(f"  Processing   : {result.processing_ms} ms")
    print("───────────────────────────────────────────────\n")
