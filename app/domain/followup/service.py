"""
Follow-up Core Service.

Orchestrates the entire Follow-up Intelligence pipeline:
  1. Trigger evaluation via Decision Engine
  2. If Yes, generate context via Context Builder
  3. Select strategy via Strategy Engine
  4. Generate message via Message Generator
  5. Validate via Quality Checker
  6. Queue for execution
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers.models import Customer
from app.domain.security.models import DEFAULT_WORKSPACE_ID
from app.domain.followup.models import FollowUpQueue
from app.domain.followup.schemas import (
    UpdateMessageRequest,
    RescheduleRequest,
    AssignRequest,
    CancelRequest,
    FollowUpQueueSummary,
    FollowUpQueueDetail,
    FollowUpQueuePage,
)
from app.domain.followup.state_machine import transition
from app.domain.followup import crm_sync
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def schedule_followup(
    session: AsyncSession,
    customer_id: UUID,
    conversation_id: Optional[UUID] = None,
    workspace_id: UUID = DEFAULT_WORKSPACE_ID,
) -> Optional[FollowUpQueue]:
    """
    Evaluate a customer for follow-up and schedule if necessary.
    Called by the event bus after incoming/outgoing messages.
    """
    from app.domain.followup.decision_engine import evaluate
    from app.domain.followup.policy_engine import get_workspace_policy
    from app.domain.followup.context_builder import build_context
    from app.domain.followup.strategy_engine import select_strategy
    from app.domain.followup.message_generator import generate_message
    from app.domain.followup.quality_checker import check
    from app.domain.intent.models import IntentHistory
    from app.domain.conversations.models import Message, Conversation
    from app.domain.scheduling.models import ScheduledEvent

    # 1. Gather basic stats for Decision Engine
    now = datetime.now(tz=timezone.utc)

    # (Simplified data gathering for the decision engine)
    last_in = await session.scalar(
        select(Message.timestamp).join(Conversation).where(
            Conversation.customer_id == customer_id, Message.direction == "incoming"
        ).order_by(Message.timestamp.desc()).limit(1)
    )
    last_out = await session.scalar(
        select(Message.timestamp).join(Conversation).where(
            Conversation.customer_id == customer_id, Message.direction == "outgoing"
        ).order_by(Message.timestamp.desc()).limit(1)
    )

    last_fu = await session.scalar(
        select(FollowUpQueue.executed_at).where(
            FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "sent"
        ).order_by(FollowUpQueue.executed_at.desc()).limit(1)
    )

    fu_count = await session.scalar(
        select(func.count(FollowUpQueue.id)).where(
            FollowUpQueue.customer_id == customer_id, FollowUpQueue.status.in_(["sent", "scheduled"])
        )
    ) or 0

    latest_intent = await session.scalar(
        select(IntentHistory).where(IntentHistory.customer_id == customer_id).order_by(IntentHistory.created_at.desc()).limit(1)
    )

    policy = get_workspace_policy(workspace_id)
    max_attempts = policy.effective_max_attempts(latest_intent.buying_stage if latest_intent else None)

    # 2. Evaluate
    decision = evaluate(
        customer_id=customer_id,
        conversation_id=conversation_id,
        last_outgoing_at=last_out,
        last_incoming_at=last_in,
        last_followup_sent_at=last_fu,
        followup_attempt_count=fu_count,
        buying_stage=latest_intent.buying_stage if latest_intent else None,
        urgency=latest_intent.urgency.value if latest_intent and latest_intent.urgency else None,
        has_open_proposal=False,  # Stubbed for now, integrate with CRM later
        has_confirmed_meeting=False,
        next_meeting_at=None,
        has_missed_meeting=False,
        callback_requested=False,
        approval_pending=False,
        budget_mentioned=False,
        budget_paused=False,
        max_attempts=max_attempts,
    )

    if not decision.should_follow_up:
        return None

    # Cancel any existing scheduled follow-ups
    existing = await session.execute(
        select(FollowUpQueue).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
    )
    for ext in existing.scalars().all():
        ext.status = transition(ext.status, "cancelled")
        ext.cancellation_reason = "Superseded by new evaluation"

    # 3. Strategy
    strategy_dec = select_strategy(
        reason=decision.reason,
        buying_stage=latest_intent.buying_stage if latest_intent else None,
        health_band=None,
        follow_up_attempt=fu_count + 1,
        days_since_last_contact=(now - last_out.replace(tzinfo=timezone.utc)).days if last_out else 0,
        has_proposal=False,
        has_budget=False,
        has_meeting=False,
        objections_detected=[],
        policy=policy,
        workspace_id=workspace_id,
    )
    
    if decision.explainability:
        decision.explainability.strategy = strategy_dec.strategy
        decision.explainability.strategy_instructions = strategy_dec.instructions

    # 4. Context & Generation
    ctx = await build_context(
        session, customer_id, conversation_id,
        follow_up_reason=decision.reason,
        follow_up_strategy=strategy_dec.strategy,
        strategy_instructions=strategy_dec.instructions,
        attempt_number=fu_count + 1,
        workspace_id=workspace_id,
    )

    logger.info(f"[TRACE] Generating AI message (LLM called) for customer_id: {customer_id}")
    msg = await generate_message(ctx)

    # 5. Quality Check
    logger.info(f"[TRACE] Quality Checker executed for drafted message")
    q_res = check(msg.content)
    
    is_paused = not q_res.passed
    if is_paused:
        logger.warning("followup_quality_check_failed", customer_id=str(customer_id), issues=q_res.issues)

    # 6. Queue
    logger.info(f"[TRACE] FollowUpQueue record inserted (status: {'human_paused' if is_paused else 'scheduled'})")
    queue_item = FollowUpQueue(
        workspace_id=workspace_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        reason=decision.reason,
        strategy=strategy_dec.strategy,
        status="scheduled",
        priority=decision.priority,
        scheduled_for=decision.scheduled_for,
        generated_message=msg.content,
        final_message=msg.content,
        explainability_report=decision.explainability.model_dump() if decision.explainability else None,
        confidence_score=msg.confidence,
        risk_score=decision.risk_score,
        human_paused=human_paused,
        channel="whatsapp", # default for phase 6
    )

    session.add(queue_item)
    await session.flush()
    await crm_sync.sync_followup_created(session, queue_item.id, customer_id, queue_item.reason, workspace_id)
    
    return queue_item


# ── Operational methods ────────────────────────────────────────────────────────

async def get_queue_page(
    session: AsyncSession,
    workspace_id: UUID,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> FollowUpQueuePage:
    q = select(FollowUpQueue, Customer).outerjoin(Customer, FollowUpQueue.customer_id == Customer.id).where(FollowUpQueue.workspace_id == workspace_id)
    
    if status:
        q = q.where(FollowUpQueue.status == status)
    if priority:
        q = q.where(FollowUpQueue.priority == priority)
        
    q = q.order_by(FollowUpQueue.scheduled_for.asc())
    
    total = await session.scalar(select(func.count()).select_from(q.subquery())) or 0
    
    offset = (page - 1) * page_size
    q = q.offset(offset).limit(page_size)
    
    result = await session.execute(q)
    rows = result.all()
    
    items = []
    for fu, cust in rows:
        summary = FollowUpQueueSummary.model_validate(fu)
        if cust:
            summary.customer_name = cust.name
            summary.customer_phone = cust.phone
        items.append(summary)
        
    return FollowUpQueuePage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total
    )


async def get_detail(session: AsyncSession, followup_id: UUID, workspace_id: UUID) -> Optional[FollowUpQueueDetail]:
    from sqlalchemy.orm import selectinload
    
    q = select(FollowUpQueue, Customer).outerjoin(Customer, FollowUpQueue.customer_id == Customer.id).options(
        selectinload(FollowUpQueue.executions)
    ).where(
        FollowUpQueue.id == followup_id,
        FollowUpQueue.workspace_id == workspace_id
    )
    row = await session.execute(q)
    res = row.first()
    if not res:
        return None
        
    fu, cust = res
    detail = FollowUpQueueDetail.model_validate(fu)
    if cust:
        detail.customer_name = cust.name
        detail.customer_phone = cust.phone
    return detail


async def pause(session: AsyncSession, followup_id: UUID, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.human_paused = True
        logger.info("followup_paused", followup_id=str(followup_id))


async def resume(session: AsyncSession, followup_id: UUID, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.human_paused = False
        logger.info("followup_resumed", followup_id=str(followup_id))


async def cancel(session: AsyncSession, followup_id: UUID, reason: str, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.status = transition(fu.status, "cancelled")
        fu.cancellation_reason = reason
        await crm_sync.sync_followup_cancelled(session, fu.id, reason, workspace_id)
        logger.info("followup_cancelled_by_human", followup_id=str(followup_id))


async def update_message(session: AsyncSession, followup_id: UUID, message: str, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.final_message = message
        fu.human_edited = True
        logger.info("followup_message_edited", followup_id=str(followup_id))


async def reschedule(session: AsyncSession, followup_id: UUID, scheduled_for: datetime, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.scheduled_for = scheduled_for
        logger.info("followup_rescheduled", followup_id=str(followup_id), scheduled_for=str(scheduled_for))


async def assign(session: AsyncSession, followup_id: UUID, user_id: UUID, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        fu.assigned_to = user_id
        logger.info("followup_assigned", followup_id=str(followup_id), user_id=str(user_id))


async def send_now(session: AsyncSession, followup_id: UUID, workspace_id: UUID) -> None:
    fu = await session.get(FollowUpQueue, followup_id)
    if fu and fu.workspace_id == workspace_id:
        # Just update scheduled_for to now. The worker will pick it up immediately.
        fu.scheduled_for = datetime.now(tz=timezone.utc)
        fu.human_paused = False
        logger.info("followup_send_now_requested", followup_id=str(followup_id))
