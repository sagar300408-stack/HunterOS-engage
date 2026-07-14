from uuid import UUID
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.followup.models import SalesMemoryTimeline

async def record_customer_replied(session: AsyncSession, customer_id: UUID, workspace_id: UUID):
    entry = SalesMemoryTimeline(
        workspace_id=workspace_id,
        customer_id=customer_id,
        event_type="customer_replied",
        title="Customer Replied",
        description="The customer responded to a message."
    )
    session.add(entry)

async def record_follow_up_sent(session: AsyncSession, customer_id: UUID, reason: str, strategy: str, workspace_id: UUID):
    entry = SalesMemoryTimeline(
        workspace_id=workspace_id,
        customer_id=customer_id,
        event_type="followup_sent",
        title="Follow-up Sent",
        description=f"Sent a follow-up: {strategy}. Reason: {reason}"
    )
    session.add(entry)

async def get_timeline(session: AsyncSession, customer_id: UUID, limit: int = 50) -> List[SalesMemoryTimeline]:
    q = select(SalesMemoryTimeline).where(
        SalesMemoryTimeline.customer_id == customer_id
    ).order_by(SalesMemoryTimeline.created_at.desc()).limit(limit)
    res = await session.execute(q)
    return list(res.scalars().all())
