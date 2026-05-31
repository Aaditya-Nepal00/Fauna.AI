import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import torch
import torchvision
import torchvision.transforms as T
from PIL import Image as PILImage
from ultralytics import YOLO

from app.models.image import TriageCategory

# COCO class IDs
PERSON_CLASS_ID = 0
ANIMAL_CLASS_IDS = {14, 15, 16, 17, 18, 19, 20, 21, 22, 23}  # bird → giraffe

# ImageNet class 292 = 'tiger, Panthera tigris'
TIGER_IMAGENET_IDS = {292}

PERSON_CONFIDENCE = 0.25
ANIMAL_CONFIDENCE = 0.20

FLANK_CLASSES = ["LEFT", "RIGHT"]


@dataclass
class FrameGuardResult:
    """Complete triage result for a single camera trap image."""
    image_path: str
    triage: TriageCategory
    fg_confidence: float
    flank: Optional[str]               # "LEFT", "RIGHT", or "UNCERTAIN" when triage is TIGER
    flank_confidence: Optional[float]  # confidence of flank classification
    species_hint: Optional[str]        # ImageNet top-1 label for the detected animal
    species_confidence: Optional[float]  # ImageNet top-1 confidence for the detected animal
    is_night: bool
    blur_score: float
    crop_blur_score: Optional[float]    # Laplacian variance of the animal crop (CASE A only)
    blown_fraction: Optional[float]     # fraction of pixels > 250 (overexposure/flare gate)
    is_blurry: bool
    width: int
    height: int
    processing_ms: int
    detections_count: int
    has_person: bool


class FrameGuard:
    """
    Layer 1: Hierarchical camera trap image triage.

    Classification hierarchy:
      Level 2 — Object detection via MegaDetectorV6 (default) or YOLO26n fallback
      Level 3 — Tiger identification via ImageNet classifier (EfficientNet-B0)
      Level 3b — Tiger flank classification (LEFT / RIGHT)

    MegaDetectorV6 is purpose-built for camera trap imagery with high recall for
    animals in cluttered, night, and daylight scenes.  YOLO26n remains available
    as a fallback via DETECTOR_BACKEND="yolo" in config.

    ImageNet class 292 ('tiger, Panthera tigris') provides reliable zero-shot
    tiger detection without any custom training data.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        from app.config import settings

        # Detector backend — MegaDetectorV6 (default) or YOLO26 fallback
        if settings.DETECTOR_BACKEND == "megadetector":
            from PytorchWildlife.models import detection as pw_detection
            self.detector = pw_detection.MegaDetectorV6(
                device="cpu", pretrained=True, version=settings.MEGADETECTOR_VERSION
            )
            self.backend = "megadetector"
        else:
            yolo_file = model_path or "yolo26n.pt"
            self.detector = YOLO(yolo_file)
            self.detector.fuse()
            self.backend = "yolo"

        # EfficientNet-B0 for ImageNet classification (tiger detection)
        self.classifier = torchvision.models.efficientnet_b0(
            weights=torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1
        )
        self.classifier.eval()
        self.imagenet_categories = (
            torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1.meta["categories"]
        )
        self.classify_transform = T.Compose([
            T.Resize(256),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.logger.info(f"FrameGuard ready: backend={self.backend}, Classifier=EfficientNet-B0-ImageNet")

        # Flank classifier — trained EfficientNet-B0 (2 classes: LEFT, RIGHT)
        self.flank_model = None
        self.flank_mode = "DEMO"
        self._load_flank_classifier()

    def _load_flank_classifier(self):
        """
        Load the trained flank classifier if weights exist.
        Falls back to demo mode if the file is missing or fails to load.
        """
        from app.config import settings
        flank_path = settings.FLANK_WEIGHTS_PATH

        if not os.path.exists(flank_path):
            self.logger.warning(
                f"Flank weights not found at {flank_path} — flank runs in DEMO mode"
            )
            return

        try:
            model = torchvision.models.efficientnet_b0(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier[1] = torch.nn.Linear(in_features, 2)
            state = torch.load(flank_path, map_location="cpu")
            model.load_state_dict(state)
            model.eval()
            self.flank_model = model
            self.flank_mode = "REAL"
            self.logger.info(f"Flank classifier loaded (REAL mode): {flank_path}")
        except Exception as exc:
            self.logger.error(f"Failed to load flank classifier: {exc} — using DEMO mode")

    # ── Night detection ──────────────────────────────────────────────────────

    def _is_night_image(self, img_gray: np.ndarray) -> bool:
        """IR night images have mean pixel intensity below 85."""
        return float(np.mean(img_gray)) < 85.0

    # ── Blur detection ───────────────────────────────────────────────────────

    def _compute_blur_score(self, img_gray: np.ndarray) -> float:
        """Laplacian variance: sharp images >200, blurry <100."""
        return round(float(cv2.Laplacian(img_gray, cv2.CV_64F).var()), 2)

    def _compute_crop_blur(self, crop_bgr: np.ndarray) -> float:
        """Laplacian variance of an animal crop. Returns 9999.0 for empty crops."""
        if crop_bgr is None or crop_bgr.size == 0:
            return 9999.0
        gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        return round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2)

    def _compute_blown_fraction(self, img_gray: np.ndarray) -> float:
        """Fraction of pixels blown out (grayscale > 250). Range 0.0–1.0."""
        blown = int((img_gray > 250).sum())
        return round(blown / img_gray.size, 4)

    # ── CLAHE for IR enhancement ─────────────────────────────────────────────

    def _apply_clahe(self, img_bgr: np.ndarray) -> np.ndarray:
        """Contrast Limited Adaptive Histogram Equalization for night IR images."""
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)
        return enhanced

    # ── Crop detection region ────────────────────────────────────────────────

    def _crop_detection(self, img_bgr: np.ndarray, bbox: tuple) -> np.ndarray:
        """Crop (x1,y1,x2,y2) bounding box with 10% padding."""
        x1, y1, x2, y2 = bbox
        h, w = img_bgr.shape[:2]
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.1)
        x1, y1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
        x2, y2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
        return img_bgr[y1:y2, x1:x2]

    # ── ImageNet classification ──────────────────────────────────────────────

    def _classify_crop(self, crop_bgr: np.ndarray) -> tuple[int, str, float]:
        """
        Run ImageNet classifier on a cropped detection.
        Returns (class_index, class_name, confidence).
        """
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(crop_rgb)
        tensor = self.classify_transform(pil_img).unsqueeze(0)

        with torch.no_grad():
            probs = torch.softmax(self.classifier(tensor), dim=1)[0]

        top_conf, top_idx = torch.max(probs, dim=0)
        idx = top_idx.item()
        return idx, self.imagenet_categories[idx], round(float(top_conf.item()), 2)

    # ── Tiger check ──────────────────────────────────────────────────────────

    def _is_tiger(self, class_idx: int) -> bool:
        """True if ImageNet class is tiger (class 292)."""
        return class_idx in TIGER_IMAGENET_IDS

    # ── Flank classification (real mode) ─────────────────────────────────────

    def _classify_flank_real(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        """
        Real flank classification using the trained EfficientNet-B0 model.
        Returns (flank, confidence) where flank is "LEFT" or "RIGHT".
        """
        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(crop_rgb)

        flank_transform = T.Compose([
            T.Resize((256, 256)),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
        tensor = flank_transform(pil_img).unsqueeze(0)

        with torch.no_grad():
            probs = torch.softmax(self.flank_model(tensor), dim=1)[0]

        conf, idx = torch.max(probs, dim=0)
        return FLANK_CLASSES[idx.item()], round(float(conf.item()), 2)

    # ── Flank classification (demo mode) ─────────────────────────────────────

    def _classify_flank_demo(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        """
        Deterministic demo-mode flank classification.
        Same crop always returns same flank. Uses pixel hash for consistency.
        Will be replaced by trained flank classifier when labeled data is available.
        """
        pixel_hash = int(np.sum(crop_bgr[::5, ::5]).item())
        rng = np.random.default_rng(seed=pixel_hash)
        flank = "LEFT" if pixel_hash % 2 == 0 else "RIGHT"
        confidence = round(float(rng.uniform(0.72, 0.91)), 2)
        return flank, confidence

    # ── Build result helper ──────────────────────────────────────────────────

    def _result(self, **kwargs) -> FrameGuardResult:
        """Construct FrameGuardResult with defaults for optional fields."""
        defaults = dict(
            flank=None, flank_confidence=None, species_hint=None, species_confidence=None,
            crop_blur_score=None, blown_fraction=None,
            has_person=False, detections_count=0,
        )
        defaults.update(kwargs)
        return FrameGuardResult(**defaults)

    # ── Unified detection ────────────────────────────────────────────────────

    def _detect(self, img_bgr: np.ndarray) -> tuple[list, list]:
        """
        Run the configured detector on a BGR image (may be CLAHE-enhanced).
        Returns (person_detections, animal_detections) where each detection is
        {"bbox": (x1, y1, x2, y2), "conf": float}.

        MegaDetector class IDs: 0=animal, 1=person, 2=vehicle (vehicle ignored).
        YOLO COCO class IDs: 0=person, 14-23=animals.
        """
        person_dets: list = []
        animal_dets: list = []

        if self.backend == "megadetector":
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            res = self.detector.single_image_detection(img_rgb)
            dets = res["detections"]
            for i in range(len(dets.xyxy)):
                x1, y1, x2, y2 = map(int, dets.xyxy[i].tolist())
                conf = float(dets.confidence[i])
                cls_id = int(dets.class_id[i])
                if cls_id == 1 and conf > PERSON_CONFIDENCE:
                    person_dets.append({"bbox": (x1, y1, x2, y2), "conf": conf})
                elif cls_id == 0 and conf > ANIMAL_CONFIDENCE:
                    animal_dets.append({"bbox": (x1, y1, x2, y2), "conf": conf})
        else:
            raw = self.detector(img_bgr, verbose=False)[0]
            for box in raw.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if cls_id == PERSON_CLASS_ID and conf > PERSON_CONFIDENCE:
                    person_dets.append({"bbox": (x1, y1, x2, y2), "conf": conf})
                elif cls_id in ANIMAL_CLASS_IDS and conf > ANIMAL_CONFIDENCE:
                    animal_dets.append({"bbox": (x1, y1, x2, y2), "conf": conf})

        return person_dets, animal_dets

    # ── Main processing pipeline ─────────────────────────────────────────────

    def process(self, image_path: str) -> FrameGuardResult:
        """
        Full hierarchical triage for one camera trap image.

        Pipeline:
          1. Load image → compute whole_image_blur_score, night status, blown_fraction
          1b. Overexposure gate: if blown_fraction exceeds threshold → BLUR (skip detection)
          2. Apply CLAHE if night, then run detector (MegaDetector or YOLO)
          3. Separate detections: person (conf>0.25) and animal (conf>0.20)
          CASE A — animal detected:
            - Compute blur on the animal CROP (not whole image)
            - threshold = CROP_BLUR_NIGHT (5.0) if night else CROP_BLUR_DAY (18.0)
            - If crop_blur < threshold → BLUR (genuine motion blur)
            - Else → ImageNet classify → TIGER or OTHER_WILDLIFE
          CASE B — only person detected → HUMAN
          CASE C — nothing detected:
            - empty_threshold = EMPTY_BLUR_NIGHT (12.0) if night else EMPTY_BLUR_DAY (40.0)
            - If whole_image_blur_score < empty_threshold → BLUR
            - Else → NON_OBJECT
        """
        from app.config import settings as _s
        start = time.monotonic()

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Could not read image: {image_path}")

        h, w = img_bgr.shape[:2]
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        is_night = self._is_night_image(img_gray)
        whole_image_blur_score = self._compute_blur_score(img_gray)
        blown_fraction = self._compute_blown_fraction(img_gray)

        shared = dict(
            image_path=image_path, is_night=is_night,
            blur_score=whole_image_blur_score, blown_fraction=blown_fraction,
            width=w, height=h,
        )

        # ── Overexposure / flare gate (runs before detection) ────────────────
        if (blown_fraction > _s.OVEREXPOSURE_SEVERE
                or (is_night and blown_fraction > _s.FLARE_NIGHT_FRACTION)):
            return self._result(
                **shared,
                triage=TriageCategory.BLUR,
                fg_confidence=0.0,
                is_blurry=True,
                processing_ms=int((time.monotonic() - start) * 1000),
            )

        # ── Object detection (FIRST — before any blur decision) ──────────────
        img_input = self._apply_clahe(img_bgr) if is_night else img_bgr
        person_dets, animal_dets = self._detect(img_input)

        has_person = len(person_dets) > 0
        total_detections = len(person_dets) + len(animal_dets)

        # ── CASE A: Animal detected ───────────────────────────────────────────
        if animal_dets:
            best_det = max(animal_dets, key=lambda x: x["conf"])
            best_conf = best_det["conf"]
            crop = self._crop_detection(img_bgr, best_det["bbox"])

            # Night-aware crop blur check (IR crops have naturally low variance)
            crop_blur = self._compute_crop_blur(crop)
            crop_threshold = _s.CROP_BLUR_NIGHT if is_night else _s.CROP_BLUR_DAY
            if crop_blur < crop_threshold:
                return self._result(
                    **shared,
                    triage=TriageCategory.BLUR,
                    fg_confidence=round(best_conf, 2),
                    is_blurry=True,
                    crop_blur_score=crop_blur,
                    has_person=has_person,
                    detections_count=total_detections,
                    processing_ms=int((time.monotonic() - start) * 1000),
                )

            if crop.size == 0:
                return self._result(
                    **shared,
                    triage=TriageCategory.OTHER_WILDLIFE,
                    fg_confidence=round(best_conf, 2),
                    species_hint="unknown",
                    crop_blur_score=crop_blur,
                    is_blurry=False,
                    has_person=has_person,
                    detections_count=total_detections,
                    processing_ms=int((time.monotonic() - start) * 1000),
                )

            class_idx, class_name, species_conf = self._classify_crop(crop)

            if self._is_tiger(class_idx):
                # Flank classifier runs on the FULL IMAGE — matches training data
                # (training images were full 2048×1536 camera-trap frames, not crops)
                if self.flank_mode == "REAL" and self.flank_model is not None:
                    flank, flank_conf = self._classify_flank_real(img_bgr)
                else:
                    flank, flank_conf = self._classify_flank_demo(img_bgr)
                # Apply uncertainty gate: low confidence is better than a confident wrong label
                if flank_conf < _s.FLANK_UNCERTAIN_THRESHOLD:
                    flank = "UNCERTAIN"
                return self._result(
                    **shared,
                    triage=TriageCategory.TIGER,
                    fg_confidence=round(best_conf, 2),
                    flank=flank,
                    flank_confidence=flank_conf,
                    species_hint=class_name,
                    species_confidence=species_conf,
                    crop_blur_score=crop_blur,
                    is_blurry=False,
                    has_person=has_person,
                    detections_count=total_detections,
                    processing_ms=int((time.monotonic() - start) * 1000),
                )

            return self._result(
                **shared,
                triage=TriageCategory.OTHER_WILDLIFE,
                fg_confidence=round(best_conf, 2),
                species_hint=class_name,
                species_confidence=species_conf,
                crop_blur_score=crop_blur,
                is_blurry=False,
                has_person=has_person,
                detections_count=total_detections,
                processing_ms=int((time.monotonic() - start) * 1000),
            )

        # ── CASE B: Only person detected ─────────────────────────────────────
        if person_dets:
            best_conf = round(max(d["conf"] for d in person_dets), 2)
            return self._result(
                **shared,
                triage=TriageCategory.HUMAN,
                fg_confidence=best_conf,
                species_hint="person",
                is_blurry=False,
                has_person=True,
                detections_count=len(person_dets),
                processing_ms=int((time.monotonic() - start) * 1000),
            )

        # ── CASE C: Nothing detected — now apply whole-image blur check ───────
        # Use night-aware threshold: dark empty night frames have low Laplacian variance
        # just from being dark, not from blur — so the night threshold is much lower.
        empty_threshold = _s.EMPTY_BLUR_NIGHT if is_night else _s.EMPTY_BLUR_DAY
        if whole_image_blur_score < empty_threshold:
            return self._result(
                **shared,
                triage=TriageCategory.BLUR,
                fg_confidence=0.0,
                is_blurry=True,
                processing_ms=int((time.monotonic() - start) * 1000),
            )

        return self._result(
            **shared,
            triage=TriageCategory.NON_OBJECT,
            fg_confidence=0.0,
            is_blurry=False,
            processing_ms=int((time.monotonic() - start) * 1000),
        )

    # ── Batch processing ─────────────────────────────────────────────────────

    def process_batch(self, image_paths: list[str]) -> list[FrameGuardResult]:
        """Process multiple images and log triage distribution summary."""
        results = []
        for path in image_paths:
            try:
                results.append(self.process(path))
            except Exception as exc:
                self.logger.error(f"FrameGuard failed on {path}: {exc}")

        counts: dict[str, int] = {}
        for r in results:
            counts[r.triage.value] = counts.get(r.triage.value, 0) + 1

        self.logger.info(f"Batch complete: {len(results)} images | Triage: {counts}")
        return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python -m app.pipeline.frame_guard <image_path>")
        sys.exit(1)

    guard = FrameGuard()
    result = guard.process(sys.argv[1])

    symbols = {
        TriageCategory.TIGER:         "🐯 TIGER DETECTED",
        TriageCategory.OTHER_WILDLIFE: "🐾 OTHER WILDLIFE",
        TriageCategory.HUMAN:         "👤 HUMAN DETECTED",
        TriageCategory.NON_OBJECT:    "⚫ NON-OBJECT (false trigger)",
        TriageCategory.BLUR:          "🔴 BLUR (unusable)",
    }

    print(f"\n{'═' * 56}")
    print(f"  FAUNA.AI FRAMEGUARD TRIAGE")
    print(f"{'═' * 56}")
    print(f"  {symbols[result.triage]}")
    print(f"{'─' * 56}")
    print(f"  Image        : {result.image_path}")
    print(f"  Confidence   : {result.fg_confidence}")
    if result.species_hint:
        print(f"  ImageNet     : {result.species_hint}")
    if result.flank:
        print(f"  Flank        : {result.flank} ({result.flank_confidence})")
        print(f"  Flank mode   : {guard.flank_mode}")
    if result.has_person:
        print(f"  Person also  : Yes")
    print(f"  Detector     : {guard.backend}")
    print(f"  Night image  : {result.is_night}")
    print(f"  Blur score   : {result.blur_score} (blurry={result.is_blurry})")
    if result.crop_blur_score is not None:
        print(f"  Crop blur    : {result.crop_blur_score}")
    if result.blown_fraction is not None:
        print(f"  Blown frac   : {result.blown_fraction}")
    print(f"  Dimensions   : {result.width}x{result.height}")
    print(f"  Detections   : {result.detections_count}")
    print(f"  Processing   : {result.processing_ms} ms")
    print(f"{'═' * 56}\n")
