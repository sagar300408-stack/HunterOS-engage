from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.domain.followup.models import LeadHealthScore
from app.domain.conversations.models import Message, Conversation
from datetime import datetime, timezone

async def upsert_health_score(session: AsyncSession, customer_id: UUID, workspace_id: UUID) -> LeadHealthScore:
    """Recalculates and saves the lead health score."""
    
    # Simple heuristic calculation
    msg_count = await session.scalar(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.customer_id == customer_id, Message.direction == "incoming")
    ) or 0
    
    score = 50 + (msg_count * 5)
    score = min(score, 100)
    
    if score >= 80:
        band = "Excellent"
        reasons = ["Highly engaged", "Responds frequently"]
        positive = ["Active communication"]
        rec = "Push for a close"
    elif score >= 60:
        band = "Good"
        reasons = ["Regular engagement"]
        positive = ["Responds"]
        rec = "Continue nurturing"
    elif score >= 40:
        band = "Moderate"
        reasons = ["Occasional engagement"]
        positive = []
        rec = "Try a different strategy"
    else:
        band = "At Risk"
        reasons = ["Ghosting", "Low engagement"]
        positive = []
        rec = "Send re-engagement campaign"
        
    hs = await session.scalar(
        select(LeadHealthScore).where(LeadHealthScore.customer_id == customer_id)
    )
    if hs:
        hs.score = score
        hs.band = band
        hs.reasons = reasons
        hs.positive_signals = positive
        hs.recommendation = rec
    else:
        hs = LeadHealthScore(
            workspace_id=workspace_id,
            customer_id=customer_id,
            score=score,
            band=band,
            reasons=reasons,
            positive_signals=positive,
            recommendation=rec
        )
        session.add(hs)
        
    return hs
