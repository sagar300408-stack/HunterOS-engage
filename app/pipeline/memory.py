"""
Pipeline Stage 3 — Memory Injection (Phase 2 — Activated)

Phase 1: Returned empty list — no memory context injected.
Phase 2: Calls build_ai_context() to assemble the 4-block customer context.

This file's interface is intentionally thin — it only orchestrates the call
to the domain service. All business logic lives in domain/memory/service.py.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.customers.models import Customer
from app.domain.memory import service as memory_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def inject_memory(
    session: AsyncSession,
    customer: Customer,
) -> list[dict]:
    """
    Retrieve the 4-block memory context for this customer and return as
    OpenAI-compatible message dicts to prepend to conversation history.

    Phase 2: Returns [profile_block, facts_block, summary_block] for returning
             customers. Returns [] for brand-new customers with no memory yet.

    The returned list is prepended to conversation history before the AI call,
    giving the model full customer context without re-sending the entire
    message archive.

    Args:
        session:  Active async database session.
        customer: The Customer ORM object from Stage 2 of the pipeline.

    Returns:
        List of OpenAI-compatible system message dicts.
    """
    context = await memory_service.build_ai_context(
        session=session,
        customer_id=customer.id,
        customer_name=customer.name,
    )

    logger.debug(
        "memory_stage_completed",
        customer_id=str(customer.id),
        phone=customer.phone,
        context_blocks=len(context),
    )

    return context
