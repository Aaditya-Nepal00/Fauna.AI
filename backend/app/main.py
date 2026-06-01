import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.pipeline.orchestrator import PipelineOrchestrator
from app.routers import surveys_router, cameras_router, images_router, alerts_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fauna.AI",
    version="1.0.0",
    description="Wildlife camera trap intelligence for Nepal",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    for dir_path in [
        settings.DATA_RAW_DIR,
        settings.DATA_PROCESSED_DIR,
        settings.REVIEW_QUEUE_DIR,
        settings.MODEL_DIR,
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    app.state.orchestrator = PipelineOrchestrator()
    logger.info("All pipeline layers ready")


app.include_router(surveys_router)
app.include_router(cameras_router)
app.include_router(images_router)
app.include_router(alerts_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
