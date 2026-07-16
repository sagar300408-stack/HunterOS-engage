from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.briefing.repository import BriefingRepository
from app.domain.briefing.engine import ExecutiveBriefingEngine
from app.domain.briefing.schemas import BriefingSnapshotResponse

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.post("/workspace/{workspace_id}/generate", response_model=BriefingSnapshotResponse)
async def generate_briefing(workspace_id: UUID, template_name: str, period: str = "on_demand", db: AsyncSession = Depends(get_db)):
    """
    On-demand generation of an Executive Briefing.
    """
    engine = ExecutiveBriefingEngine(db)
    try:
        snapshot = await engine.generate_briefing(workspace_id, template_name, period)
        return snapshot
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workspace/{workspace_id}/template/{template_name}/latest", response_model=BriefingSnapshotResponse)
async def get_latest_briefing(workspace_id: UUID, template_name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the most recent briefing for a specific template.
    """
    repo = BriefingRepository(db)
    snapshot = await repo.get_latest_briefing(workspace_id, template_name)
    if not snapshot:
        raise HTTPException(status_code=404, detail="No briefing found for this template")
    return snapshot


@router.get("/workspace/{workspace_id}/template/{template_name}/history", response_model=List[BriefingSnapshotResponse])
async def get_briefing_history(workspace_id: UUID, template_name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the historical briefings for a specific template.
    """
    repo = BriefingRepository(db)
    snapshots = await repo.get_briefing_history(workspace_id, template_name)
    return snapshots


@router.get("/workspace/{workspace_id}/period/{period}", response_model=List[BriefingSnapshotResponse])
async def get_briefings_by_period(workspace_id: UUID, period: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves all briefings for a specific period (daily, weekly, monthly).
    """
    repo = BriefingRepository(db)
    snapshots = await repo.get_briefings_by_period(workspace_id, period)
    return snapshots
