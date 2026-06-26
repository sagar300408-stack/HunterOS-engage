"""
memory_service — Customer memory management.

Public API (stable — no later phase queries the DB directly):
    get_customer_memory(session, customer_id)  -> CustomerMemory | None
    get_or_create_memory(session, customer_id) -> CustomerMemory
    update_customer_memory(session, customer_id, conversation_history, ai_response, trigger)
    build_ai_context(session, customer_id, customer_name) -> list[dict]
    append_memory_event(session, customer_id, event_type, payload) -> CustomerMemoryEvent

Internal helpers:
    _should_update_memory(message_count, ai_response, interval) -> bool
    _snapshot_memory_version(session, memory) -> None
    _extract_memory_with_ai(conversation_history, current_memory) -> dict
    _detect_significant_fact(ai_response) -> bool

Design:
    - Memory is updated every N messages (configurable) OR immediately when
      a significant business fact is detected in the AI response.
    - Before every update the current state is snapped to customer_memory_versions.
    - All AI extractions carry confidence scores. Only facts >= 0.85 enter AI context.
    - The AI context is injected as a system message list in a fixed 4-block order:
        Profile → Structured Memory → Rolling Summary → (recent msgs handled by pipeline)
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.memory.models import (
    CustomerMemory,
    CustomerMemoryEvent,
    CustomerMemoryVersion,
    MemoryEventType,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Facts that trigger an immediate memory update regardless of message count
_SIGNIFICANT_FACT_KEYWORDS = [
    # Budget signals
    "lakh", "lakhs", "₹", "crore", "budget", "afford", "price range",
    "usd", "dollar", "$", "inr", "rs.", "rupee",
    # Timeline signals
    "months", "weeks", "years", "immediate", "asap", "urgently",
    "planning to", "looking to buy", "want to buy", "ready to",
    # Interest signals
    "interested in", "looking for", "want a", "need a",
    "apartment", "villa", "plot", "office", "flat", "bhk",
    "commercial", "residential", "warehouse",
    # Location signals
    "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai",
    "area", "location", "neighbourhood", "north", "south",
    # Appointment signals
    "appointment", "visit", "meeting", "schedule", "call me",
    "available", "free on",
]

# Confidence threshold for injecting facts into AI context
_CONFIDENCE_THRESHOLD_AUTO = 0.85


# ── Public API ────────────────────────────────────────────────────────────────

async def get_customer_memory(
    session: AsyncSession,
    customer_id: UUID,
) -> Optional[CustomerMemory]:
    """Return the current CustomerMemory row, or None if not yet created."""
    result = await session.execute(
        select(CustomerMemory).where(CustomerMemory.customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_memory(
    session: AsyncSession,
    customer_id: UUID,
) -> CustomerMemory:
    """
    Return the CustomerMemory row, creating an empty one if absent.
    Safe to call on every message — idempotent.
    """
    memory = await get_customer_memory(session, customer_id)

    if not memory:
        memory = CustomerMemory(
            customer_id=customer_id,
            summary=None,
            structured_data={},
            message_count=0,
        )
        session.add(memory)
        await session.flush()
        logger.info("customer_memory_created", customer_id=str(customer_id))

    return memory


async def build_ai_context(
    session: AsyncSession,
    customer_id: UUID,
    customer_name: Optional[str] = None,
) -> list[dict]:
    """
    Build the 4-block AI context prepended before every OpenAI call.

    Returns an ordered list of OpenAI-compatible system message dicts:
        Block 1 — Customer Profile
        Block 2 — Structured Memory (high-confidence facts only)
        Block 3 — Rolling Summary (if exists)

    Recent conversation messages are added separately by the pipeline.
    Returns [] for brand-new customers with no memory yet.
    """
    memory = await get_customer_memory(session, customer_id)

    if not memory or (not memory.summary and not memory.structured_data):
        logger.debug(
            "memory_context_empty",
            customer_id=str(customer_id),
            reason="no_memory_yet",
        )
        return []

    context_blocks: list[dict] = []

    # ── Block 1: Customer Profile ─────────────────────────────────────────────
    profile_parts = []
    if customer_name:
        profile_parts.append(f"Customer name: {customer_name}")
    profile_parts.append(f"Total interactions: {memory.message_count}")

    context_blocks.append({
        "role": "system",
        "content": "CUSTOMER PROFILE:\n" + "\n".join(profile_parts),
    })

    # ── Block 2: Structured Memory (high-confidence facts only) ───────────────
    structured = memory.structured_data or {}
    fact_lines = []

    # Budget
    budget = structured.get("budget")
    if budget and isinstance(budget, dict):
        if budget.get("confidence", 0) >= _CONFIDENCE_THRESHOLD_AUTO:
            fact_lines.append(f"- Budget: {budget['value']}")

    # Timeline
    timeline = structured.get("timeline")
    if timeline and isinstance(timeline, dict):
        if timeline.get("confidence", 0) >= _CONFIDENCE_THRESHOLD_AUTO:
            fact_lines.append(f"- Purchase timeline: {timeline['value']}")

    # Preferred location
    location = structured.get("preferred_location")
    if location and isinstance(location, dict):
        if location.get("confidence", 0) >= _CONFIDENCE_THRESHOLD_AUTO:
            fact_lines.append(f"- Preferred location: {location['value']}")

    # Interests
    interests = structured.get("interests", [])
    if isinstance(interests, list):
        high_conf_interests = [
            i["value"] for i in interests
            if isinstance(i, dict) and i.get("confidence", 0) >= _CONFIDENCE_THRESHOLD_AUTO
        ]
        if high_conf_interests:
            fact_lines.append(f"- Interests: {', '.join(high_conf_interests)}")

    if fact_lines:
        context_blocks.append({
            "role": "system",
            "content": "KNOWN CUSTOMER FACTS (high-confidence):\n" + "\n".join(fact_lines),
        })

    # ── Block 3: Rolling Summary ──────────────────────────────────────────────
    if memory.summary:
        context_blocks.append({
            "role": "system",
            "content": f"CONVERSATION HISTORY SUMMARY:\n{memory.summary}",
        })

    logger.debug(
        "memory_context_built",
        customer_id=str(customer_id),
        blocks=len(context_blocks),
        has_summary=bool(memory.summary),
        fact_count=len(fact_lines),
    )

    return context_blocks


async def update_customer_memory(
    session: AsyncSession,
    customer_id: UUID,
    conversation_history: list[dict],
    ai_response: str,
    trigger: str = "interval",
) -> None:
    """
    Update the customer memory after a significant interaction.

    Flow:
        1. Get/create memory row
        2. Snapshot current state to customer_memory_versions (immutable archive)
        3. Call OpenAI extraction prompt to generate new summary + structured fields
        4. Write updated memory
        5. Append memory_summarized event

    Args:
        session:              Active async database session.
        customer_id:          UUID of the customer.
        conversation_history: Recent messages as OpenAI dicts (for extraction context).
        ai_response:          The latest AI response (included in context).
        trigger:              "interval" | "significant_fact"
    """
    memory = await get_or_create_memory(session, customer_id)

    # ── 1. Snapshot current state before overwriting ───────────────────────────
    if memory.summary or memory.structured_data:
        await _snapshot_memory_version(session, memory, customer_id)

    # ── 2. Extract new summary + structured data via OpenAI ───────────────────
    extracted = await _extract_memory_with_ai(
        conversation_history=conversation_history,
        current_summary=memory.summary,
        current_structured=memory.structured_data or {},
    )

    # ── 3. Write updated memory ────────────────────────────────────────────────
    memory.summary = extracted.get("summary", memory.summary)
    memory.structured_data = extracted.get("structured_data", memory.structured_data)
    memory.last_updated = datetime.now(timezone.utc)
    await session.flush()

    # ── 4. Emit events for each detected significant fact ─────────────────────
    structured = extracted.get("structured_data", {})

    if structured.get("budget"):
        await append_memory_event(
            session, customer_id, MemoryEventType.budget_detected,
            {"value": structured["budget"].get("value"),
             "confidence": structured["budget"].get("confidence")},
        )
    if structured.get("timeline"):
        await append_memory_event(
            session, customer_id, MemoryEventType.timeline_detected,
            {"value": structured["timeline"].get("value"),
             "confidence": structured["timeline"].get("confidence")},
        )
    if structured.get("interests"):
        await append_memory_event(
            session, customer_id, MemoryEventType.interest_detected,
            {"interests": structured["interests"]},
        )
    if structured.get("preferred_location"):
        await append_memory_event(
            session, customer_id, MemoryEventType.location_detected,
            {"value": structured["preferred_location"].get("value"),
             "confidence": structured["preferred_location"].get("confidence")},
        )

    # ── 5. Append memory_summarized event ─────────────────────────────────────
    await append_memory_event(
        session, customer_id, MemoryEventType.memory_summarized,
        {"trigger": trigger, "message_count": memory.message_count},
    )

    logger.info(
        "customer_memory_updated",
        customer_id=str(customer_id),
        trigger=trigger,
        message_count=memory.message_count,
        has_summary=bool(memory.summary),
    )


async def append_memory_event(
    session: AsyncSession,
    customer_id: UUID,
    event_type: MemoryEventType,
    payload: Optional[dict[str, Any]] = None,
) -> CustomerMemoryEvent:
    """
    Append an event to the customer_memory_events log.

    This is the only write method for the event log — append-only, never updated.
    Called by customer_service, memory_service, and conversation_service.
    """
    event = CustomerMemoryEvent(
        customer_id=customer_id,
        event_type=event_type,
        payload=payload,
        created_at=datetime.now(timezone.utc),
    )
    session.add(event)
    await session.flush()

    logger.debug(
        "memory_event_appended",
        customer_id=str(customer_id),
        event_type=event_type.value,
    )

    return event


# ── Internal helpers ──────────────────────────────────────────────────────────

def _should_update_memory(
    message_count: int,
    ai_response: str,
    interval: int = 5,
) -> tuple[bool, str]:
    """
    Pure function — no DB access.

    Returns (should_update: bool, trigger: str).

    Triggers:
        1. message_count is a multiple of interval
        2. Significant business fact detected in ai_response (keyword scan)
    """
    if message_count > 0 and message_count % interval == 0:
        return True, "interval"

    if _detect_significant_fact(ai_response):
        return True, "significant_fact"

    return False, ""


def _detect_significant_fact(text: str) -> bool:
    """
    Lightweight keyword scan — no OpenAI call.
    Returns True if the text contains a significant business signal.
    """
    lower = text.lower()
    return any(keyword in lower for keyword in _SIGNIFICANT_FACT_KEYWORDS)


async def _snapshot_memory_version(
    session: AsyncSession,
    memory: CustomerMemory,
    customer_id: UUID,
) -> None:
    """
    Write the current memory state to customer_memory_versions before overwriting.
    Enables rollback and full audit trail.
    """
    version = CustomerMemoryVersion(
        customer_id=customer_id,
        summary=memory.summary,
        structured_data=memory.structured_data,
        created_at=datetime.now(timezone.utc),
    )
    session.add(version)
    await session.flush()

    await append_memory_event(
        session, customer_id, MemoryEventType.memory_version_created,
        {"version_id": str(version.id)},
    )

    logger.debug(
        "memory_version_created",
        customer_id=str(customer_id),
        version_id=str(version.id),
    )


async def _extract_memory_with_ai(
    conversation_history: list[dict],
    current_summary: Optional[str],
    current_structured: dict,
) -> dict:
    """
    Call OpenAI with a compact extraction prompt to generate:
        - An updated rolling summary
        - Confidence-scored structured fields (budget, timeline, location, interests)

    Uses a dedicated low-temperature call separate from the main chat response.
    Returns a dict matching UpdateMemoryDTO structure.
    """
    from app.integrations.openai.client import get_openai_client
    from app.config import get_settings

    settings = get_settings()
    client = get_openai_client()

    # Format conversation context for extraction
    conversation_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in conversation_history[-20:]  # last 20 messages max
    )

    current_summary_text = current_summary or "None yet."
    current_structured_text = json.dumps(current_structured, ensure_ascii=False) if current_structured else "{}"

    extraction_prompt = f"""You are a memory extraction system for a real estate sales AI assistant.

Your task: Analyse the conversation below and extract/update customer information.

CURRENT MEMORY SUMMARY:
{current_summary_text}

CURRENT STRUCTURED DATA:
{current_structured_text}

RECENT CONVERSATION:
{conversation_text}

Return a JSON object with EXACTLY this structure (no extra keys):
{{
  "summary": "A concise 2-4 sentence narrative describing who this customer is, what they are looking for, their key requirements, and where they are in their buying journey. Write in third person.",
  "structured_data": {{
    "budget": {{"value": "extracted budget or null", "confidence": 0.0}},
    "timeline": {{"value": "extracted timeline or null", "confidence": 0.0}},
    "preferred_location": {{"value": "extracted location or null", "confidence": 0.0}},
    "interests": [
      {{"value": "interest description", "confidence": 0.0}}
    ]
  }}
}}

Rules:
- confidence is a float 0.0–1.0 reflecting how certain you are from the conversation
- If a field cannot be determined, set value to null and confidence to 0.0
- Do NOT invent information not present in the conversation
- Merge new information with existing structured_data — do not discard previous facts unless contradicted
- Return ONLY the JSON object, no explanation, no markdown code fences"""

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a precise data extraction system. Return only valid JSON."},
                {"role": "user", "content": extraction_prompt},
            ],
            max_tokens=600,
            temperature=0.1,  # Low temperature for deterministic extraction
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        extracted = json.loads(raw)

        logger.info(
            "memory_extraction_completed",
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        return extracted

    except (json.JSONDecodeError, KeyError, Exception) as exc:
        logger.error(
            "memory_extraction_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        # Return existing memory unchanged on failure — never corrupt state
        return {
            "summary": current_summary,
            "structured_data": current_structured,
        }


# ── Legacy stub compatibility (called by pipeline/memory.py) ──────────────────
# This function is retained for backward compatibility with the Phase 1 pipeline stub.
# The pipeline/memory.py inject_memory() function calls this during Phase 1.
# Phase 2 replaces the inject_memory() call with build_ai_context() directly.

async def get_memory_context(customer_phone: str) -> list[dict]:
    """
    Phase 1 stub — preserved for import compatibility.
    Phase 2 callers use build_ai_context(session, customer_id) instead.
    """
    logger.debug(
        "get_memory_context_legacy_stub_called",
        phone=customer_phone,
        note="Phase 2 uses build_ai_context() directly",
    )
    return []
