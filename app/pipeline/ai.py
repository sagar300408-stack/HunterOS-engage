"""
Pipeline Stage 4 — AI Processing

Responsibilities:
  - Fetch conversation history from the database (stateless, no in-memory cache)
  - Inject memory context (Phase 2: customer history, preferences)
  - Call the OpenAI Chat Completions API
  - Emit AIRequested and AIResponded events
  - Return the full AI result dict (content + all metadata)
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations import service as message_service
from app.events.dispatcher import dispatcher
from app.events.message_events import AIRequested, AIResponded
from app.integrations.openai.client import get_ai_response
from app.pipeline.memory import inject_memory
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def process_with_ai(
    conversation_id: UUID,
    from_phone: str,
    user_content: str,
    session: AsyncSession,
) -> dict:
    """
    Stage 4: Build context, call OpenAI, return structured response.

    The system is stateless — history is always fetched from PostgreSQL,
    making horizontal scaling safe with no shared state.

    Args:
        conversation_id: UUID of the active conversation.
        from_phone:      Customer's phone number (for memory lookup).
        user_content:    The raw incoming message text.
        session:         Active async database session.

    Returns:
        Full result dict from integrations/openai/client.py:
        content, model, tokens, latency_ms, estimated_cost_usd, etc.
    """
    logger.info(
        "ai_stage_started",
        conversation_id=str(conversation_id),
        from_phone=from_phone,
    )

    # ── Emit AIRequested event ────────────────────────────────────────────────
    dispatcher.dispatch(
        AIRequested(
            conversation_id=conversation_id,
            from_phone=from_phone,
            user_content=user_content,
        )
    )

    # ── Fetch conversation history (stateless) ────────────────────────────────
    history = await message_service.get_conversation_history(session, conversation_id)

    # ── Inject memory context (Phase 2 will populate) ─────────────────────────
    memory_context = await inject_memory(from_phone)

    # Build the full context: memory + prior history (excluding the just-saved
    # incoming message — it will be appended as the user_message parameter)
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

    return ai_result
