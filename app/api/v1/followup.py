"""
Follow-up Intelligence API endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth_deps import get_current_user
from app.domain.security.models import User, DEFAULT_WORKSPACE_ID
from app.domain.followup import service, analytics, health_engine, sales_memory
from app.domain.followup.schemas import (
    FollowUpQueuePage,
    FollowUpQueueDetail,
    FollowUpOverviewStats,
    LeadHealthSummary,
    SalesTimelineEntry,
    UpdateMessageRequest,
    RescheduleRequest,
    AssignRequest,
    CancelRequest,
)
from app.integrations.postgres.database import get_db

router = APIRouter(prefix="/followups", tags=["Follow-ups"])


@router.get("/overview", response_model=FollowUpOverviewStats)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get operational overview stats for the follow-up dashboard."""
    return await analytics.get_overview(db, user.workspace_id)


@router.get("/queue", response_model=FollowUpQueuePage)
async def get_queue(
    status: Optional[str] = Query(None, description="Filter by status (e.g., scheduled, sent)"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get paginated follow-up queue."""
    return await service.get_queue_page(db, user.workspace_id, status, priority, page, page_size)


@router.get("/queue/{followup_id}", response_model=FollowUpQueueDetail)
async def get_followup_detail(
    followup_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full details of a specific follow-up, including execution history."""
    detail = await service.get_detail(db, followup_id, user.workspace_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return detail


@router.post("/queue/{followup_id}/pause", status_code=status.HTTP_204_NO_CONTENT)
async def pause_followup(
    followup_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pause a scheduled follow-up."""
    await service.pause(db, followup_id, user.workspace_id)


@router.post("/queue/{followup_id}/resume", status_code=status.HTTP_204_NO_CONTENT)
async def resume_followup(
    followup_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resume a paused follow-up."""
    await service.resume(db, followup_id, user.workspace_id)


@router.post("/queue/{followup_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_followup(
    followup_id: UUID,
    req: CancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cancel a follow-up."""
    try:
        await service.cancel(db, followup_id, req.reason, user.workspace_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/queue/{followup_id}/send-now", status_code=status.HTTP_204_NO_CONTENT)
async def send_followup_now(
    followup_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute a follow-up immediately."""
    await service.send_now(db, followup_id, user.workspace_id)


@router.put("/queue/{followup_id}/message", status_code=status.HTTP_204_NO_CONTENT)
async def update_followup_message(
    followup_id: UUID,
    req: UpdateMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update the message content of a scheduled follow-up."""
    await service.update_message(db, followup_id, req.message, user.workspace_id)


@router.put("/queue/{followup_id}/reschedule", status_code=status.HTTP_204_NO_CONTENT)
async def reschedule_followup(
    followup_id: UUID,
    req: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Change the scheduled time of a follow-up."""
    await service.reschedule(db, followup_id, req.scheduled_for, user.workspace_id)


@router.put("/queue/{followup_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
async def assign_followup(
    followup_id: UUID,
    req: AssignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Assign a follow-up to a specific user."""
    await service.assign(db, followup_id, req.user_id, user.workspace_id)


# ── Customer-centric endpoints ────────────────────────────────────────────────

@router.get("/customer/{customer_id}/health", response_model=LeadHealthSummary)
async def get_customer_health(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the current health score for a lead."""
    from app.domain.followup.models import LeadHealthScore
    from sqlalchemy import select
    
    health = await db.scalar(
        select(LeadHealthScore)
        .where(LeadHealthScore.customer_id == customer_id, LeadHealthScore.workspace_id == user.workspace_id)
    )
    if not health:
        # Calculate on demand if missing
        health = await health_engine.upsert_health_score(db, customer_id, user.workspace_id)
        
    return LeadHealthSummary.model_validate(health)


@router.get("/customer/{customer_id}/timeline", response_model=list[SalesTimelineEntry])
async def get_customer_timeline(
    customer_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the sales memory timeline for a lead."""
    entries = await sales_memory.get_timeline(db, customer_id, limit)
    return [SalesTimelineEntry.model_validate(e) for e in entries]
