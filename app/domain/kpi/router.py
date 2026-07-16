import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.kpi.engine import KpiIntelligenceEngine
from app.domain.kpi.repository import KpiRepository
from app.domain.kpi.schemas import KpiSnapshotResponse

router = APIRouter(prefix="/kpis", tags=["kpi_intelligence"])


@router.post("/workspace/{workspace_id}/refresh", response_model=List[KpiSnapshotResponse])
async def refresh_workspace_kpis(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
):
    """
    On-demand trigger to calculate the latest KPIs for a workspace.
    """
    engine = KpiIntelligenceEngine(session)
    # Right now target_type is workspace and target_id is the workspace itself
    snapshots = await engine.refresh_kpis(
        workspace_id=workspace_id,
        target_type="workspace",
        target_id=workspace_id
    )
    return snapshots


@router.get("/workspace/{workspace_id}/latest", response_model=List[KpiSnapshotResponse])
async def get_latest_workspace_kpis(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve the most recent calculation for every KPI in this workspace.
    """
    repo = KpiRepository(session)
    snapshots = await repo.get_latest_snapshots(
        target_type="workspace",
        target_id=workspace_id
    )
    return snapshots


@router.get("/workspace/{workspace_id}/trends/{kpi_name}", response_model=List[KpiSnapshotResponse])
async def get_kpi_trends(
    workspace_id: uuid.UUID,
    kpi_name: str,
    limit: int = 30,
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve the historical trend for a specific KPI.
    """
    repo = KpiRepository(session)
    snapshots = await repo.get_kpi_trends(
        target_type="workspace",
        target_id=workspace_id,
        kpi_name=kpi_name,
        limit=limit
    )
    return snapshots
