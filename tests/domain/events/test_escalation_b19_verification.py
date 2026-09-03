import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation, Message, MessageDirection
from app.domain.intent.models import IntentHistory, IntentCategory, UrgencyLevel
from app.domain.intent.schemas import IntentResult, NextAction, ExtractedField
from app.domain.intent.service import save_intent
from app.domain.escalation.models import HumanEscalation, EscalationStatus
from app.domain.escalation.service import resolve_escalation

@pytest.mark.asyncio
async def test_human_escalation_lifecycle(pg_session, pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    workspace_id = uuid.uuid4()
    
    customer = Customer(
        phone="+1b19esctest01",
        workspace_id=workspace_id,
        status="new",
    )
    pg_session.add(customer)
    await pg_session.flush()

    conv = Conversation(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        customer_id=customer.id,
        customer_phone=customer.phone,
    )
    pg_session.add(conv)
    await pg_session.flush()

    msg1 = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        content="I am very angry!",
        direction=MessageDirection.incoming,
        timestamp=datetime.now(timezone.utc),
    )
    pg_session.add(msg1)
    await pg_session.flush()

    # B6 -> B19 Trigger
    intent_result = IntentResult(
        intent=IntentCategory.complaint,
        confidence=0.85,
        urgency=UrgencyLevel.high,
        next_action=NextAction.ESCALATE_TO_HUMAN,
    )
    
    intent_history = await save_intent(
        session=pg_session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg1.id,
        intent_result=intent_result,
        workspace_id=workspace_id,
    )

    # Assert escalation created
    stmt = select(HumanEscalation).where(HumanEscalation.customer_id == customer.id)
    result = await pg_session.execute(stmt)
    escalations = list(result.scalars().all())
    
    assert len(escalations) == 1
    esc = escalations[0]
    assert esc.status == EscalationStatus.pending
    assert esc.trigger_intent == IntentCategory.complaint.value
    assert esc.trigger_next_action == NextAction.ESCALATE_TO_HUMAN

    # Idempotency check: trigger again on new message
    msg2 = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        content="Still angry!",
        direction=MessageDirection.incoming,
        timestamp=datetime.now(timezone.utc),
    )
    pg_session.add(msg2)
    await pg_session.flush()
    
    await save_intent(
        session=pg_session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg2.id,
        intent_result=intent_result,
        workspace_id=workspace_id,
    )
    
    result2 = await pg_session.execute(stmt)
    escalations2 = list(result2.scalars().all())
    assert len(escalations2) == 1  # Should still be 1 (idempotent)

    # Resolve escalation
    resolved_esc = await resolve_escalation(
        session=pg_session,
        escalation_id=esc.id,
        workspace_id=workspace_id,
        resolved_by="agent@test.com",
        resolution_note="Handled complaint",
    )
    assert resolved_esc.status == EscalationStatus.resolved
    assert resolved_esc.resolved_by == "agent@test.com"
    
    # Non-escalation intent
    msg3 = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        content="What is the price?",
        direction=MessageDirection.incoming,
        timestamp=datetime.now(timezone.utc),
    )
    pg_session.add(msg3)
    await pg_session.flush()

    intent_result_safe = IntentResult(
        intent=IntentCategory.pricing_request,
        confidence=0.90,
        urgency=UrgencyLevel.medium,
        next_action=NextAction.SHARE_PRICING_IMMEDIATELY,
    )
    
    await save_intent(
        session=pg_session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg3.id,
        intent_result=intent_result_safe,
        workspace_id=workspace_id,
    )
    
    result3 = await pg_session.execute(stmt)
    escalations3 = list(result3.scalars().all())
    assert len(escalations3) == 1  # Still 1, no new escalation created
