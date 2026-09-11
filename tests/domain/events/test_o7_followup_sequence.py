import pytest
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func

from app.domain.followup.service import schedule_followup
from app.domain.followup.models import FollowUpQueue, FollowUpExecution
from app.domain.customers.models import Customer
from app.domain.intent.models import IntentHistory

@pytest.mark.asyncio
async def test_o7_followup_sequence_is_deterministic_and_idempotent(pg_session_factory):
    # This requires pg_session_factory (will use sqlite in memory if conftest sets it, or pg if pg)
    # Wait, if this test needs to test pg_advisory_xact_lock, it needs PG. But we can test the sequence logic in SQLite too (the exception is caught).
    
    workspace_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    
    async with pg_session_factory() as session:
        # Create customer
        import random
        cust = Customer(id=customer_id, workspace_id=workspace_id, name="Test Cust", phone=f"+155500{random.randint(10000, 99999)}")
        session.add(cust)
        await session.commit()
        
    async with pg_session_factory() as session:
        # 1. Trigger follow-up Step 1
        fu1 = await schedule_followup(session, customer_id, workspace_id=workspace_id)
        assert fu1 is not None, "Should schedule Step 1"
        assert fu1.status == "scheduled"
        await session.commit()
        
    async with pg_session_factory() as session:
        # Simulate executing Step 1
        fu1_db = await session.get(FollowUpQueue, fu1.id)
        fu1_db.status = "sent"
        fu1_db.executed_at = datetime.now(timezone.utc)
        await session.commit()
        
    async with pg_session_factory() as session:
        # 2. Trigger follow-up Step 2 (as if from FollowUpExecutedConsumer)
        fu2 = await schedule_followup(session, customer_id, workspace_id=workspace_id)
        assert fu2 is not None, "Should schedule Step 2"
        await session.commit()
        
    async with pg_session_factory() as session:
        # 3. Prove Idempotency! 
        # If the same event arrives AGAIN, it should NOT advance to Step 3.
        # It should just cancel Step 2 and reschedule Step 2.
        fu2_duplicate = await schedule_followup(session, customer_id, workspace_id=workspace_id)
        assert fu2_duplicate is not None
        await session.commit()
        
    async with pg_session_factory() as session:
        # Verify only ONE scheduled follow-up exists (Step 2)
        q = select(func.count(FollowUpQueue.id)).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
        scheduled_count = await session.scalar(q)
        assert scheduled_count == 1, "O7 PROOF FAILED: Duplicate progression created multiple scheduled steps"
        
        # Verify it is Step 2 (i.e. only 1 sent previously)
        q_sent = select(func.count(FollowUpQueue.id)).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "sent")
        sent_count = await session.scalar(q_sent)
        assert sent_count == 1, "O7 PROOF FAILED: Sent count changed unexpectedly"
        
    # Execute Step 2
    async with pg_session_factory() as session:
        # Execute the new scheduled one
        q = select(FollowUpQueue).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
        fu2_db = (await session.execute(q)).scalar_one()
        fu2_db.status = "sent"
        fu2_db.executed_at = datetime.now(timezone.utc)
        await session.commit()
        
    # Trigger Step 3
    async with pg_session_factory() as session:
        fu3 = await schedule_followup(session, customer_id, workspace_id=workspace_id)
        assert fu3 is not None, "Should schedule Step 3"
        await session.commit()
        
    # Execute Step 3
    async with pg_session_factory() as session:
        q = select(FollowUpQueue).where(FollowUpQueue.customer_id == customer_id, FollowUpQueue.status == "scheduled")
        fu3_db = (await session.execute(q)).scalar_one()
        fu3_db.status = "sent"
        fu3_db.executed_at = datetime.now(timezone.utc)
        await session.commit()
        
    # Trigger Step 4
    async with pg_session_factory() as session:
        # max_attempts is typically 3 for default policy
        fu4 = await schedule_followup(session, customer_id, workspace_id=workspace_id)
        assert fu4 is None, "O7 PROOF FAILED: Sequence is not finite! Scheduled beyond max_attempts (3)."
