# Configuration for Fauna.AI Wildlife Monitoring
# Optimized for Nepal-specific field conditions

# IR (Infrared) Lighting Settings
# Nepal's dense canopy in Chitwan/Bardia often requires specific IR calibration
IR_CONFIG = {
    "low_light_threshold": 45,  # Pixel intensity threshold to trigger IR mode
    "gamma_correction": 1.2,    # Adjustment for deep forest shadows
    "noise_reduction_level": 2  # Gaussian blur intensity for grainy night shots
}

# Model Confidence Thresholds
DETECTION_THRESHOLDS = {
    "frame_guard": 0.35,       # Lower threshold to avoid missing camouflaged animals
    "species_id": 0.85,        # Higher threshold for critical species classification
    "pulse_scan_anomaly": 2.5  # Standard deviations for behavioral anomaly detection
}

# Target Species List (Nepal Specific)
TARGET_SPECIES = [
    "Bengal Tiger",
    "Greater One-horned Rhino",
    "Snow Leopard",
    "Red Panda",
    "Clouded Leopard",
    "Asian Elephant",
    "Gaur"
]

# Path Configurations
PATHS = {
    "raw_data": "./data/raw",
    "processed_data": "./data/processed",
    "review_queue": "./data/review_queue",
    "model_dir": "./models"
}
