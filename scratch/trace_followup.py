import asyncio
import logging
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.postgres.database import get_engine, get_session
from app.domain.security.models import DEFAULT_WORKSPACE_ID
from app.domain.customers.models import Customer
from app.domain.conversations.models import Conversation
from app.domain.scheduling.models import ScheduledEvent
from app.domain.intent.models import IntentHistory
from app.domain.memory.models import CustomerMemory
from app.domain.followup.models import FollowUpQueue
from app.domain.scheduling.service import transition_event, TransitionEventRequest
from app.domain.followup.models import FollowUpQueue
from sqlalchemy import select

# We want to see all logs from followup and scheduling
import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("trace")

async def run_trace():
    engine = get_engine()
    
    # Needs a real session
    async with get_session() as session:
        # 1. Setup mock data
        cust_id = uuid4()
        conv_id = uuid4()
        event_id = uuid4()
        
        cust = Customer(id=cust_id, workspace_id=DEFAULT_WORKSPACE_ID, name="Trace Test", phone="+15550000000")
        conv = Conversation(id=conv_id, workspace_id=DEFAULT_WORKSPACE_ID, customer_id=cust_id, customer_phone="+15550000000")
        
        now = datetime.now(tz=timezone.utc)
        ev = ScheduledEvent(
            id=event_id,
            workspace_id=DEFAULT_WORKSPACE_ID,
            customer_id=cust_id,
            event_type="Site Visit",
            status="confirmed",
            title="Test Site Visit",
            scheduled_for=now,
            duration_minutes=60,
        )
        
        session.add_all([cust, conv, ev])
        await session.commit()
        
        # 2. Trigger the completion
        logger.info(f"Triggering transition_event to complete event {event_id}...")
        req = TransitionEventRequest(new_status="completed", note="Site visit completed successfully")
        
        try:
            await transition_event(session, event_id, req, workspace_id=DEFAULT_WORKSPACE_ID)
            await session.commit()
        except Exception as e:
            logger.error(f"Error during transition: {e}", exc_info=True)
            
        # 3. Check for FollowUpQueue record
        result = await session.execute(
            select(FollowUpQueue).where(FollowUpQueue.customer_id == cust_id)
        )
        queues = result.scalars().all()
        
        logger.info(f"Found {len(queues)} follow-up queue records for customer {cust_id}.")
        for q in queues:
            logger.info(f"Queue ID: {q.id}, status: {q.status}, reason: {q.reason}, strategy: {q.strategy}")
            
        # Cleanup
        await session.delete(ev)
        for q in queues:
            await session.delete(q)
        await session.delete(conv)
        await session.delete(cust)
        await session.commit()
        
if __name__ == "__main__":
    # Import and register subscribers just like main.py
    from app.events.followup_subscribers import register_notification_bus_subscribers
    from app.domain.scheduling.notification_bus import notification_bus
    
    register_notification_bus_subscribers()
    
    asyncio.run(run_trace())
