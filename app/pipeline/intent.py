"""
Pipeline Stage 6 — Intent Classification (Phase 3 — Activated)

Responsibilities:
  - Run intent extraction via a dedicated OpenAI call (temperature=0, JSON mode)
  - Persist the result to intent_history
  - Sync buying_stage to the customer profile
  - Return IntentResult for use by the AI context builder

Design:
  - Intent extraction runs on EVERY message — it is fast (~100 tokens) and
    deterministic, making every conversation turn immediately queryable.
  - This stage runs BEFORE the conversational AI call so the intent block
    can enrich the AI's context.
  - Failures are swallowed safely — a fallback IntentResult is returned so
    the pipeline never crashes due to an extraction error.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers import service as customer_service
from app.domain.customers.models import Customer
from app.domain.intent import service as intent_service
from app.domain.intent.schemas import IntentResult
from app.domain.memory.models import CustomerMemory
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def classify_intent(
    session: AsyncSession,
    customer: Customer,
    conversation_id: UUID,
    message_id: UUID,
    user_content: str,
    conversation_history: list[dict],
    memory_summary: str | None = None,
) -> IntentResult:
    """
    Stage 6: Extract intent, persist to DB, sync customer profile.

    Args:
        session:              Active async DB session.
        customer:             Customer ORM object from Stage 2.
        conversation_id:      Active conversation UUID.
        message_id:           The incoming message UUID.
        user_content:         Raw incoming message text.
        conversation_history: Recent messages as OpenAI dicts (for context).
        memory_summary:       Customer's rolling memory summary (optional).

    Returns:
        IntentResult — structured extraction with next_action recommendation.
        Falls back to a safe default IntentResult on any error.
    """
    try:
        # ── Extract intent ────────────────────────────────────────────────────
        intent_result = await intent_service.extract_intent(
            session=session,
            customer_id=customer.id,
            conversation_id=conversation_id,
            message_id=message_id,
            user_content=user_content,
            conversation_history=conversation_history,
            memory_summary=memory_summary,
        )

        # ── Persist to intent_history ─────────────────────────────────────────
        await intent_service.save_intent(
            session=session,
            customer_id=customer.id,
            conversation_id=conversation_id,
            message_id=message_id,
            intent_result=intent_result,
        )

        # ── Sync buying_stage to customer profile ─────────────────────────────
        if intent_result.buying_stage:
            await customer_service.update_buying_stage(
                session=session,
                customer_id=customer.id,
                buying_stage=intent_result.buying_stage,
            )

        logger.info(
            "intent_stage_completed",
            customer_id=str(customer.id),
            intent=str(intent_result.intent),
            confidence=intent_result.confidence,
            next_action=intent_result.next_action,
            buying_stage=intent_result.buying_stage,
        )

        return intent_result

    except Exception as exc:
        # Never crash the pipeline — return a safe default
        logger.error(
            "intent_stage_failed",
            customer_id=str(customer.id),
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        
        # O9: Retry extraction in background
        try:
            from app.domain.intent.tasks import retry_intent_extraction
            retry_intent_extraction.apply_async(kwargs=dict(
                customer_id_str=str(customer.id),
                conversation_id_str=str(conversation_id),
                message_id_str=str(message_id),
                user_content=user_content,
                conversation_history=conversation_history,
                memory_summary=memory_summary,
                workspace_id_str=str(customer.workspace_id) if hasattr(customer, "workspace_id") else None
            ))
        except Exception as retry_exc:
            logger.error(f"Failed to queue intent retry: {retry_exc}")

        from app.domain.intent.models import IntentCategory, UrgencyLevel
        from app.domain.intent.schemas import ExtractedField
        return IntentResult(
            intent=IntentCategory.other,
            confidence=0.0,
            urgency=UrgencyLevel.unknown,
            next_action="Continue Conversation",
        )
