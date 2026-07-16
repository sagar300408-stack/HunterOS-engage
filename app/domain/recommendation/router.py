from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.domain.recommendation.repository import RecommendationRepository
from app.domain.recommendation.schemas import RecommendationSnapshotResponse
from app.domain.recommendation.models import RecommendationSnapshot

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("/workspace/{workspace_id}/latest", response_model=List[RecommendationSnapshotResponse])
async def get_latest_recommendations(workspace_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the latest active recommendations for the workspace.
    """
    repo = RecommendationRepository(db)
    snapshots = await repo.get_latest_recommendations(target_type="workspace", target_id=workspace_id)
    return snapshots


@router.get("/workspace/{workspace_id}/category/{category}", response_model=List[RecommendationSnapshotResponse])
async def get_recommendations_by_category(workspace_id: UUID, category: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves active recommendations filtered by category.
    """
    stmt = select(RecommendationSnapshot).where(
        RecommendationSnapshot.target_type == "workspace",
        RecommendationSnapshot.target_id == workspace_id,
        RecommendationSnapshot.category == category,
        RecommendationSnapshot.lifecycle_status == "active"
    ).order_by(
        RecommendationSnapshot.recommendation_score.desc(),
        RecommendationSnapshot.generated_at.desc()
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/workspace/{workspace_id}/priority/{priority}", response_model=List[RecommendationSnapshotResponse])
async def get_recommendations_by_priority(workspace_id: UUID, priority: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves active recommendations filtered by priority.
    """
    stmt = select(RecommendationSnapshot).where(
        RecommendationSnapshot.target_type == "workspace",
        RecommendationSnapshot.target_id == workspace_id,
        RecommendationSnapshot.priority == priority,
        RecommendationSnapshot.lifecycle_status == "active"
    ).order_by(
        RecommendationSnapshot.recommendation_score.desc(),
        RecommendationSnapshot.generated_at.desc()
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.put("/{recommendation_id}/status")
async def update_recommendation_status(recommendation_id: UUID, status: str, db: AsyncSession = Depends(get_db)):
    """
    Updates the lifecycle status of a recommendation (e.g. to 'acknowledged' or 'dismissed').
    """
    valid_statuses = ["active", "acknowledged", "dismissed", "completed", "expired", "superseded"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    repo = RecommendationRepository(db)
    await repo.update_status(recommendation_id, status)
    return {"status": "success"}
