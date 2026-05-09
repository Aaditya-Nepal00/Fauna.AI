from fastapi import FastAPI
from app.layers.frame_guard import FrameGuard
from app.layers.species_id import SpeciesID
from app.layers.pulse_scan import PulseScan

app = FastAPI(title="Fauna.AI API")

@app.get("/")
def read_root():
    return {"message": "Fauna.AI Wildlife Monitoring System API Active"}

@app.post("/process")
def process_image(image_path: str):
    # Pipeline execution logic
    return {"status": "success"}
