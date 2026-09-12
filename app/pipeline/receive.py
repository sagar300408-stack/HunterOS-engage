"""
Pipeline Stage 1 — Receive
Phase 2 — Customer Identification

Responsibilities:
  - Extract and validate message data from the Meta webhook payload
  - Deduplicate against previously processed WhatsApp message IDs
  - Identify or create the Customer (Stage 2 — NEW in Phase 2)
  - Persist the incoming message to the database
  - Emit MessageReceived, MessageStored, and customer events

Returns (Conversation, message_data, Customer) on success, None if skipped.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations import service as message_service
from app.domain.conversations.models import Message
from app.domain.conversations.schemas import MessageDirectionEnum, SaveMessageDTO
from app.domain.customers import service as customer_service
from app.domain.memory.service import MemoryService
from app.domain.memory.schemas import CustomerMemoryCreateRequest
from app.domain.memory.models import (
    MemoryEventType,
    CustomerMemoryTimelineEvent,
    MemoryTimelineCategory,
    MemoryImportance,
)
from app.utils.helpers import extract_message_data
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def receive(
    payload: dict,
    session: AsyncSession,
) -> Optional[tuple]:
    """
    Stage 1 + Stage 2: Parse, validate, dedup, identify customer, and persist.

    Args:
        payload: Raw Meta webhook JSON payload.
        session: Active async database session.

    Returns:
        (Conversation, message_data dict, Customer) — or None if the message
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
    contact_name = message_data["contact_name"]

    logger.info(
        "incoming_message_received",
        from_phone=from_phone,
        wa_message_id=wa_message_id,
        contact_name=contact_name,
        content_preview=message_data["content"][:80],
    )



    # ── Deduplication ─────────────────────────────────────────────────────────
    if await message_service.is_duplicate_message(session, wa_message_id):
        logger.warning(
            "duplicate_message_skipped",
            wa_message_id=wa_message_id,
            from_phone=from_phone,
        )
        return None

    # ── Stage 2: Customer Identification ─────────────────────────────────────
    is_new_customer = await customer_service.get_customer(session, from_phone) is None

    customer = await customer_service.get_or_create_customer(
        session,
        phone=from_phone,
        name=contact_name,
    )

    mem_svc = MemoryService()
    memory = await mem_svc.get_customer_memory(customer.id, session=session, workspace_id=customer.workspace_id)
    if not memory:
        req = CustomerMemoryCreateRequest(
            customer_id=customer.id,
            workspace_id=customer.workspace_id,
            source="webhook",
            created_by="system",
        )
        memory = await mem_svc.create_customer_memory(req, session)

    if is_new_customer:
        session.add(CustomerMemoryTimelineEvent(
            customer_id=customer.id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type=MemoryEventType.customer_created.value,
            title="Customer Created",
            description="New customer detected via webhook.",
            source="receive_pipeline",
            importance=MemoryImportance.MEDIUM,
            payload={"phone": from_phone, "name": contact_name},
            version_number=memory.version_number,
        ))

    # ── Conversation lookup / creation (with 24h idle rule) ───────────────────
    conversation = await message_service.get_or_create_conversation(
        session,
        customer_phone=from_phone,
        customer_id=customer.id,
    )

    # Emit conversation_started event on fresh conversations.
    #
    # WHY NOT conversation.messages:
    #   Conversation.messages is a SQLAlchemy relationship with lazy="select"
    #   (the default). Accessing it in an async context triggers
    #   "greenlet_spawn has not been called" (MissingGreenlet) because SQLAlchemy
    #   Async cannot issue implicit I/O outside an awaitable greenlet.
    #
    # THE FIX:
    #   Issue a minimal explicit async query — SELECT id LIMIT 1 — which:
    #     • uses await so SQLAlchemy Async can schedule the I/O correctly
    #     • touches only one index row (ix_messages_conversation_id)
    #     • never traverses the ORM relationship attribute
    #     • is semantically identical: None means "no messages yet"
    existing_message_id = await session.scalar(
        select(Message.id)
        .where(Message.conversation_id == conversation.id)
        .limit(1)
    )
    if existing_message_id is None:
        session.add(CustomerMemoryTimelineEvent(
            customer_id=customer.id,
            memory_id=memory.id,
            category=MemoryTimelineCategory.LIFECYCLE,
            event_type=MemoryEventType.conversation_started.value,
            title="Conversation Started",
            description="A new conversation thread was started.",
            source="receive_pipeline",
            importance=MemoryImportance.MEDIUM,
            payload={"conversation_id": str(conversation.id)},
            version_number=memory.version_number,
        ))

    # ── Persist incoming message ──────────────────────────────────────────────
    dto = SaveMessageDTO(
        conversation_id=conversation.id,
        direction=MessageDirectionEnum.incoming,
        content=message_data["content"],
        wa_message_id=wa_message_id,
        timestamp=message_data["timestamp"],
    )
    message = await message_service.save_message(session, dto)

    # ── Event creation moved to consumer ──────────────────────────────────────    # ── Log Pipeline Steps for Event Replay (Phase 4) ────────────────────────
    try:
        from app.domain.dashboard.service import log_pipeline_step
        # 1. Message Received
        await log_pipeline_step(
            session=session,
            message_id=message.id,
            step="message_received",
            payload={"content": message_data["content"], "from_phone": from_phone, "wa_message_id": wa_message_id},
            workspace_id=customer.workspace_id,
        )
        # 2. Customer Identified
        await log_pipeline_step(
            session=session,
            message_id=message.id,
            step="customer_identified",
            payload={"customer_id": str(customer.id), "name": customer.name, "is_new": is_new_customer},
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_receive_pipeline_steps", error=str(e))

    # Phase 3: return the saved Message object so the pipeline has message.id
    # for intent_history persistence without an extra DB query.
    return conversation, message_data, customer, message

