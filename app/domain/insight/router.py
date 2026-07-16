from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.domain.insight.repository import InsightRepository
from app.domain.insight.schemas import InsightSnapshotResponse
from app.domain.insight.models import InsightSnapshot

router = APIRouter(prefix="/insight", tags=["insight"])


@router.get("/workspace/{workspace_id}/latest", response_model=List[InsightSnapshotResponse])
async def get_latest_insights(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the latest active insights for the workspace.
    """
    repo = InsightRepository(db)
    snapshots = await repo.get_latest_insights(target_type="workspace", target_id=workspace_id)
    return snapshots


@router.get("/workspace/{workspace_id}/category/{category}", response_model=List[InsightSnapshotResponse])
async def get_insights_by_category(workspace_id: UUID, category: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves active insights filtered by category.
    """
    stmt = select(InsightSnapshot).where(
        InsightSnapshot.target_type == "workspace",
        InsightSnapshot.target_id == workspace_id,
        InsightSnapshot.category == category,
        InsightSnapshot.lifecycle_status == "active"
    ).order_by(InsightSnapshot.generated_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/workspace/{workspace_id}/history", response_model=List[InsightSnapshotResponse])
async def get_historical_insights(workspace_id: UUID, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Retrieves historical insights including those that have been resolved or superseded.
    """
    stmt = select(InsightSnapshot).where(
        InsightSnapshot.target_type == "workspace",
        InsightSnapshot.target_id == workspace_id
    ).order_by(InsightSnapshot.generated_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())
