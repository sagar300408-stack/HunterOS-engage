from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/system", tags=["System Information"])

@router.get("/info")
async def system_info():
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }

@router.get("/version")
async def system_version():
    return {
        "version": settings.VERSION
    }
