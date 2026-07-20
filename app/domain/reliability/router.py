from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.integrations.postgres.database import get_db
from app.api.deps import get_current_user, RequirePermissions
from app.domain.reliability.models import PerformanceBenchmark, ReliabilityEvent, DeploymentRecord

router = APIRouter(tags=["Reliability & Performance"])

@router.get("/performance/benchmarks", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_benchmarks(db: AsyncSession = Depends(get_db)):
    """
    Returns the latest performance benchmark runs and SLO compliance.
    """
    stmt = select(PerformanceBenchmark).order_by(PerformanceBenchmark.timestamp.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/reliability/status", dependencies=[Depends(RequirePermissions("view_all"))])
async def reliability_status(db: AsyncSession = Depends(get_db)):
    """
    Returns current platform health, including active degradations or failovers.
    """
    stmt = select(ReliabilityEvent).where(ReliabilityEvent.resolved == False)
    result = await db.execute(stmt)
    active_events = result.scalars().all()
    
    return {
        "status": "degraded" if active_events else "healthy",
        "active_events": active_events
    }

@router.post("/reliability/failover", dependencies=[Depends(RequirePermissions("platform_admin"))])
async def trigger_manual_failover(service_name: str, db: AsyncSession = Depends(get_db)):
    """
    Manually triggers a failover for a specific service.
    """
    event = ReliabilityEvent(
        event_type="failover",
        service_name=service_name,
        description="Manual failover triggered by admin"
    )
    db.add(event)
    await db.commit()
    return {"status": "failover_initiated"}

@router.get("/deployments", dependencies=[Depends(RequirePermissions("view_all"))])
async def list_deployments(db: AsyncSession = Depends(get_db)):
    """
    Returns deployment history.
    """
    stmt = select(DeploymentRecord).order_by(DeploymentRecord.deployed_at.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()
