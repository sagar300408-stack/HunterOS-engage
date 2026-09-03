"""
BW4 Certification Test — B6 (Intent Failure Handling & Fallback Classification)

Tests run against real PostgreSQL.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone

# ── Bootstrap SQLAlchemy mapper order ─────────────────────────────────────────
from app.domain.customers.models import Customer  # noqa: F401 — must be first
from app.domain.conversations.models import Conversation, Message, MessageDirection  # noqa: F401
from app.domain.intent.models import IntentCategory, IntentHistory, UrgencyLevel
from app.domain.intent.schemas import ExtractedField, IntentResult, NextAction
import app.domain.intent.service as intent_service
from app.domain.escalation.models import HumanEscalation, EscalationStatus
from sqlalchemy import select


@pytest_asyncio.fixture
async def pg_session_intent(pg_engine):
    from app.domain.conversations.models import Base
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _setup_conversation_hierarchy(session, workspace_id: uuid.UUID):
    customer = Customer(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        phone=f"+1b6test{uuid.uuid4().hex[:8]}",
        name="Test Customer B6",
    )
    session.add(customer)
    await session.flush()

    conv = Conversation(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        customer_id=customer.id,
        customer_phone=customer.phone,
    )
    session.add(conv)
    await session.flush()

    msg = Message(
        id=uuid.uuid4(),
        conversation_id=conv.id,
        direction=MessageDirection.incoming,
        content="Testing message extraction",
        timestamp=datetime.now(timezone.utc),
    )
    session.add(msg)
    await session.flush()

    return customer, conv, msg


@pytest.mark.asyncio
async def test_b6_fallback_flag_persisted_on_extraction_failure(pg_session_intent):
    """
    B6 Intent Failure Handling:
    When extraction fails or returns fallback defaults (confidence=0.0, intent=Other, is_fallback=True),
    IntentHistory must persist is_fallback=True in PostgreSQL.
    """
    session = pg_session_intent
    workspace_id = uuid.uuid4()
    customer, conv, msg = await _setup_conversation_hierarchy(session, workspace_id)

    fallback_result = IntentResult(
        intent=IntentCategory.other,
        confidence=0.0,
        urgency=UrgencyLevel.unknown,
        buying_stage=None,
        next_action=NextAction.CONTINUE_CONVERSATION,
        is_fallback=True,
        raw_extraction={"is_fallback": True, "reasoning": "Intent extraction failed; defaulted to fallback classification."},
    )

    saved_row = await intent_service.save_intent(
        session=session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg.id,
        intent_result=fallback_result,
        workspace_id=workspace_id,
    )

    # Verify directly from DB
    stmt = select(IntentHistory).where(IntentHistory.id == saved_row.id)
    res = await session.execute(stmt)
    db_row = res.scalar_one()

    assert db_row.is_fallback is True
    assert db_row.confidence == 0.0
    assert db_row.detected_intent == IntentCategory.other


@pytest.mark.asyncio
async def test_b6_genuine_intent_not_flagged_as_fallback(pg_session_intent):
    """
    B6 Positive Path:
    When extraction succeeds with a genuine classified intent,
    IntentHistory must persist is_fallback=False.
    """
    session = pg_session_intent
    workspace_id = uuid.uuid4()
    customer, conv, msg = await _setup_conversation_hierarchy(session, workspace_id)

    genuine_result = IntentResult(
        intent=IntentCategory.product_inquiry,
        confidence=0.95,
        budget=ExtractedField(value="$500,000", confidence=0.9),
        timeline=ExtractedField(value="Immediate", confidence=0.85),
        urgency=UrgencyLevel.high,
        buying_stage="Purchase Ready",
        next_action=NextAction.SHARE_PRODUCT_DETAILS,
        is_fallback=False,
        raw_extraction={"intent": "Product Inquiry", "confidence": 0.95},
    )

    saved_row = await intent_service.save_intent(
        session=session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg.id,
        intent_result=genuine_result,
        workspace_id=workspace_id,
    )

    stmt = select(IntentHistory).where(IntentHistory.id == saved_row.id)
    res = await session.execute(stmt)
    db_row = res.scalar_one()

    assert db_row.is_fallback is False
    assert db_row.detected_intent == IntentCategory.product_inquiry
    assert db_row.confidence == 0.95


@pytest.mark.asyncio
async def test_b6_failure_escalation_trigger_path(pg_session_intent):
    """
    B6 + B19 Integration:
    When next_action is ESCALATE_TO_HUMAN (e.g. Complaint or severe fallback failure),
    save_intent() automatically creates a HumanEscalation record in PostgreSQL.
    """
    session = pg_session_intent
    workspace_id = uuid.uuid4()
    customer, conv, msg = await _setup_conversation_hierarchy(session, workspace_id)

    escalation_result = IntentResult(
        intent=IntentCategory.complaint,
        confidence=0.88,
        urgency=UrgencyLevel.high,
        buying_stage=None,
        next_action=NextAction.ESCALATE_TO_HUMAN,
        is_fallback=False,
        raw_extraction={"intent": "Complaint", "confidence": 0.88},
    )

    await intent_service.save_intent(
        session=session,
        customer_id=customer.id,
        conversation_id=conv.id,
        message_id=msg.id,
        intent_result=escalation_result,
        workspace_id=workspace_id,
    )

    # Verify HumanEscalation was created
    stmt = select(HumanEscalation).where(
        HumanEscalation.workspace_id == workspace_id,
        HumanEscalation.customer_id == customer.id,
    )
    res = await session.execute(stmt)
    escalations = res.scalars().all()

    assert len(escalations) == 1
    assert escalations[0].status == EscalationStatus.pending.value
    assert escalations[0].trigger_intent == "Complaint"
    assert escalations[0].trigger_next_action == NextAction.ESCALATE_TO_HUMAN
