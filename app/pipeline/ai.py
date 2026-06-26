"""
Pipeline Stage 4 — AI Processing (Phase 3)

Responsibilities:
  - Build 4-block memory context (Phase 2)
  - Run intent extraction and inject intent context block (Phase 3 — NEW)
  - Fetch conversation history (stateless)
  - Call OpenAI conversational response
  - Post-response: conditional memory update + last_interaction stamp
  - Emit AIRequested and AIResponded events

Phase 3 additions vs Phase 2:
  - classify_intent() called between memory injection and AI call
  - Intent context block inserted into full_history
  - message_id now accepted (required for intent_history FK)
  - ai_result enriched with intent_result for downstream use
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
from app.pipeline.intent import classify_intent
from app.pipeline.memory import inject_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def process_with_ai(
    conversation_id: UUID,
    message_id: UUID,
    customer: Customer,
    user_content: str,
    session: AsyncSession,
) -> dict:
    """
    Stage 4: Build full context, extract intent, call OpenAI, update memory.

    Context construction order (per spec):
        1. System prompt (v3.txt)
        2. Customer Profile block       (Phase 2 memory)
        3. Structured Memory block      (Phase 2 memory)
        4. Rolling Summary block        (Phase 2 memory)
        5. Intent block                 (Phase 3 — NEW)
        6. Recent conversation history
        7. New user message

    Args:
        conversation_id: UUID of the active conversation.
        message_id:      UUID of the incoming Message row.
        customer:        Customer ORM object from Stage 2.
        user_content:    The raw incoming message text.
        session:         Active async database session.

    Returns:
        Enriched result dict — all OpenAI metadata plus intent_result key.
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

    # ── Stage 5: Inject memory context (4-block, Phase 2) ────────────────────
    memory_context = await inject_memory(session=session, customer=customer)

    # ── Stage 6: Intent extraction (Phase 3) ──────────────────────────────────
    # Grab memory summary to give the intent extractor extra context
    memory = await memory_service.get_customer_memory(session, customer.id)
    memory_summary = memory.summary if memory else None

    intent_result = await classify_intent(
        session=session,
        customer=customer,
        conversation_id=conversation_id,
        message_id=message_id,
        user_content=user_content,
        conversation_history=history[:-1],   # exclude the just-saved incoming msg
        memory_summary=memory_summary,
    )

    # Build the intent context block injected into the AI call
    intent_context = [{
        "role": "system",
        "content": (
            "DETECTED CUSTOMER INTENT:\n"
            + intent_result.build_context_block()
            + "\n\nGuide your response to naturally move the customer toward "
            "this next action without being explicit about the classification."
        ),
    }] if intent_result.confidence > 0.0 else []

    # ── Build full history ────────────────────────────────────────────────────
    # Order: memory blocks → intent block → conversation history
    full_history = memory_context + intent_context + history[:-1]

    # ── Call OpenAI conversational response ───────────────────────────────────
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

    # Attach intent result to ai_result for downstream use (Phase 5/6)
    ai_result["intent_result"] = intent_result

    # ── Stage 10: Conditional Memory Update (Phase 2) ─────────────────────────
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
        )

    # ── Stage 11: Update last_interaction ─────────────────────────────────────
    await customer_service.update_last_interaction(session, customer.id)

    return ai_result
