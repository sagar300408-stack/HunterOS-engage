"""
message_service — Conversation and message persistence.

All database read/write operations for the conversations domain.
The pipeline exclusively calls this service; no layer touches ORM models directly.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.conversations.models import (
    AIMetadata,
    Conversation,
    Message,
    MessageDirection,
)
from app.domain.conversations.schemas import SaveMessageDTO
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_or_create_conversation(
    session: AsyncSession,
    customer_phone: str,
) -> Conversation:
    """
    Fetch the most recent conversation for this phone number,
    or create a new one. This keeps the flow idempotent.
    """
    result = await session.execute(
        select(Conversation)
        .where(Conversation.customer_phone == customer_phone)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(
            customer_phone=customer_phone,
            created_at=datetime.now(timezone.utc),
        )
        session.add(conversation)
        await session.flush()  # get the generated UUID before commit
        logger.info(
            "conversation_created",
            conversation_id=str(conversation.id),
            customer_phone=customer_phone,
        )
    else:
        logger.debug(
            "conversation_found",
            conversation_id=str(conversation.id),
            customer_phone=customer_phone,
        )

    return conversation


async def is_duplicate_message(
    session: AsyncSession,
    wa_message_id: str,
) -> bool:
    """
    Check whether this WhatsApp message ID has already been processed.
    Prevents double-handling on Meta webhook retries.
    """
    result = await session.execute(
        select(Message).where(Message.wa_message_id == wa_message_id)
    )
    return result.scalar_one_or_none() is not None


async def save_message(session: AsyncSession, dto: SaveMessageDTO) -> Message:
    """
    Persist a message and its optional AI metadata to the database.
    Flushes (but does not commit) — the route handler commits via get_db().
    """
    message = Message(
        conversation_id=dto.conversation_id,
        direction=MessageDirection(dto.direction.value),
        content=dto.content,
        wa_message_id=dto.wa_message_id,
        timestamp=dto.timestamp,
    )
    session.add(message)
    await session.flush()

    if dto.ai_metadata:
        metadata = AIMetadata(
            message_id=message.id,
            model=dto.ai_metadata.model,
            prompt_tokens=dto.ai_metadata.prompt_tokens,
            completion_tokens=dto.ai_metadata.completion_tokens,
            total_tokens=dto.ai_metadata.total_tokens,
            latency_ms=dto.ai_metadata.latency_ms,
            estimated_cost_usd=dto.ai_metadata.estimated_cost_usd,
            finish_reason=dto.ai_metadata.finish_reason,
            prompt_version=dto.ai_metadata.prompt_version,
        )
        session.add(metadata)
        await session.flush()

    logger.info(
        "database_insert_successful",
        message_id=str(message.id),
        conversation_id=str(dto.conversation_id),
        direction=dto.direction.value,
    )

    return message


async def get_conversation_history(
    session: AsyncSession,
    conversation_id: UUID,
) -> list[dict]:
    """
    Return all messages in a conversation as OpenAI-compatible message dicts.

    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    This is the context window fed to the AI on every new message.
    The system is stateless — history is always rebuilt from the database.
    """
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .options(selectinload(Message.ai_metadata))
    )
    messages = result.scalars().all()

    history = []
    for msg in messages:
        role = "user" if msg.direction == MessageDirection.incoming else "assistant"
        history.append({"role": role, "content": msg.content})

    return history
