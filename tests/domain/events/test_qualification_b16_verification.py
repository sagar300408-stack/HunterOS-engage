import uuid
import pytest
from sqlalchemy import select

from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation, Message, MessageDirection
from app.domain.intent.models import IntentHistory, IntentCategory, UrgencyLevel
from app.domain.leads.service import qualify_lead
from app.domain.leads.models import LeadQualificationSnapshot
from app.integrations.postgres.database import create_tables

@pytest.mark.asyncio
async def test_lead_qualification_persistence(pg_session, pg_engine):
    # Ensure tables are created
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    workspace_id = uuid.uuid4()
    workspace_2 = uuid.uuid4()
    
    customer = Customer(
        phone="+16b16test01",
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

    from datetime import datetime, timezone
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        content="Hello, I want to buy",
        direction=MessageDirection.incoming,
        timestamp=datetime.now(timezone.utc),
    )
    pg_session.add(msg)
    await pg_session.flush()

    intent = IntentHistory(
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg.id,
        workspace_id=workspace_id,
        detected_intent=IntentCategory.purchase_ready,
        confidence=0.95,
        buying_stage="Purchase Ready",
        urgency=UrgencyLevel.high,
        budget="500000",
        timeline="Q1 2025",
        next_action="Close Deal",
    )
    pg_session.add(intent)
    await pg_session.flush()

    qual_dict = await qualify_lead(pg_session, customer.id, conversation_id=None, workspace_id=workspace_id)
    
    assert qual_dict["score"] >= 70
    assert qual_dict["grade"] == "A"
    assert qual_dict["qualified"] is True

    stmt = select(LeadQualificationSnapshot).where(LeadQualificationSnapshot.customer_id == customer.id)
    result = await pg_session.execute(stmt)
    snapshot = result.scalars().first()

    assert snapshot is not None
    assert snapshot.score == qual_dict["score"]
    assert snapshot.grade == qual_dict["grade"]
    assert snapshot.workspace_id == workspace_id
    
    # Test workspace isolation
    stmt_iso = select(LeadQualificationSnapshot).where(
        LeadQualificationSnapshot.customer_id == customer.id,
        LeadQualificationSnapshot.workspace_id == workspace_2
    )
    result_iso = await pg_session.execute(stmt_iso)
    assert result_iso.scalars().first() is None
