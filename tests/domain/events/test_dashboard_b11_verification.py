import pytest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.dashboard.service import get_overview_metrics
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation, Message, AIMetadata
from app.domain.memory.models import CustomerMemoryEvent
from app.utils.clock import SystemClock

@pytest.mark.asyncio
async def test_b11_dashboard_aggregation_correctness(pg_session: AsyncSession, pg_session_factory):
    """
    B11 VERIFICATION:
    Proves that the dashboard overview accurately aggregates metrics directly from the DB.
    Tests: Total customers, New leads today, Qualified leads, Purchase ready, Active conversations, AI success rate.
    Uses real PostgreSQL persistence.
    """
    ws_id = uuid.uuid4()
    other_ws_id = uuid.uuid4()
    
    now = SystemClock.now()
    yesterday = now - timedelta(days=1, hours=1)
    
    async with pg_session_factory() as s:
        async with s.begin():
            # Workspace 1 Data (The one we will query)
            p1, p2, p3, p4 = str(uuid.uuid4())[:15], str(uuid.uuid4())[:15], str(uuid.uuid4())[:15], str(uuid.uuid4())[:15]
            # 1. Customer created today, Purchase Ready
            c1 = Customer(id=uuid.uuid4(), workspace_id=ws_id, name="C1", phone=p1, buying_stage="Purchase Ready", created_at=now)
            # 2. Customer created yesterday, Qualified (Evaluation)
            c2 = Customer(id=uuid.uuid4(), workspace_id=ws_id, name="C2", phone=p2, buying_stage="Evaluation", created_at=yesterday)
            # 3. Customer created yesterday, Unqualified (Research)
            c3 = Customer(id=uuid.uuid4(), workspace_id=ws_id, name="C3", phone=p3, buying_stage="Research", created_at=yesterday)
            
            # Workspace 2 Data (Must be ignored)
            c_other = Customer(id=uuid.uuid4(), workspace_id=other_ws_id, name="CO", phone=p4, buying_stage="Purchase Ready", created_at=now)
            
            s.add_all([c1, c2, c3, c_other])

            # Conversations & Messages (for active conversations & AI success rate & latency & cost)
            conv1 = Conversation(id=uuid.uuid4(), workspace_id=ws_id, customer_id=c1.id, customer_phone=p1)
            conv2 = Conversation(id=uuid.uuid4(), workspace_id=ws_id, customer_id=c2.id, customer_phone=p2)
            conv_other = Conversation(id=uuid.uuid4(), workspace_id=other_ws_id, customer_id=c_other.id, customer_phone=p4)
            s.add_all([conv1, conv2, conv_other])
            
            # Active message today in conv1
            m1 = Message(id=uuid.uuid4(), conversation_id=conv1.id, direction="outgoing", content="hello", timestamp=now)
            # Inactive message yesterday in conv2
            m2 = Message(id=uuid.uuid4(), conversation_id=conv2.id, direction="outgoing", content="old", timestamp=yesterday)
            s.add_all([m1, m2])
            
            # AI Metadata for success rate and latency and cost
            meta1 = AIMetadata(id=uuid.uuid4(), message_id=m1.id, model="gpt-4o", finish_reason="stop", latency_ms=1000, estimated_cost_usd=0.01)
            meta2 = AIMetadata(id=uuid.uuid4(), message_id=m2.id, model="gpt-4o", finish_reason="length", latency_ms=2000, estimated_cost_usd=0.02)
            s.add_all([meta1, meta2])
            
            # Customer Memory Events today
            from app.domain.memory.models import CustomerMemory
            mem_root = CustomerMemory(id=uuid.uuid4(), customer_id=c1.id)
            mem = CustomerMemoryEvent(
                id=uuid.uuid4(), 
                customer_id=c1.id, 
                memory_id=mem_root.id,
                category="SYSTEM",
                event_type="memory_summarized", 
                title="Summarized",
                created_at=now
            )
            s.add_all([mem_root, mem])
            
            await s.flush()

    # Query metrics
    async with pg_session_factory() as s:
        metrics = await get_overview_metrics(s, workspace_id=ws_id)
        
        # Total customers: 3 in ws_id
        assert metrics.total_customers.value == 3
        # New leads today: 1 (c1)
        assert metrics.new_leads_today.value == 1
        # Qualified leads: 2 (c1, c2) - not None and not Research
        assert metrics.qualified_leads.value == 2
        # Purchase ready: 1 (c1)
        assert metrics.purchase_ready.value == 1
        
        # Active conversations in last 24h: 1 (conv1)
        assert metrics.active_conversations.value == 1
        
        # Avg response time: (1000 + 2000) / 2 = 1500
        assert metrics.avg_response_time_ms.value == 1500
        
        # Success rate: 1 "stop" out of 2 = 50.0%
        assert metrics.ai_success_rate.value == 50.0
        
        # Memory updates today: 1
        assert metrics.memory_updates_today.value == 1
        
        # Cost today: only m1 is today, so 0.01
        assert metrics.total_cost_today_usd.value == 0.01
        
    # Cleanup
    async with pg_session_factory() as cleanup_session:
        async with cleanup_session.begin():
            for c in [c1, c2, c3, c_other]:
                cust = await cleanup_session.get(Customer, c.id)
                if cust:
                    await cleanup_session.delete(cust)
