from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any
import asyncio

from app.integrations.postgres.database import get_db
from app.core.config import settings

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
    is_ready = dependencies["database"] == "Healthy" and dependencies["redis"] == "Healthy"
    
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
        "redis": "Unknown",
        "celery": "Unknown"
    }
    
    # 1. Check Database
    try:
        await db.execute(text("SELECT 1"))
        health["database"] = "Healthy"
    except Exception as e:
        health["database"] = f"Unhealthy: {str(e)}"
        
    # 2. Check Redis
    try:
        from app.domain.reliability.engines.caching import get_redis
        redis_client = get_redis()
        ping_res = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        health["redis"] = "Healthy" if ping_res else "Degraded"
    except Exception as e:
        health["redis"] = f"Unhealthy: {str(e)}"
        
    # 3. Check Celery (bounded timeout to prevent hanging)
    try:
        from app.celery_app import celery_app
        # Run synchronous celery inspect in threadpool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        def _check_celery():
            i = celery_app.control.inspect(timeout=1.0)
            return i.ping()
            
        ping_res = await loop.run_in_executor(None, _check_celery)
        if ping_res is None:
            health["celery"] = "Unhealthy: No workers responding"
        else:
            health["celery"] = "Healthy"
    except Exception as e:
        health["celery"] = f"Unhealthy: {str(e)}"
        
    return health
