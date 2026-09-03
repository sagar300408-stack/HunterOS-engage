from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone
from app.domain.followup.models import FollowUpQueue, FollowUpExecution
from app.domain.followup.schemas import FollowUpOverviewStats

async def get_overview(session: AsyncSession, workspace_id: UUID) -> FollowUpOverviewStats:
    now = datetime.now(tz=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    pending = await session.scalar(
        select(func.count(FollowUpQueue.id)).where(
            FollowUpQueue.workspace_id == workspace_id,
            FollowUpQueue.status.in_(["scheduled", "executing"])
        )
    ) or 0
    
    due_today = await session.scalar(
        select(func.count(FollowUpQueue.id)).where(
            FollowUpQueue.workspace_id == workspace_id,
            FollowUpQueue.status.in_(["scheduled", "executing"]),
            FollowUpQueue.scheduled_for >= today_start
        )
    ) or 0
    
    sent_today = await session.scalar(
        select(func.count(FollowUpQueue.id)).where(
            FollowUpQueue.workspace_id == workspace_id,
            FollowUpQueue.status == "sent",
            FollowUpQueue.executed_at >= today_start
        )
    ) or 0
    
    failed_today = await session.scalar(
        select(func.count(FollowUpExecution.id)).where(
            FollowUpExecution.workspace_id == workspace_id,
            FollowUpExecution.outcome == "failed",
            FollowUpExecution.created_at >= today_start
        )
    ) or 0
    
    paused = await session.scalar(
        select(func.count(FollowUpQueue.id)).where(
            FollowUpQueue.workspace_id == workspace_id,
            FollowUpQueue.human_paused == True
        )
    ) or 0
    
    strategies_res = await session.execute(
        select(FollowUpQueue.strategy, func.count(FollowUpQueue.id)).where(
            FollowUpQueue.workspace_id == workspace_id,
            FollowUpQueue.strategy.isnot(None)
        ).group_by(FollowUpQueue.strategy)
    )
    strategy_dist = {str(row[0]): int(row[1]) for row in strategies_res.all()}
    
    return FollowUpOverviewStats(
        pending_followups=pending,
        due_today=due_today,
        sent_today=sent_today,
        failed_today=failed_today,
        paused_needs_review=paused,
        strategy_distribution=strategy_dist
    )
