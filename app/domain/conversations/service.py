"""
message_service — Conversation and message persistence.

All database read/write operations for the conversations domain.
The pipeline exclusively calls this service; no layer touches ORM models directly.

Phase 2 additions:
    - get_or_create_conversation() now accepts customer_id and applies the
      configurable idle-window rule (CONVERSATION_IDLE_HOURS).
    - get_recent_messages_across_conversations() enables memory update context.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
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
    customer_id: Optional[UUID] = None,
) -> Conversation:
    """
    Fetch or create a conversation for this customer.

    Phase 2 idle-window rule:
        - If the most recent conversation was created < CONVERSATION_IDLE_HOURS ago
          → continue that conversation.
        - If ≥ CONVERSATION_IDLE_HOURS have passed, or no conversation exists
          → create a new one (same customer, new thread).

    This keeps conversations cleanly separated by session while the Customer
    record remains the single persistent identity.

    Args:
        session:       Active async database session.
        customer_phone: Customer's phone number (always stored on Conversation).
        customer_id:   UUID of the Customer row (Phase 2+). None for legacy rows.
    """
    settings = get_settings()
    idle_cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.conversation_idle_hours)

    result = await session.execute(
        select(Conversation)
        .where(Conversation.customer_phone == customer_phone)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()

    # ── Determine if we continue or start fresh ───────────────────────────────
    if conversation:
        # Make created_at timezone-aware for comparison if it isn't already
        conv_created = conversation.created_at
        if conv_created.tzinfo is None:
            conv_created = conv_created.replace(tzinfo=timezone.utc)

        if conv_created >= idle_cutoff:
            # Within idle window — continue this conversation
            if customer_id and conversation.customer_id is None:
                # Back-fill customer_id on legacy Phase 1 rows
                conversation.customer_id = customer_id
                await session.flush()
            logger.debug(
                "conversation_continued",
                conversation_id=str(conversation.id),
                customer_phone=customer_phone,
            )
            return conversation

        # Past idle window — log the gap and fall through to create a new one
        idle_hours = (datetime.now(timezone.utc) - conv_created).total_seconds() / 3600
        logger.info(
            "conversation_idle_window_exceeded",
            idle_hours=round(idle_hours, 1),
            threshold_hours=settings.conversation_idle_hours,
            customer_phone=customer_phone,
        )

    # ── Create new conversation ────────────────────────────────────────────────
    conversation = Conversation(
        customer_phone=customer_phone,
        customer_id=customer_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(conversation)
    await session.flush()

    logger.info(
        "conversation_created",
        conversation_id=str(conversation.id),
        customer_phone=customer_phone,
        customer_id=str(customer_id) if customer_id else None,
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

    [{\"role\": \"user\", \"content\": \"...\"}, {\"role\": \"assistant\", \"content\": \"...\"}]

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


async def get_recent_messages_across_conversations(
    session: AsyncSession,
    customer_id: UUID,
    limit: int = 20,
) -> list[dict]:
    """
    Fetch the last N messages from any conversation for this customer.

    Used by the memory service to build extraction context when performing
    a memory update — spans conversation boundaries so the AI has the
    most recent signals regardless of which conversation thread they appeared in.

    Returns OpenAI-compatible message dicts ordered oldest → newest.
    """
    # Get the most recent conversations for this customer
    conv_result = await session.execute(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)  # look across last 5 conversations at most
    )
    conversations = conv_result.scalars().all()

    if not conversations:
        return []

    conversation_ids = [c.id for c in conversations]

    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id.in_(conversation_ids))
        .order_by(Message.timestamp.desc())
        .limit(limit)
    )
    messages = msg_result.scalars().all()

    # Reverse to get chronological order (oldest → newest)
    messages = list(reversed(messages))

    history = []
    for msg in messages:
        role = "user" if msg.direction == MessageDirection.incoming else "assistant"
        history.append({"role": role, "content": msg.content})

    return history
