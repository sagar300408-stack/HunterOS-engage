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
from app.integrations.whatsapp.provider import WhatsAppProvider

logger = logging.getLogger(__name__)

class WhatsAppSendConsumer(EventConsumer):
    def __init__(self, whatsapp_provider: WhatsAppProvider):
        self.whatsapp_provider = whatsapp_provider

    def get_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy.BACKGROUND

    def get_subscriptions(self) -> List[Type[UniversalBaseEvent]]:
        return [MessageReadyToSendEvent]

    async def handle_event(self, event: UniversalBaseEvent) -> None:
        if not isinstance(event, MessageReadyToSendEvent):
            return

        # ── 0. Pre-send Idempotency Guards ───────────────────────────────────────────
        # Check 1: If event references a stored message_id, check if wa_message_id is already assigned
        if event.metadata and event.metadata.get("message_id"):
            try:
                from app.domain.conversations.models import Message
                from uuid import UUID as PyUUID
                msg_uuid = PyUUID(str(event.metadata["message_id"]))
                async with get_session() as session:
                    msg = await session.get(Message, msg_uuid)
                    if msg and isinstance(getattr(msg, "wa_message_id", None), str) and msg.wa_message_id:
                        logger.info(
                            f"whatsapp_send_skipped_already_sent message_id={msg_uuid} "
                            f"wa_message_id={msg.wa_message_id}"
                        )
                        return
            except Exception as check_err:
                logger.warning(f"whatsapp_send_message_check_warning: {check_err}")

        # Check 2: Check if a ReplySent event already exists for this correlation_id
        if event.correlation_id:
            try:
                from sqlalchemy import select
                from app.events.store.models import EventRecord
                async with get_session() as session:
                    stmt = select(EventRecord).where(
                        EventRecord.workspace_id == event.workspace_id,
                        EventRecord.correlation_id == event.correlation_id,
                        EventRecord.event_name == "ReplySent",
                    ).limit(1)
                    res = await session.execute(stmt)
                    existing_reply = res.scalar_one_or_none()
                    if (
                        existing_reply
                        and isinstance(getattr(existing_reply, "payload", None), dict)
                        and existing_reply.payload.get("wa_message_id")
                    ):
                        existing_wa_id = existing_reply.payload.get("wa_message_id")
                        logger.info(
                            f"whatsapp_send_skipped_already_sent correlation_id={event.correlation_id} "
                            f"existing_wa_message_id={existing_wa_id}"
                        )
                        return
            except Exception as check_err:
                logger.warning(f"whatsapp_send_replysent_check_warning: {check_err}")

        wa_message_id = None
        try:
            # ── 1. Send via WhatsApp Provider ─────────────────────────────────────────
            wa_message_id = await self.whatsapp_provider.send_text_message(
                to=event.to_phone, 
                body=event.content
            )

            logger.info(
                f"reply_sent to_phone={event.to_phone} wa_message_id={wa_message_id} correlation_id={event.correlation_id}"
            )
            
            # Additional log for test verification
            if "THIS IS A TEST MESSAGE" in event.content:
                logger.info(f"[WHATSAPP TEST] response sent successfully wa_message_id={wa_message_id}")

        except Exception as e:
            # Provider failure: message was NOT sent. Record ErrorOccurred and re-raise for retry.
            logger.error(f"whatsapp_send_error: {str(e)}")
            try:
                async with get_session() as session:
                    error_event = ErrorOccurred(
                        workspace_id=event.workspace_id,
                        actor_type=event.actor_type,
                        correlation_id=event.correlation_id,
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
            except Exception as store_err:
                logger.error(f"failed_to_publish_error_event: {store_err}")
            raise

        # ── 2. Post-delivery event publication ────────────────────────────────────────
        # The external message has already been accepted by Meta (wa_message_id is known).
        # Any subsequent failure in publishing ReplySent must NOT re-raise to Celery/caller,
        # avoiding unexamined duplicate message sends on worker retries.
        try:
            async with get_session() as session:
                reply_event = ReplySent(
                    workspace_id=event.workspace_id,
                    actor_type=event.actor_type,
                    correlation_id=event.correlation_id,
                    to_phone=event.to_phone,
                    content=event.content,
                    wa_message_id=wa_message_id,
                )
                
                from app.events.store.service import EventStoreService
                from app.events.store.repository import EventStoreRepository
                from app.events.bus.event_bus import EventBus
                
                local_bus = EventBus(EventStoreService(EventStoreRepository()))
                await local_bus.publish(session, reply_event)

                if event.metadata and event.metadata.get("message_id"):
                    try:
                        from app.domain.conversations.models import Message
                        from uuid import UUID as PyUUID
                        msg_uuid = PyUUID(str(event.metadata["message_id"]))
                        msg_obj = await session.get(Message, msg_uuid)
                        if msg_obj:
                            msg_obj.wa_message_id = wa_message_id
                    except Exception as msg_update_err:
                        logger.warning(f"whatsapp_post_send_message_update_warning: {msg_update_err}")

                await session.commit()
        except Exception as post_err:
            logger.error(
                f"whatsapp_post_send_event_error: External message sent (wa_message_id={wa_message_id}) "
                f"but failed to record ReplySent: {post_err}",
                exc_info=True
            )
