from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.health.engine import OperationalHealthEngine
from app.domain.health.repository import HealthRepository
from app.domain.health.schemas import HealthSnapshotResponse

router = APIRouter(prefix="/health", tags=["operational_health"])


@router.post("/workspace/{workspace_id}/refresh", response_model=List[HealthSnapshotResponse])
async def rebuild_health(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Manually triggers a full rebuild of the Operational Health evaluations for a workspace.
    Note: Health is normally updated automatically whenever KPIs are refreshed.
    """
    engine = OperationalHealthEngine(db)
    # Defaulting target to the workspace itself
    snapshots = await engine.refresh_health(workspace_id, target_type="workspace", target_id=workspace_id)
    return snapshots


@router.get("/workspace/{workspace_id}/latest", response_model=List[HealthSnapshotResponse])
async def get_latest_health(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the latest Operational Health snapshot for every registered health domain.
    """
    repo = HealthRepository(db)
    snapshots = await repo.get_latest_snapshots(target_type="workspace", target_id=workspace_id)
    return snapshots


@router.get("/workspace/{workspace_id}/trends/{health_name}", response_model=List[HealthSnapshotResponse])
async def get_health_trends(workspace_id: UUID, health_name: str, limit: int = 30, db: AsyncSession = Depends(get_db)):
    """
    Retrieves historical snapshots for a specific health domain to build trend visualizations.
    """
    repo = HealthRepository(db)
    snapshots = await repo.get_health_trends(target_type="workspace", target_id=workspace_id, health_name=health_name, limit=limit)
    return snapshots
