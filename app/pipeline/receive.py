"""
Pipeline Stage 1 — Receive

Responsibilities:
  - Extract and validate message data from the Meta webhook payload
  - Deduplicate against previously processed WhatsApp message IDs
  - Persist the incoming message to the database
  - Emit MessageReceived and MessageStored events

Returns (Conversation, message_data) on success, None if skipped.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations import service as message_service
from app.domain.conversations.schemas import MessageDirectionEnum, SaveMessageDTO
from app.events.dispatcher import dispatcher
from app.events.message_events import MessageReceived, MessageStored
from app.utils.helpers import extract_message_data
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def receive(
    payload: dict,
    session: AsyncSession,
) -> Optional[tuple]:
    """
    Stage 1: Parse, validate, dedup, and persist the incoming message.

    Args:
        payload: Raw Meta webhook JSON payload.
        session: Active async database session.

    Returns:
        (Conversation, message_data dict) — or None if the message
        should not be processed (non-text, duplicate, malformed).
    """
    # ── Extract ──────────────────────────────────────────────────────────────
    message_data = extract_message_data(payload)

    if not message_data:
        logger.debug(
            "receive_stage_skipped",
            reason="non_text_or_invalid_payload",
        )
        return None

    wa_message_id = message_data["wa_message_id"]
    from_phone = message_data["from_phone"]

    logger.info(
        "incoming_message_received",
        from_phone=from_phone,
        wa_message_id=wa_message_id,
        contact_name=message_data["contact_name"],
        content_preview=message_data["content"][:80],
    )

    # ── Emit MessageReceived event ────────────────────────────────────────────
    dispatcher.dispatch(
        MessageReceived(
            wa_message_id=wa_message_id,
            from_phone=from_phone,
            content=message_data["content"],
            timestamp=message_data["timestamp"],
            contact_name=message_data["contact_name"],
        )
    )

    # ── Deduplication ─────────────────────────────────────────────────────────
    if await message_service.is_duplicate_message(session, wa_message_id):
        logger.warning(
            "duplicate_message_skipped",
            wa_message_id=wa_message_id,
            from_phone=from_phone,
        )
        return None

    # ── Conversation lookup / creation ────────────────────────────────────────
    conversation = await message_service.get_or_create_conversation(
        session, from_phone
    )

    # ── Persist incoming message ──────────────────────────────────────────────
    dto = SaveMessageDTO(
        conversation_id=conversation.id,
        direction=MessageDirectionEnum.incoming,
        content=message_data["content"],
        wa_message_id=wa_message_id,
        timestamp=message_data["timestamp"],
    )
    message = await message_service.save_message(session, dto)

    # ── Emit MessageStored event ──────────────────────────────────────────────
    dispatcher.dispatch(
        MessageStored(
            message_id=message.id,
            conversation_id=conversation.id,
            from_phone=from_phone,
        )
    )

    return conversation, message_data
