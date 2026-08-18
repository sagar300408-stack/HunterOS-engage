"""
Consumer for RawWebhookEvent.
Parses the Meta webhook and initiates the conversational pipeline.
"""
from typing import List, Type

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.model.actor_types import ActorType
from app.events.message_events import RawWebhookEvent, MessageReceived
from app.pipeline.receive import receive
from app.integrations.postgres.database import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebhookReceiveConsumer(EventConsumer):
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.ORDERED

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [RawWebhookEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, RawWebhookEvent):
            return

        # 1. Parse and persist the message via the receive pipeline stage
        async with get_session() as session:
            try:
                # We pass the event bus to receive() so it can publish MessageStored etc.
                # Since we don't have dependency injection for event_bus yet, we will 
                # retrieve it from the consumer registry or just publish MessageReceived here.
                # Actually, let's just use the current registry's event_bus, but for now 
                # we'll let receive() handle its own publishing if we update it.
                
                # To avoid circular imports and since event_bus is attached to app state,
                # we can just publish MessageReceived from here after receive() finishes.
                result = await receive(event.payload, session)
                
                if result:
                    conversation, message_data, customer, message = result
                    
                    # We need to trigger the next stage (AI processing)
                    # By publishing MessageReceived, the AIProcessingConsumer will pick it up.
                    from app.celery_app import celery_app
                    
                    # We can instantiate a local EventBus just for publishing, but it's cleaner to 
                    # do it through a shared instance.
                    # For Phase D, let's assume receive() has been refactored to NOT use dispatcher,
                    # and we publish MessageReceived right here.
                    
                    logger.info("webhook_receive_completed", conversation_id=str(conversation.id))
                    
                    msg_event = MessageReceived(
                        wa_message_id=message_data["wa_message_id"],
                        from_phone=message_data["from_phone"],
                        to_phone="", # system phone is usually not in payload directly or not needed here
                        content=message_data["content"],
                        timestamp=message_data["timestamp"],
                        contact_name=message_data["contact_name"],
                        message_id=message.id,
                        workspace_id=customer.workspace_id,
                        customer_id=customer.id,
                        conversation_id=conversation.id,
                        actor_type=ActorType.CUSTOMER,
                        correlation_id=message.id,
                    )
                    
                    # To publish it properly via EventBus, we need the EventBus instance.
                    # We will mock a direct handle for now, or we can use the registry.
                    # The outbox pattern means we must persist it. 
                    from app.events.bus.event_bus import EventBus
                    from app.events.store.service import EventStoreService
                    from app.events.store.repository import EventStoreRepository
                    
                    store = EventStoreService(EventStoreRepository())
                    local_bus = EventBus(store)
                    await local_bus.publish(session, msg_event)
                    
                await session.commit()
            except Exception as e:
                logger.error("webhook_receive_consumer_error", error=str(e), exc_info=True)
                raise
