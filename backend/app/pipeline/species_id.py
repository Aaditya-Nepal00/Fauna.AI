import logging
import random
from dataclasses import dataclass
from pathlib import Path

DEMO_SPECIES = [
    "Bengal Tiger",
    "Snow Leopard",
    "One-horned Rhinoceros",
    "Asian Elephant",
    "Red Panda",
    "Clouded Leopard",
    "Himalayan Black Bear",
    "Sloth Bear",
    "Gaur",
    "Sambar Deer",
    "Indian Leopard",
    "Nilgai",
]


@dataclass
class SpeciesIDResult:
    species: str
    confidence: float
    count_estimate: int
    top3: list
    model_mode: str  # "DEMO" or "REAL"


class SpeciesID:
    """
    Layer 2: Species classification using EfficientNet-B4.
    Falls back to DEMO mode (deterministic random) when weights are absent.
    Model is loaded once at init; predict() is called per-image.
    """

    def __init__(self, weights_path: str):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.model_mode = "DEMO"

        if Path(weights_path).exists():
            try:
                import torch
                self.model = torch.load(weights_path, map_location="cpu")
                self.model.eval()
                self.model_mode = "REAL"
                self.logger.info(f"SpeciesID loaded: {weights_path}")
            except Exception as exc:
                self.logger.warning(f"SpeciesID weights unusable ({exc}) — DEMO mode")
        else:
            self.logger.info(f"SpeciesID weights not found at {weights_path} — DEMO mode")

    def predict(self, image_path: str) -> SpeciesIDResult:
        if self.model_mode == "REAL":
            return self._real_predict(image_path)
        return self._demo_predict(image_path)

    def _demo_predict(self, image_path: str) -> SpeciesIDResult:
        # Seed from filename so same image always returns same species
        seed = sum(ord(c) for c in Path(image_path).name)
        rng = random.Random(seed)
        picked = rng.sample(DEMO_SPECIES, min(3, len(DEMO_SPECIES)))
        confs = sorted(
            [rng.uniform(0.55, 0.97), rng.uniform(0.05, 0.28), rng.uniform(0.01, 0.12)],
            reverse=True,
        )
        top3 = [{"species": s, "confidence": round(c, 3)} for s, c in zip(picked, confs)]
        return SpeciesIDResult(
            species=top3[0]["species"],
            confidence=top3[0]["confidence"],
            count_estimate=rng.randint(1, 4),
            top3=top3,
            model_mode="DEMO",
        )

    def _real_predict(self, image_path: str) -> SpeciesIDResult:
        raise NotImplementedError("Real EfficientNet-B4 inference not yet implemented")
