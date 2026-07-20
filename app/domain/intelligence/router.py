from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID

from app.domain.intelligence.schemas import (
    IntelligenceSummaryResponse,
    OperationalHealthSnapshotResponse,
    LeakageEventResponse,
    RootCauseAnalysisResponse,
    PredictionEventResponse,
    ExecutiveInsightResponse
)
from app.domain.intelligence.repository import IntelligenceRepository
from app.domain.intelligence.engines.pipeline import OperationalIntelligencePipeline
from app.integrations.postgres.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/summary/{workspace_id}", response_model=IntelligenceSummaryResponse)
async def get_intelligence_summary(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the full executive operational intelligence summary.
    Includes the 4 KPIs, leakages, root causes, predictions, and executive insights.
    """
    repo = IntelligenceRepository(db)
    
    health = await repo.get_latest_health_snapshot(workspace_id)
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No intelligence snapshot found for this workspace."
        )

    insights = await repo.get_recent_insights(workspace_id)
    leakages = await repo.get_active_leakages(workspace_id)
    predictions = await repo.get_recent_predictions(workspace_id)
    
    # Just grab all root causes for now
    from sqlalchemy import select
    from app.domain.intelligence.models import RootCauseAnalysis
    root_causes_result = await db.execute(
        select(RootCauseAnalysis)
        .where(RootCauseAnalysis.workspace_id == workspace_id)
        .order_by(RootCauseAnalysis.analyzed_at.desc())
        .limit(10)
    )
    root_causes = root_causes_result.scalars().all()

    return IntelligenceSummaryResponse(
        health=health,
        insights=insights,
        top_leakages=leakages,
        top_predictions=predictions,
        top_root_causes=root_causes
    )


@router.post("/analyze/{workspace_id}", response_model=OperationalHealthSnapshotResponse)
async def trigger_analysis(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually forces the Operational Intelligence pipeline to run immediately (bypassing debounce)
    and returns the updated health snapshot.
    """
    pipeline = OperationalIntelligencePipeline(db)
    # Bypass debounce by resetting the debounce record if needed, but for manual trigger 
    # we can just run it directly. However, our pipeline checks debounce. 
    # Let's just bypass it here by removing the check or passing a flag.
    # We will just run it directly for now since it's an admin endpoint.
    
    # Actually, pipeline.run checks debounce natively. Let's reset the debounce.
    from sqlalchemy import update, delete
    from app.domain.intelligence.models import ObservationDebounce
    await db.execute(delete(ObservationDebounce).where(ObservationDebounce.workspace_id == workspace_id))
    await db.commit()

    health = await pipeline.run(workspace_id)
    await db.commit()
    
    return health
