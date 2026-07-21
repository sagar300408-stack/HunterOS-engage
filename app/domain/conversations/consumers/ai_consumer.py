"""
Consumer for MessageReceived.
Triggers AI processing and publishes AIResponded.
"""
from typing import List, Type
import logging

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.message_events import MessageReceived, AIResponded
from app.integrations.postgres.database import get_session
from app.pipeline.ai import process_with_ai
from app.domain.customers.service import get_customer

logger = logging.getLogger(__name__)

class AIProcessingConsumer(EventConsumer):
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageReceived]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, MessageReceived):
            return

        async with get_session() as session:
            # Re-fetch customer and conversation objects needed by process_with_ai
            # This is a bit of overhead but ensures pure decoupling
            from app.domain.conversations.service import get_conversation_by_id
            from app.domain.customers.models import Customer
            from sqlalchemy import select
            
            # MessageReceived doesn't have conversation_id on it directly, 
            # wait, it does not. We'll need to fetch the customer by phone.
            customer = await session.scalar(select(Customer).where(Customer.phone == event.from_phone))
            if not customer:
                logger.error("AIProcessingConsumer: Customer not found")
                return

            # Fetch active conversation
            # For simplicity, we just use the customer to get their active conversation
            from app.domain.conversations.models import Conversation
            from sqlalchemy import desc
            
            conv = await session.scalar(
                select(Conversation)
                .where(Conversation.customer_id == customer.id)
                .order_by(desc(Conversation.created_at))
                .limit(1)
            )
            
            if not conv:
                logger.error("AIProcessingConsumer: Conversation not found")
                return

            # Dummy message_id for now as we don't have it on MessageReceived
            import uuid
            message_id = uuid.uuid4()
            
            ai_result = await process_with_ai(
                conversation_id=conv.id,
                message_id=message_id,
                customer=customer,
                user_content=event.content,
                session=session,
            )

            # Publish AIResponded
            response_event = AIResponded(
                response_content=ai_result["content"],
                model="gpt-4",  # mocked metadata
                total_tokens=0,
                latency_ms=0,
                estimated_cost_usd=0.0
            )
            
            # Since we can't easily inject the bus here in this refactor, 
            # we do the same hack or import the bus
            from app.events.store.service import EventStoreService
            from app.events.store.repository import EventStoreRepository
            from app.events.bus.event_bus import EventBus
            
            local_bus = EventBus(EventStoreService(EventStoreRepository()))
            await local_bus.publish(session, response_event)
            
            await session.commit()
