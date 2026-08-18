"""
Consumer for AIResponded.
Triggers sending response and publishes ReplySent.
"""
from typing import List, Type
import logging
import time

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.message_events import AIResponded, ReplySent, MessageReadyToSendEvent
from app.integrations.postgres.database import get_session
from app.pipeline.respond import send_response

logger = logging.getLogger(__name__)

class ResponseConsumer(EventConsumer):
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.BACKGROUND

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [AIResponded]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, AIResponded):
            return

        async with get_session() as session:
            # We have to_phone directly on AIResponded
            to_phone = event.to_phone
            conversation_id = event.conversation_id
            
            ai_result = {
                "content": event.response_content,
                "model": event.model,
                "prompt_tokens": event.total_tokens,
                "completion_tokens": 0,
                "total_tokens": event.total_tokens,
                "latency_ms": event.latency_ms,
                "estimated_cost_usd": event.estimated_cost_usd,
                "finish_reason": "stop",
                "prompt_version": "v1"
            }
            
            # send_response persists the outbound message. It needs the customer id too?
            # actually we don't have to change send_response unless it requires it, 
            # let's assume send_response works with just conversation_id.
            await send_response(
                to_phone=to_phone,
                conversation_id=conversation_id,
                ai_result=ai_result,
                session=session
            )
            
            # Publish MessageReadyToSendEvent
            ready_event = MessageReadyToSendEvent(
                to_phone=to_phone,
                content=event.response_content,
                conversation_id=str(conversation_id),
                workspace_id=event.workspace_id,
                customer_id=event.customer_id,
                actor_type=event.actor_type,
                correlation_id=event.correlation_id,
                causation_id=event.source_message_id, # causation is the inbound message
            )
            
            from app.events.store.service import EventStoreService
            from app.events.store.repository import EventStoreRepository
            from app.events.bus.event_bus import EventBus
            
            local_bus = EventBus(EventStoreService(EventStoreRepository()))
            await local_bus.publish(session, ready_event)
            await session.commit()
