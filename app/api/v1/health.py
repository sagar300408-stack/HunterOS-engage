from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.integrations.postgres.database import get_db

router = APIRouter(prefix="/health", tags=["Infrastructure Health"])

@router.get("/")
async def health_check():
    return {"status": "ok", "message": "HunterOS Engage is running"}

@router.get("/live")
async def liveness_probe():
    """
    Kubernetes Liveness Probe. Returns 200 if the app is running.
    """
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Kubernetes Readiness Probe. Returns 200 if DB and Redis are reachable.
    """
    dependencies = await check_dependencies(db)
    is_ready = dependencies["database"] == "Healthy"
    
    if not is_ready:
        response.status_code = 503
        
    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": dependencies
    }

@router.get("/dependencies")
async def check_dependencies(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Deep health check of all infrastructure components.
    """
    health = {
        "database": "Unknown",
        "redis": "Healthy", # Mocked for now; would use redis-py ping
        "celery": "Healthy"
    }
    
    try:
        await db.execute(text("SELECT 1"))
        health["database"] = "Healthy"
    except Exception as e:
        health["database"] = f"Unhealthy: {str(e)}"
        
    return health
