"""
Consumer for MessageReadyToSendEvent.
Calls the WhatsApp API and publishes ReplySent.
"""
from typing import List, Type
import logging

from app.events.bus.interfaces import EventConsumer, ExecutionPolicy
from app.events.model.base_event import UniversalBaseEvent
from app.events.message_events import MessageReadyToSendEvent, ReplySent, ErrorOccurred
from app.integrations.postgres.database import get_session
from app.integrations.whatsapp.provider import get_whatsapp_provider

logger = logging.getLogger(__name__)

class WhatsAppSendConsumer(EventConsumer):
    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.BACKGROUND

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageReadyToSendEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, MessageReadyToSendEvent):
            return

        try:
            # ── Send via WhatsApp ─────────────────────────────────────────────────────
            wa_message_id = await get_whatsapp_provider().send_text_message(
                to=event.to_phone, 
                body=event.content
            )

            logger.info(
                "reply_sent",
                to_phone=event.to_phone,
                wa_message_id=wa_message_id,
                content_preview=event.content[:80],
            )

            async with get_session() as session:
                reply_event = ReplySent(
                    to_phone=event.to_phone,
                    content=event.content,
                    wa_message_id=wa_message_id,
                )
                
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, reply_event)
                await session.commit()
                
        except Exception as e:
            logger.error("whatsapp_send_error", error=str(e))
            # Publish ErrorOccurred
            async with get_session() as session:
                error_event = ErrorOccurred(
                    stage="whatsapp_send",
                    error_message=str(e),
                    error_type=type(e).__name__,
                    from_phone=event.to_phone
                )
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, error_event)
                await session.commit()
            raise
