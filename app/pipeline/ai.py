"""
Pipeline Stage 4 — AI Processing (Phase 2)

Responsibilities:
  - Build 4-block memory context (customer profile, facts, summary)
  - Fetch conversation history from database (stateless)
  - Call the OpenAI Chat Completions API
  - After sending response: conditionally update customer memory
  - Update customer last_interaction timestamp
  - Emit AIRequested and AIResponded events

Phase 2 additions vs Phase 1:
  - inject_memory() now receives session + customer (not just phone)
  - Post-response memory update with smart trigger logic
  - last_interaction stamped on every successful response
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.conversations import service as message_service
from app.domain.customers import service as customer_service
from app.domain.customers.models import Customer
from app.domain.memory import service as memory_service
from app.events.dispatcher import dispatcher
from app.events.message_events import AIRequested, AIResponded
from app.integrations.openai.client import get_ai_response
from app.pipeline.memory import inject_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def process_with_ai(
    conversation_id: UUID,
    customer: Customer,
    user_content: str,
    session: AsyncSession,
) -> dict:
    """
    Stage 4: Build context, call OpenAI, update memory, return structured response.

    The system is stateless — history is always fetched from PostgreSQL,
    making horizontal scaling safe with no shared state.

    Args:
        conversation_id: UUID of the active conversation.
        customer:        Customer ORM object from Stage 2.
        user_content:    The raw incoming message text.
        session:         Active async database session.

    Returns:
        Full result dict from integrations/openai/client.py:
        content, model, tokens, latency_ms, estimated_cost_usd, etc.
    """
    settings = get_settings()

    logger.info(
        "ai_stage_started",
        conversation_id=str(conversation_id),
        customer_id=str(customer.id),
        phone=customer.phone,
    )

    # ── Emit AIRequested event ────────────────────────────────────────────────
    dispatcher.dispatch(
        AIRequested(
            conversation_id=conversation_id,
            from_phone=customer.phone,
            user_content=user_content,
        )
    )

    # ── Fetch conversation history (stateless) ────────────────────────────────
    history = await message_service.get_conversation_history(session, conversation_id)

    # ── Inject memory context (Phase 2 — 4-block customer context) ────────────
    memory_context = await inject_memory(session=session, customer=customer)

    # Build the full context:
    #   memory_context (profile + facts + summary) + prior history
    # The new user message is appended as the user_message parameter in get_ai_response
    full_history = memory_context + history[:-1]

    # ── Call OpenAI ───────────────────────────────────────────────────────────
    ai_result = await get_ai_response(
        conversation_history=full_history,
        user_message=user_content,
    )

    # ── Emit AIResponded event ────────────────────────────────────────────────
    dispatcher.dispatch(
        AIResponded(
            conversation_id=conversation_id,
            response_content=ai_result["content"],
            model=ai_result["model"],
            total_tokens=ai_result["total_tokens"],
            latency_ms=ai_result["latency_ms"],
            estimated_cost_usd=ai_result["estimated_cost_usd"],
        )
    )

    # ── Stage 8: Conditional Memory Update ────────────────────────────────────
    # Increment message count and check update trigger
    memory = await memory_service.get_or_create_memory(session, customer.id)
    memory.message_count += 1
    await session.flush()

    should_update, trigger = memory_service._should_update_memory(
        message_count=memory.message_count,
        ai_response=ai_result["content"],
        interval=settings.memory_update_interval,
    )

    if should_update:
        logger.info(
            "memory_update_triggered",
            customer_id=str(customer.id),
            trigger=trigger,
            message_count=memory.message_count,
        )
        # Fetch recent messages across conversations for extraction context
        recent_messages = await message_service.get_recent_messages_across_conversations(
            session, customer.id, limit=20
        )
        await memory_service.update_customer_memory(
            session=session,
            customer_id=customer.id,
            conversation_history=recent_messages,
            ai_response=ai_result["content"],
            trigger=trigger,
        )
    else:
        logger.debug(
            "memory_update_skipped",
            customer_id=str(customer.id),
            message_count=memory.message_count,
            next_update_at=memory.message_count + (
                settings.memory_update_interval - (memory.message_count % settings.memory_update_interval)
            ),
        )

    # ── Stage 9: Update last_interaction ──────────────────────────────────────
    await customer_service.update_last_interaction(session, customer.id)

    return ai_result
