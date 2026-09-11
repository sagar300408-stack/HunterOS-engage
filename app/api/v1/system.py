from fastapi import APIRouter, Depends
from app.core.config import settings
from app.api.v1.security import verify_internal_network

router = APIRouter(prefix="/system", tags=["System Information"], dependencies=[Depends(verify_internal_network)])

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
        "version": getattr(settings, "VERSION", "1.0.0"),
        "status": "stable"
    }

@router.get("/changelog")
async def system_changelog():
    """
    Returns the latest release notes and changelog from docs/release-notes.
    In a real system, this would read from docs/release-notes/changelog.md.
    """
    return {
        "version": "1.0.0",
        "changes": [
            "Introduced Enterprise Integration Platform",
            "Added Webhook parsing",
            "Included CLI Tooling"
        ]
    }
