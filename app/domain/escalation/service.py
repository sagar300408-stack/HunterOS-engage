from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.escalation.models import HumanEscalation, EscalationStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def create_escalation(
    session: AsyncSession,
    workspace_id: UUID,
    customer_id: UUID,
    conversation_id: Optional[UUID],
    intent_history_id: Optional[UUID],
    trigger_intent: str,
    trigger_next_action: str,
    context_snapshot: Optional[dict] = None,
) -> HumanEscalation:
    # Check for existing pending escalation to ensure idempotency
    stmt = select(HumanEscalation).where(
        HumanEscalation.workspace_id == workspace_id,
        HumanEscalation.customer_id == customer_id,
        HumanEscalation.status == EscalationStatus.pending,
    )
    result = await session.execute(stmt)
    existing = result.scalars().first()

    if existing:
        logger.info(
            "escalation_already_pending",
            customer_id=str(customer_id),
            escalation_id=str(existing.id),
        )
        return existing

    escalation = HumanEscalation(
        workspace_id=workspace_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        intent_history_id=intent_history_id,
        trigger_intent=trigger_intent,
        trigger_next_action=trigger_next_action,
        context_snapshot=context_snapshot,
    )
    session.add(escalation)
    await session.flush()

    logger.info(
        "escalation_created",
        customer_id=str(customer_id),
        escalation_id=str(escalation.id),
        trigger_intent=trigger_intent,
    )
    return escalation


async def get_pending_escalations(
    session: AsyncSession,
    workspace_id: UUID,
) -> List[HumanEscalation]:
    stmt = select(HumanEscalation).where(
        HumanEscalation.workspace_id == workspace_id,
        HumanEscalation.status == EscalationStatus.pending,
    ).order_by(HumanEscalation.created_at.asc())
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def resolve_escalation(
    session: AsyncSession,
    escalation_id: UUID,
    workspace_id: UUID,
    resolved_by: Optional[str] = None,
    resolution_note: Optional[str] = None,
) -> Optional[HumanEscalation]:
    stmt = select(HumanEscalation).where(
        HumanEscalation.id == escalation_id,
        HumanEscalation.workspace_id == workspace_id,
    )
    result = await session.execute(stmt)
    escalation = result.scalars().first()

    if not escalation:
        return None

    escalation.status = EscalationStatus.resolved
    escalation.resolved_at = datetime.now(timezone.utc)
    escalation.resolved_by = resolved_by
    escalation.resolution_note = resolution_note

    await session.flush()

    logger.info(
        "escalation_resolved",
        escalation_id=str(escalation.id),
        resolved_by=resolved_by,
    )
    return escalation
