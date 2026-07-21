"""
Pipeline Stage 4 — AI Processing (Phase 3 + Phase 4 Events)

Responsibilities:
  - Build 4-block memory context (Phase 2)
  - Run intent extraction and inject intent context block (Phase 3)
  - Fetch conversation history (stateless)
  - Call OpenAI conversational response
  - Post-response: conditional memory update + last_interaction stamp
  - Emit AIRequested and AIResponded events
  - Log pipeline events for Event Replay (Phase 4 — NEW)
"""

from uuid import UUID
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.conversations import service as message_service
from app.domain.customers import service as customer_service
from app.domain.customers.models import Customer
from app.domain.memory import service as memory_service

from app.events.message_events import AIRequested, AIResponded
from app.integrations.openai.provider import get_ai_provider
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

    Context construction order:
        1. System prompt (v3.txt)
        2. Customer Profile block
        3. Structured Memory block
        4. Rolling Summary block
        5. Intent block
        6. Recent conversation history
        7. New user message
    """
    settings = get_settings()

    logger.info(
        "ai_stage_started",
        conversation_id=str(conversation_id),
        customer_id=str(customer.id),
        phone=customer.phone,
    )

    # ── Emit AIRequested event ────────────────────────────────────────────────
    # Event creation moved to consumer

    # ── Fetch conversation history (stateless) ────────────────────────────────
    history = await message_service.get_conversation_history(session, conversation_id)

    # ── Stage 5: Inject memory context (4-block, Phase 2) ────────────────────
    t0 = time.monotonic()
    memory_context = await inject_memory(session=session, customer=customer)
    t_memory = int((time.monotonic() - t0) * 1000)

    # Grab memory summary to give the intent extractor extra context
    memory = await memory_service.get_customer_memory(session, customer.id)
    memory_summary = memory.summary if memory else None

    # Log Stage 3: memory_loaded
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="memory_loaded",
            duration_ms=t_memory,
            payload={"summary": memory_summary, "message_count": memory.message_count if memory else 0},
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_memory_loaded_step", error=str(e))

    # ── Stage 6: Intent extraction (Phase 3) ──────────────────────────────────
    t0 = time.monotonic()
    intent_result = await classify_intent(
        session=session,
        customer=customer,
        conversation_id=conversation_id,
        message_id=message_id,
        user_content=user_content,
        conversation_history=history[:-1],   # exclude the just-saved incoming msg
        memory_summary=memory_summary,
    )
    t_intent = int((time.monotonic() - t0) * 1000)

    # Log Stage 4: intent_extracted
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="intent_extracted",
            duration_ms=t_intent,
            payload={
                "intent": str(intent_result.intent),
                "confidence": intent_result.confidence,
                "urgency": str(intent_result.urgency),
                "buying_stage": intent_result.buying_stage,
                "reasoning": intent_result.raw_extraction.get("reasoning"),
            },
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_intent_extracted_step", error=str(e))

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
    t0 = time.monotonic()
    ai_result = await get_ai_provider().get_ai_response(
        conversation_history=full_history,
        user_message=user_content,
    )
    t_ai = int((time.monotonic() - t0) * 1000)

    # Log Stage 5: response_generated
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="response_generated",
            duration_ms=t_ai,
            payload={
                "response": ai_result["content"],
                "model": ai_result["model"],
                "total_tokens": ai_result["total_tokens"],
                "cost": float(ai_result["estimated_cost_usd"]),
            },
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_response_generated_step", error=str(e))

    # ── Emit AIResponded event ────────────────────────────────────────────────
    # Event creation moved to consumer

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

    t_mem_update = 0
    if should_update:
        t0 = time.monotonic()
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
        t_mem_update = int((time.monotonic() - t0) * 1000)
    else:
        logger.debug(
            "memory_update_skipped",
            customer_id=str(customer.id),
            message_count=memory.message_count,
        )

    # Log Stage 6: memory_updated
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="memory_updated",
            duration_ms=t_mem_update if should_update else None,
            payload={
                "updated": should_update,
                "trigger": trigger,
                "current_summary": memory.summary,
            },
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_memory_updated_step", error=str(e))

    # ── Stage 11: Update last_interaction ─────────────────────────────────────
    await customer_service.update_last_interaction(session, customer.id)

    return ai_result
