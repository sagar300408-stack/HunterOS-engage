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
from app.domain.memory.service import MemoryService as _MemoryService

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

    # Grab memory payload to give the intent extractor extra context
    _mem_svc = _MemoryService()
    memory = await _mem_svc.get_customer_memory(
        customer.id,
        session=session,
        workspace_id=customer.workspace_id,
    )
    memory_summary = None
    if memory and memory.memory_payload:
        personal = memory.memory_payload.get("personal_info", {})
        journey = memory.memory_payload.get("journey_snapshot", {})
        parts = []
        if personal.get("full_name"):
            parts.append(f"Name: {personal['full_name']}")
        if journey.get("current_stage"):
            parts.append(f"Stage: {journey['current_stage']}")
        memory_summary = "; ".join(parts) or None

    # Log Stage 3: memory_loaded
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="memory_loaded",
            duration_ms=t_memory,
            payload={"summary": memory_summary},
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

    # ── Controlled Test-Only Auto-Reply Check ─────────────────────────────────
    import os
    from app.utils.helpers import normalize_phone

    test_mode_enabled = (
        os.environ.get("ENABLE_WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
        or os.environ.get("WHATSAPP_TEST_AUTO_REPLY", "").lower() == "true"
    )
    authorized_recipient = normalize_phone(os.environ.get("WHATSAPP_TEST_RECIPIENT_PHONE", "919108976764"))
    sender_phone = normalize_phone(customer.phone) if customer and customer.phone else ""
    is_authorized_recipient = bool(sender_phone and sender_phone == authorized_recipient)
    is_hi_message = bool(user_content and user_content.strip().lower() == "hi")

    # Verify event has not already been processed for this test
    is_test_already_processed = False
    if test_mode_enabled and is_authorized_recipient and is_hi_message:
        from sqlalchemy import select
        from app.events.store.models import EventRecord
        
        existing_event_stmt = select(EventRecord.event_id).where(
            EventRecord.causation_id == message_id,
            EventRecord.event_name.in_(["MessageReadyToSendEvent", "ReplySent", "AIResponded"]),
        ).limit(1)
        res = await session.execute(existing_event_stmt)
        if res.scalar_one_or_none() is not None:
            is_test_already_processed = True
            logger.info(
                "whatsapp_test_reply_already_processed",
                message_id=str(message_id),
                conversation_id=str(conversation_id),
            )

    is_test_reply_triggered = (
        test_mode_enabled
        and is_authorized_recipient
        and is_hi_message
        and not is_test_already_processed
    )

    t0 = time.monotonic()
    if is_test_reply_triggered:
        test_response_text = "THIS IS A TEST MESSAGE FROM HUNTEROS ENGAGE, BACKEND VERIFIED"
        logger.info(
            f"[WHATSAPP TEST] triggered controlled test response conversation_id={conversation_id} recipient={sender_phone}"
        )
        ai_result = {
            "content": test_response_text,
            "model": "test-controlled-response",
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "latency_ms": 0,
            "estimated_cost_usd": 0.0,
            "finish_reason": "stop",
            "prompt_version": "v1"
        }
    else:
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

    # ── Stage 10: Track message count in memory metadata ──────────────────────
    t0_mem = time.monotonic()
    
    from app.domain.memory.service import MemoryService
    from app.domain.memory.schemas import CustomerMemoryUpdateRequest
    mem_svc = MemoryService()
    
    # We must patch the message_count in the memory payload
    # fetch existing first
    existing_mem = await mem_svc.get_customer_memory(customer.id, session=session, workspace_id=customer.workspace_id)
    current_count = 0
    if existing_mem and existing_mem.memory_payload:
        current_count = existing_mem.memory_payload.get("message_count", 0)
    
    req = CustomerMemoryUpdateRequest(
        workspace_id=customer.workspace_id,
        memory_payload={"message_count": current_count + 1},
        reason="Increment message count",
        trigger="message_received",
        changed_module="pipeline"
    )
    await mem_svc.update_customer_memory(customer.id, req, session=session)
    
    t_mem_update = int((time.monotonic() - t0_mem) * 1000)
    should_update = True
    trigger = "message_received"

    # Log Stage 6: memory_updated
    try:
        from app.domain.dashboard.service import log_pipeline_step
        await log_pipeline_step(
            session=session,
            message_id=message_id,
            step="memory_updated",
            duration_ms=t_mem_update,
            payload={
                "updated": should_update,
                "trigger": trigger,
            },
            workspace_id=customer.workspace_id,
        )
    except Exception as e:
        logger.error("failed_to_log_memory_updated_step", error=str(e))

    # ── Stage 11: Update last_interaction ─────────────────────────────────────
    await customer_service.update_last_interaction(session, customer.id)

    return ai_result
