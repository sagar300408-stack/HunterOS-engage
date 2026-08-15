import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.domain.conversations.models import Conversation, Message, MessageDirection, AIMetadata, Base
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory, IntentCategory
from app.domain.memory.models import CustomerMemoryTimelineEvent, MemoryTimelineCategory
from app.domain.dashboard.models import BackgroundJob, JobStatus
from app.domain.security.models import AuditLog
from app.domain.dashboard import service as dash_service

@pytest.fixture
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

@pytest.fixture
def session_maker(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def db_session(engine, session_maker):
    from app.domain.conversations.models import Base as ConvBase
    from app.domain.customers.models import Base as CustBase
    from app.domain.intent.models import Base as IntentBase
    from app.domain.memory.models import Base as MemBase
    from app.domain.dashboard.models import Base as DashBase
    from app.domain.security.models import Base as SecBase
    
    async with engine.begin() as conn:
        await conn.run_sync(SecBase.metadata.create_all)
        await conn.run_sync(CustBase.metadata.create_all)
        await conn.run_sync(ConvBase.metadata.create_all)
        await conn.run_sync(IntentBase.metadata.create_all)
        await conn.run_sync(MemBase.metadata.create_all)
        await conn.run_sync(DashBase.metadata.create_all)

    async with session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def setup_data(db_session: AsyncSession):
    ws_a = uuid.uuid4()
    ws_b = uuid.uuid4()
    
    # Workspace A data
    cust_a = Customer(id=uuid.uuid4(), workspace_id=ws_a, phone="+1000000000A", name="Cust A", buying_stage="Purchase Ready")
    db_session.add(cust_a)
    conv_a = Conversation(id=uuid.uuid4(), workspace_id=ws_a, customer_id=cust_a.id, customer_phone="+1000000000A")
    db_session.add(conv_a)
    msg_a = Message(id=uuid.uuid4(), conversation_id=conv_a.id, direction=MessageDirection.incoming, content="Hello A", timestamp=datetime.now(timezone.utc))
    db_session.add(msg_a)
    ai_a = AIMetadata(id=uuid.uuid4(), message_id=msg_a.id, model="test", latency_ms=100, finish_reason="stop", estimated_cost_usd=0.01)
    db_session.add(ai_a)
    intent_a = IntentHistory(id=uuid.uuid4(), workspace_id=ws_a, customer_id=cust_a.id, conversation_id=conv_a.id, message_id=msg_a.id, detected_intent=IntentCategory.product_inquiry)
    db_session.add(intent_a)
    event_a = CustomerMemoryTimelineEvent(id=uuid.uuid4(), customer_id=cust_a.id, memory_id=uuid.uuid4(), category=MemoryTimelineCategory.MANUAL, event_type="test_event", title="Title A")
    db_session.add(event_a)
    audit_a = AuditLog(id=uuid.uuid4(), workspace_id=ws_a, action="test", target_type="customer", is_demo=False)
    db_session.add(audit_a)
    job_a = BackgroundJob(workspace_id=ws_a, job_type="test", status=JobStatus.pending, is_demo=False)
    db_session.add(job_a)

    # Workspace B data
    cust_b = Customer(id=uuid.uuid4(), workspace_id=ws_b, phone="+1000000000B", name="Cust B", buying_stage="Purchase Ready")
    db_session.add(cust_b)
    conv_b = Conversation(id=uuid.uuid4(), workspace_id=ws_b, customer_id=cust_b.id, customer_phone="+1000000000B")
    db_session.add(conv_b)
    msg_b = Message(id=uuid.uuid4(), conversation_id=conv_b.id, direction=MessageDirection.incoming, content="Hello B", timestamp=datetime.now(timezone.utc))
    db_session.add(msg_b)
    ai_b = AIMetadata(id=uuid.uuid4(), message_id=msg_b.id, model="test", latency_ms=200, finish_reason="stop", estimated_cost_usd=0.02)
    db_session.add(ai_b)
    intent_b = IntentHistory(id=uuid.uuid4(), workspace_id=ws_b, customer_id=cust_b.id, conversation_id=conv_b.id, message_id=msg_b.id, detected_intent=IntentCategory.product_inquiry)
    db_session.add(intent_b)
    event_b = CustomerMemoryTimelineEvent(id=uuid.uuid4(), customer_id=cust_b.id, memory_id=uuid.uuid4(), category=MemoryTimelineCategory.MANUAL, event_type="test_event", title="Title B")
    db_session.add(event_b)
    audit_b = AuditLog(id=uuid.uuid4(), workspace_id=ws_b, action="test", target_type="customer", is_demo=False)
    db_session.add(audit_b)
    job_b = BackgroundJob(workspace_id=ws_b, job_type="test", status=JobStatus.pending, is_demo=False)
    db_session.add(job_b)

    await db_session.commit()
    return {
        "A": {"cust": cust_a, "conv": conv_a, "msg": msg_a, "audit": audit_a, "job": job_a},
        "B": {"cust": cust_b, "conv": conv_b, "msg": msg_b, "audit": audit_b, "job": job_b},
        "ws_a": ws_a,
        "ws_b": ws_b,
    }

@pytest.mark.asyncio
async def test_dashboard_workspace_isolation(db_session: AsyncSession, setup_data):
    data = setup_data
    ws_a = data["ws_a"]
    ws_b = data["ws_b"]

    # 1. get_overview_metrics
    metrics_a = await dash_service.get_overview_metrics(db_session, ws_a)
    assert metrics_a.total_customers.value == 1
    
    # 2. get_conversations
    convs_a = await dash_service.get_conversations(db_session, ws_a)
    assert convs_a.total == 1
    assert convs_a.items[0].id == data["A"]["conv"].id
    
    # 3. get_conversation_detail
    detail_b_by_a = await dash_service.get_conversation_detail(db_session, data["B"]["conv"].id, ws_a)
    assert detail_b_by_a is None
    detail_a_by_a = await dash_service.get_conversation_detail(db_session, data["A"]["conv"].id, ws_a)
    assert detail_a_by_a is not None

    # 4. get_customers
    custs_a = await dash_service.get_customers(db_session, ws_a)
    assert custs_a.total == 1
    assert custs_a.items[0].id == data["A"]["cust"].id

    # 5. get_customer_profile
    prof_b_by_a = await dash_service.get_customer_profile(db_session, data["B"]["cust"].id, ws_a)
    assert prof_b_by_a is None
    prof_a_by_a = await dash_service.get_customer_profile(db_session, data["A"]["cust"].id, ws_a)
    assert prof_a_by_a is not None

    # 6. update_customer (A cannot modify B)
    await dash_service.update_customer(db_session, data["B"]["cust"].id, {"name": "Hacked"}, workspace_id=ws_a)
    await db_session.refresh(data["B"]["cust"])
    assert data["B"]["cust"].name != "Hacked"

    # 7. get_lead_pipeline
    leads_a = await dash_service.get_lead_pipeline(db_session, ws_a)
    assert len(leads_a.stages["Purchase Ready"]) == 1
    assert leads_a.stages["Purchase Ready"][0].customer_id == data["A"]["cust"].id

    # 8. update_lead_stage
    await dash_service.update_lead_stage(db_session, data["B"]["cust"].id, "Negotiation", workspace_id=ws_a)
    await db_session.refresh(data["B"]["cust"])
    assert data["B"]["cust"].buying_stage == "Purchase Ready"

    # 9. get_analytics
    analytics_a = await dash_service.get_analytics(db_session, ws_a)
    assert analytics_a.cost_metrics.total_cost_usd == 0.01

    # 10. get_activity_feed
    feed_a = await dash_service.get_activity_feed(db_session, ws_a)
    assert len(feed_a) == 1
    assert feed_a[0].customer_name == "Cust A"

    # 11. get_queue_status
    queue_a = await dash_service.get_queue_status(db_session, ws_a)
    assert queue_a.pending == 1
    assert queue_a.jobs[0].id == data["A"]["job"].id

    # 12. get_audit_log
    audit_a_logs = await dash_service.get_audit_log(db_session, ws_a)
    assert len(audit_a_logs) == 1
    assert audit_a_logs[0].id == data["A"]["audit"].id

    # 13. search_everything
    search_a = await dash_service.search_everything(db_session, "Hello", workspace_id=ws_a)
    assert search_a.hits[0].id == data["A"]["conv"].id

    # === WORKSPACE B REVERSE SYMMETRY ===

    # 1. get_overview_metrics
    metrics_b = await dash_service.get_overview_metrics(db_session, ws_b)
    assert metrics_b.total_customers.value == 1

    # 2. get_conversations
    convs_b = await dash_service.get_conversations(db_session, ws_b)
    assert convs_b.total == 1
    assert convs_b.items[0].id == data["B"]["conv"].id

    # 3. get_customers
    custs_b = await dash_service.get_customers(db_session, ws_b)
    assert custs_b.total == 1
    assert custs_b.items[0].id == data["B"]["cust"].id

    # 4. get_lead_pipeline
    leads_b = await dash_service.get_lead_pipeline(db_session, ws_b)
    assert len(leads_b.stages["Purchase Ready"]) == 1
    assert leads_b.stages["Purchase Ready"][0].customer_id == data["B"]["cust"].id

    # 5. get_activity_feed
    feed_b = await dash_service.get_activity_feed(db_session, ws_b)
    assert len(feed_b) == 1
    assert feed_b[0].customer_name == "Cust B"

    # 6. get_queue_status
    queue_b = await dash_service.get_queue_status(db_session, ws_b)
    assert queue_b.pending == 1
    assert queue_b.jobs[0].id == data["B"]["job"].id

    # 7. get_audit_log
    audit_b_logs = await dash_service.get_audit_log(db_session, ws_b)
    assert len(audit_b_logs) == 1
    assert audit_b_logs[0].id == data["B"]["audit"].id

    # 8. search_everything
    search_b = await dash_service.search_everything(db_session, "Hello", workspace_id=ws_b)
    assert search_b.total == 1
    assert search_b.hits[0].id == data["B"]["conv"].id

    # Workspace B cannot access A by ID
    detail_a_by_b = await dash_service.get_conversation_detail(db_session, data["A"]["conv"].id, ws_b)
    assert detail_a_by_b is None

    prof_a_by_b = await dash_service.get_customer_profile(db_session, data["A"]["cust"].id, ws_b)
    assert prof_a_by_b is None

    # Workspace B cannot modify A
    await dash_service.update_customer(db_session, data["A"]["cust"].id, {"name": "HackedByB"}, workspace_id=ws_b)
    await db_session.refresh(data["A"]["cust"])
    assert data["A"]["cust"].name == "Cust A"

    await dash_service.update_lead_stage(db_session, data["A"]["cust"].id, "Negotiation", workspace_id=ws_b)
    await db_session.refresh(data["A"]["cust"])
    assert data["A"]["cust"].buying_stage == "Purchase Ready"
