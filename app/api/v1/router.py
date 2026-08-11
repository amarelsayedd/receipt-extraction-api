from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.extractions import router as extractions_router
from app.api.v1.health import router as health_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(extractions_router)
