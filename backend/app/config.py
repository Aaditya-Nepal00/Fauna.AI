from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./fauna.db"
    MODEL_DIR: str = "./models/weights"
    DATA_RAW_DIR: str = "./data/raw"
    DATA_PROCESSED_DIR: str = "./data/processed"
    REVIEW_QUEUE_DIR: str = "./data/review_queue"

    FLANK_WEIGHTS_PATH: str = "./models/weights/flank_classifier.pt"

    DETECTOR_BACKEND: str = "megadetector"   # "megadetector" or "yolo"
    MEGADETECTOR_VERSION: str = "MDV6-yolov9-c"
    ANIMAL_CONFIDENCE: float = 0.20
    PERSON_CONFIDENCE: float = 0.25

    CROP_BLUR_DAY: float = 18.0     # daytime crops are high-contrast
    CROP_BLUR_NIGHT: float = 5.0    # night IR crops are inherently low-contrast
    EMPTY_BLUR_DAY: float = 40.0    # whole-frame blur threshold for daylight empty frames
    EMPTY_BLUR_NIGHT: float = 12.0  # whole-frame blur threshold for night empty frames (dark = low variance naturally)

    OVEREXPOSURE_SEVERE: float = 0.40   # >40% blown pixels → unusable any time of day
    FLARE_NIGHT_FRACTION: float = 0.05  # >5% blown pixels in a night frame → flash misfire

    FLANK_UNCERTAIN_THRESHOLD: float = 0.60  # below this confidence, flank is marked UNCERTAIN
    FLANK_CROP_INSET: float = 0.12          # fraction of bbox to inset on each edge for the saved flank crop

    CONFIDENCE_FRAMEGUARD_CONFIRMED: float = 0.35
    CONFIDENCE_FRAMEGUARD_REVIEW_LOW: float = 0.15
    CONFIDENCE_SPECIES: float = 0.70

    PULSE_WINDOW_HOURS: int = 2
    PULSE_BASELINE_DAYS: int = 30
    PULSE_ANOMALY_ZSCORE: float = 2.5

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
