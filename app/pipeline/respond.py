"""
Pipeline Stage 6 — Respond

Responsibilities:
  - Persist the outgoing AI message with full metadata to the database
  - Send the reply via the WhatsApp integration client
  - Emit the ReplySent event
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations import service as message_service
from app.domain.conversations.schemas import (
    AIMetadataSchema,
    MessageDirectionEnum,
    SaveMessageDTO,
)
from app.events.dispatcher import dispatcher
from app.events.message_events import ReplySent
from app.integrations.whatsapp.provider import get_whatsapp_provider
from app.utils.logger import get_logger
from app.utils.clock import SystemClock

logger = get_logger(__name__)


async def send_response(
    to_phone: str,
    conversation_id: UUID,
    ai_result: dict,
    session: AsyncSession,
) -> None:
    """
    Stage 6: Persist the AI reply and deliver it via WhatsApp.

    Saves first, then sends — so even if the WhatsApp API call fails,
    the outgoing message is already in the database for audit purposes.

    Args:
        to_phone:        Recipient phone number.
        conversation_id: Active conversation UUID.
        ai_result:       Full result dict from pipeline/ai.py.
        session:         Active async database session.
    """
    content = ai_result["content"]

    # ── Persist outgoing message + AI metadata ────────────────────────────────
    dto = SaveMessageDTO(
        conversation_id=conversation_id,
        direction=MessageDirectionEnum.outgoing,
        content=content,
        wa_message_id=None,  # populated below after send
        timestamp=SystemClock.now(),
        ai_metadata=AIMetadataSchema(
            model=ai_result["model"],
            prompt_tokens=ai_result["prompt_tokens"],
            completion_tokens=ai_result["completion_tokens"],
            total_tokens=ai_result["total_tokens"],
            latency_ms=ai_result["latency_ms"],
            estimated_cost_usd=ai_result["estimated_cost_usd"],
            finish_reason=ai_result["finish_reason"],
            prompt_version=ai_result["prompt_version"],
        ),
    )
    outgoing_message = await message_service.save_message(session, dto)

    logger.info(
        "database_insert_successful",
        stage="outgoing_message",
        message_id=str(outgoing_message.id),
        conversation_id=str(conversation_id),
    )

    # ── Send via WhatsApp ─────────────────────────────────────────────────────
    wa_message_id = await get_whatsapp_provider().send_text_message(to=to_phone, body=content)

    logger.info(
        "reply_sent",
        to_phone=to_phone,
        wa_message_id=wa_message_id,
        content_preview=content[:80],
    )

    # ── Emit ReplySent event ──────────────────────────────────────────────────
    dispatcher.dispatch(
        ReplySent(
            to_phone=to_phone,
            content=content,
            wa_message_id=wa_message_id,
        )
    )
