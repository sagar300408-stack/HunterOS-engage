"""
intent_service — Intent extraction, persistence, and workflow recommendations.

Public API (stable — no later phase queries intent_history directly):
    extract_intent(session, customer_id, conversation_id, message_id,
                   user_content, conversation_history, memory_summary) -> IntentResult
    save_intent(session, customer_id, conversation_id, message_id,
                intent_result) -> IntentHistory
    get_latest_intent(session, customer_id) -> IntentHistory | None
    get_intent_history(session, customer_id, limit) -> list[IntentHistory]
    recommend_next_action(intent, urgency, buying_stage) -> str

Internal:
    _call_intent_extraction_api(user_content, conversation_history,
                                memory_summary) -> dict
    _map_intent_to_action(intent, urgency, buying_stage) -> str
    _safe_intent(raw) -> IntentCategory
    _safe_urgency(raw) -> UrgencyLevel

Design:
    - Extraction is a dedicated OpenAI call: temperature=0, JSON mode, ~100 tokens.
    - This call is intentionally separate from the conversational response call —
      keeping classification deterministic and independent of tone/style.
    - Every extraction is stored immediately — even failed/low-confidence ones.
    - _map_intent_to_action() is pure — no DB access, fully testable.
"""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from app.utils.clock import SystemClock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intent.models import (
    IntentCategory,
    IntentHistory,
    UrgencyLevel,
)
from app.domain.intent.schemas import (
    ExtractedField,
    IntentResult,
    NextAction,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Confidence threshold — fields below this are stored but omitted from AI context
_CONFIDENCE_THRESHOLD = 0.65


# ── Public API ────────────────────────────────────────────────────────────────

async def extract_intent(
    session: AsyncSession,
    customer_id: UUID,
    conversation_id: UUID,
    message_id: UUID,
    user_content: str,
    conversation_history: list[dict],
    memory_summary: Optional[str] = None,
) -> IntentResult:
    """
    Run the intent extraction pipeline for one incoming message.

    Calls OpenAI with a dedicated extraction prompt, parses the result,
    maps to a next action, and returns a structured IntentResult.

    Does NOT persist — call save_intent() after if you want DB storage.

    Args:
        session:              Active async DB session (passed for future use).
        customer_id:          Customer UUID.
        conversation_id:      Active conversation UUID.
        message_id:           The incoming message UUID.
        user_content:         Raw text of the incoming message.
        conversation_history: Recent messages as OpenAI dicts (for context).
        memory_summary:       Customer's rolling memory summary (optional context).

    Returns:
        IntentResult with all extracted fields and recommended next action.
    """
    logger.info(
        "intent_extraction_started",
        customer_id=str(customer_id),
        message_preview=user_content[:80],
    )

    from app.domain.customers.models import Customer
    customer_obj = await session.get(Customer, customer_id)
    workspace_id_str = str(customer_obj.workspace_id) if customer_obj and customer_obj.workspace_id else None

    raw = await _call_intent_extraction_api(
        user_content=user_content,
        conversation_history=conversation_history,
        memory_summary=memory_summary,
        workspace_id_str=workspace_id_str,
        session=session
    )

    # ── Parse intent ──────────────────────────────────────────────────────────
    intent      = _safe_intent(raw.get("intent", "Other"))
    confidence  = float(raw.get("confidence", 0.0))
    urgency     = _safe_urgency(raw.get("urgency", "unknown"))
    buying_stage = raw.get("buying_stage")

    # ── Parse confidence-scored fields ────────────────────────────────────────
    budget_raw   = raw.get("budget", {})
    timeline_raw = raw.get("timeline", {})
    interest_raw = raw.get("interest", {})
    location_raw = raw.get("location", {})

    budget = ExtractedField(
        value=budget_raw.get("value") if isinstance(budget_raw, dict) else None,
        confidence=float(budget_raw.get("confidence", 0.0)) if isinstance(budget_raw, dict) else 0.0,
    )
    timeline = ExtractedField(
        value=timeline_raw.get("value") if isinstance(timeline_raw, dict) else None,
        confidence=float(timeline_raw.get("confidence", 0.0)) if isinstance(timeline_raw, dict) else 0.0,
    )
    interest = ExtractedField(
        value=interest_raw.get("value") if isinstance(interest_raw, dict) else None,
        confidence=float(interest_raw.get("confidence", 0.0)) if isinstance(interest_raw, dict) else 0.0,
    )
    location = ExtractedField(
        value=location_raw.get("value") if isinstance(location_raw, dict) else None,
        confidence=float(location_raw.get("confidence", 0.0)) if isinstance(location_raw, dict) else 0.0,
    )

    # ── Recommend next action ─────────────────────────────────────────────────
    next_action = _map_intent_to_action(intent, urgency, buying_stage)
    is_fallback = bool(raw.get("is_fallback", False) or (confidence == 0.0 and intent == IntentCategory.other))

    result = IntentResult(
        intent=intent,
        confidence=confidence,
        budget=budget,
        timeline=timeline,
        interest=interest,
        location=location,
        urgency=urgency,
        buying_stage=buying_stage,
        next_action=next_action,
        is_fallback=is_fallback,
        raw_extraction=raw,
    )

    logger.info(
        "intent_extraction_completed",
        intent=intent.value,
        confidence=confidence,
        urgency=urgency.value,
        buying_stage=buying_stage,
        next_action=next_action,
        is_fallback=is_fallback,
        has_budget=bool(budget.value),
        has_timeline=bool(timeline.value),
    )

    return result


async def save_intent(
    session: AsyncSession,
    customer_id: UUID,
    conversation_id: UUID,
    message_id: UUID,
    intent_result: IntentResult,
    workspace_id: Optional[UUID] = None,
) -> IntentHistory:
    """
    Persist an IntentResult to intent_history.

    Called after extract_intent() whenever you want DB storage.
    Idempotent by message_id (unique constraint) — safe to retry.
    """
    row = IntentHistory(
        customer_id=customer_id,
        conversation_id=conversation_id,
        message_id=message_id,
        detected_intent=intent_result.intent,
        confidence=intent_result.confidence,
        budget=intent_result.budget.value,
        budget_confidence=intent_result.budget.confidence or None,
        timeline=intent_result.timeline.value,
        timeline_confidence=intent_result.timeline.confidence or None,
        interest=intent_result.interest.value,
        interest_confidence=intent_result.interest.confidence or None,
        location=intent_result.location.value,
        location_confidence=intent_result.location.confidence or None,
        urgency=intent_result.urgency,
        buying_stage=intent_result.buying_stage,
        next_action=intent_result.next_action,
        is_fallback=intent_result.is_fallback,
        extracted_json=intent_result.raw_extraction,
        # Phase 4 explainability fields
        reasoning=intent_result.raw_extraction.get("reasoning"),
        memory_influenced=intent_result.raw_extraction.get("memory_influenced"),
        detected_keywords=intent_result.raw_extraction.get("detected_keywords"),
        workspace_id=workspace_id,
        created_at=SystemClock.now(),
    )
    session.add(row)
    await session.flush()

    logger.info(
        "intent_history_saved",
        intent_history_id=str(row.id),
        customer_id=str(customer_id),
        intent=str(intent_result.intent),
        has_reasoning=bool(row.reasoning),
    )

    # ── Phase 4 B19 (BW4): Trigger Human Escalation ───────────────────────────
    from app.domain.intent.schemas import NextAction
    if intent_result.next_action == NextAction.ESCALATE_TO_HUMAN:
        from app.domain.escalation.service import create_escalation
        if workspace_id:
            await create_escalation(
                session=session,
                workspace_id=workspace_id,
                customer_id=customer_id,
                conversation_id=conversation_id,
                intent_history_id=row.id,
                trigger_intent=str(intent_result.intent),
                trigger_next_action=intent_result.next_action,
                context_snapshot={
                    "buying_stage": intent_result.buying_stage,
                    "urgency": str(intent_result.urgency) if intent_result.urgency else None,
                    "confidence": intent_result.confidence,
                },
            )
        else:
            logger.warning(
                "escalation_skipped_no_workspace",
                customer_id=str(customer_id),
                intent_history_id=str(row.id),
            )

    return row


async def get_latest_intent(
    session: AsyncSession,
    customer_id: UUID,
) -> Optional[IntentHistory]:
    """
    Return the most recent intent extraction row for this customer.
    Used by Phase 5/6 to determine current buying stage and next action.
    """
    result = await session.execute(
        select(IntentHistory)
        .where(IntentHistory.customer_id == customer_id)
        .order_by(IntentHistory.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_intent_history(
    session: AsyncSession,
    customer_id: UUID,
    limit: int = 10,
) -> list[IntentHistory]:
    """
    Return the N most recent intent rows for this customer, newest first.
    Used by the Phase 4 dashboard.
    """
    result = await session.execute(
        select(IntentHistory)
        .where(IntentHistory.customer_id == customer_id)
        .order_by(IntentHistory.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def recommend_next_action(
    intent: IntentCategory,
    urgency: UrgencyLevel,
    buying_stage: Optional[str] = None,
) -> str:
    """
    Pure function — no DB access. Returns the recommended workflow action.
    Exposed publicly so callers can re-derive recommendations without a DB round-trip.
    """
    return _map_intent_to_action(intent, urgency, buying_stage)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _call_intent_extraction_api(
    user_content: str,
    conversation_history: list[dict],
    memory_summary: Optional[str] = None,
    workspace_id_str: Optional[str] = None,
    throw_on_error: bool = False,
    session: Optional[AsyncSession] = None,
) -> dict:
    """
    Dedicated OpenAI call for intent extraction.

    Temperature 0 + JSON mode = deterministic, structured output.
    Completely independent of the conversational response call.
    """
    from app.integrations.openai.client import get_openai_client
    from app.config import get_settings
    from app.domain.intent.models import PromptConfig
    from sqlalchemy import select

    settings = get_settings()
    client = get_openai_client()

    # Format last 10 messages as context (keep prompt short)
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation_history[-10:]
        if not m.get("role") == "system"   # skip injected system blocks
    )
    memory_text = f"\nCUSTOMER MEMORY SUMMARY:\n{memory_summary}" if memory_summary else ""

    # Fetch custom prompt config if available
    base_prompt = "You are a real estate sales intent classification system."
    if session and workspace_id_str:
        import uuid
        prompt_config = await session.scalar(
            select(PromptConfig).where(PromptConfig.workspace_id == uuid.UUID(workspace_id_str))
        )
        if prompt_config:
            base_prompt = prompt_config.prompt_text

    extraction_prompt = f"""{base_prompt}

Analyse the customer's latest message and conversation context, then extract structured information.{memory_text}

CONVERSATION CONTEXT (recent):
{history_text}

LATEST CUSTOMER MESSAGE:
{user_content}

Return a JSON object with EXACTLY this structure:
{{
  "intent": "<one of: Product Inquiry | Service Inquiry | Appointment Request | Site Visit Request | Pricing Request | Follow-up | Complaint | General Question | Purchase Ready | Information Gathering | Existing Customer | Other>",
  "confidence": <float 0.0-1.0 for the intent classification>,
  "budget": {{
    "value": "<extracted budget string or null>",
    "confidence": <float 0.0-1.0>
  }},
  "timeline": {{
    "value": "<extracted timeline string or null>",
    "confidence": <float 0.0-1.0>
  }},
  "interest": {{
    "value": "<property type or service of interest or null>",
    "confidence": <float 0.0-1.0>
  }},
  "location": {{
    "value": "<preferred location or null>",
    "confidence": <float 0.0-1.0>
  }},
  "urgency": "<high | medium | low | unknown>",
  "buying_stage": "<Research | Comparing Options | Ready to Schedule | Negotiation | Purchase Ready | Existing Customer | null>",
  "reasoning": "<1-2 sentence explanation of WHY this intent was chosen>",
  "memory_influenced": "<which prior memory facts, if any, influenced this classification. null if memory was empty or not relevant>",
  "detected_keywords": ["<keyword1>", "<keyword2>"]
}}

Rules:
- Set null for fields that cannot be determined from the conversation
- confidence reflects certainty from THIS conversation — not assumptions
- buying_stage should reflect the customer's position in the purchase journey
- detected_keywords should list exact words or phrases from the message that drove the intent classification
- Return ONLY the JSON object"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise intent classification system. Return only valid JSON.",
                },
                {"role": "user", "content": extraction_prompt},
            ],
            max_tokens=400,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content.strip()
        result = json.loads(raw_text)

        logger.debug(
            "intent_api_call_completed",
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        return result

    except Exception as exc:
        if throw_on_error:
            raise exc
        logger.error(
            "intent_extraction_api_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        # We need to raise it so the pipeline catches it and queues the retry
        raise exc


def _map_intent_to_action(
    intent: IntentCategory,
    urgency: UrgencyLevel,
    buying_stage: Optional[str],
) -> str:
    """
    Pure function — maps (intent, urgency, buying_stage) → recommended action string.

    This is the workflow recommendation engine. Phase 5 (Scheduling) and
    Phase 6 (Follow-up) consume next_action to trigger automation.
    """
    # Purchase-critical intents — always highest priority
    if intent == IntentCategory.purchase_ready:
        return NextAction.NOTIFY_SALES_TEAM

    if intent == IntentCategory.site_visit_request:
        return NextAction.SCHEDULE_SITE_VISIT

    if intent == IntentCategory.appointment_request:
        return NextAction.CONFIRM_APPOINTMENT

    if intent == IntentCategory.complaint:
        return NextAction.ESCALATE_TO_HUMAN

    # Pricing intent — urgency-sensitive
    if intent == IntentCategory.pricing_request:
        if urgency == UrgencyLevel.high:
            return NextAction.SHARE_PRICING_IMMEDIATELY
        return NextAction.SEND_PRICING_BROCHURE

    # Product/service inquiry
    if intent in (IntentCategory.product_inquiry, IntentCategory.service_inquiry):
        return NextAction.SHARE_PRODUCT_DETAILS

    # Information gathering / long timeline — create a future follow-up
    if intent == IntentCategory.information_gathering:
        return NextAction.CREATE_FOLLOWUP

    # Buying stage override for purchase-ready signal in any intent
    if buying_stage == "Purchase Ready":
        return NextAction.NOTIFY_SALES_TEAM

    if intent == IntentCategory.general_question:
        return NextAction.ANSWER_AND_QUALIFY

    # Follow-up, existing customer, other
    return NextAction.CONTINUE_CONVERSATION


def _safe_intent(raw: str) -> IntentCategory:
    """Parse intent string to enum, defaulting to 'other' on unknown values."""
    for member in IntentCategory:
        if member.value.lower() == str(raw).lower():
            return member
    logger.warning("unknown_intent_value", raw=raw, fallback="other")
    return IntentCategory.other


def _safe_urgency(raw: str) -> UrgencyLevel:
    """Parse urgency string to enum, defaulting to 'unknown'."""
    for member in UrgencyLevel:
        if member.value.lower() == str(raw).lower():
            return member
    return UrgencyLevel.unknown
