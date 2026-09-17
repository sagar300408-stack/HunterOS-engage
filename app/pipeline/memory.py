"""
Pipeline Stage 3 — Memory Injection (Phase 2 — Activated)

Reads the structured memory_payload from the CQRS CustomerMemory aggregate
and converts it into an OpenAI-compatible system message block.
"""

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers.models import Customer
from app.domain.memory.service import MemoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def inject_memory(
    session: AsyncSession,
    customer: Customer,
) -> list[dict]:
    """
    Retrieve the structured customer memory and return as OpenAI-compatible
    message dicts to prepend to conversation history.

    Returns [] for brand-new customers with no memory yet.

    Args:
        session:  Active async database session.
        customer: The Customer ORM object from Stage 2 of the pipeline.

    Returns:
        List of OpenAI-compatible system message dicts.
    """
    mem_svc = MemoryService()
    memory = await mem_svc.get_customer_memory(
        customer.id,
        session=session,
        workspace_id=customer.workspace_id,
    )

    if not memory or not memory.memory_payload:
        logger.debug(
            "memory_stage_skipped_no_memory",
            customer_id=str(customer.id),
        )
        return []

    payload = memory.memory_payload
    # Build a compact summary string from the structured payload
    personal = payload.get("personal_info", {})
    financial = payload.get("financial_info", {})
    property_info = payload.get("property_info", {})
    journey = payload.get("journey_snapshot", {})

    lines = []
    if personal.get("full_name"):
        lines.append(f"Customer name: {personal['full_name']}")
    if financial.get("budget_min") or financial.get("budget_max"):
        lines.append(f"Budget: {financial.get('budget_min', '?')} – {financial.get('budget_max', '?')} {financial.get('currency', 'INR')}")
    if property_info.get("property_types"):
        lines.append(f"Interested in: {', '.join(property_info['property_types'])}")
    if property_info.get("preferred_locations"):
        lines.append(f"Preferred locations: {', '.join(property_info['preferred_locations'])}")
    if journey.get("current_stage"):
        lines.append(f"Journey stage: {journey['current_stage']}")

    if not lines:
        logger.debug(
            "memory_stage_completed_empty_payload",
            customer_id=str(customer.id),
        )
        return []

    context_text = "CUSTOMER MEMORY PROFILE:\n" + "\n".join(f"- {l}" for l in lines)

    context = [{"role": "system", "content": context_text}]

    logger.debug(
        "memory_stage_completed",
        customer_id=str(customer.id),
        phone=customer.phone,
        context_blocks=len(context),
    )

    return context
