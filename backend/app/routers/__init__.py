from app.routers.surveys import router as surveys_router
from app.routers.cameras import router as cameras_router
from app.routers.images import router as images_router
from app.routers.alerts import router as alerts_router

__all__ = ["surveys_router", "cameras_router", "images_router", "alerts_router"]
