"""
Pipeline Stage 3 — Memory Injection (Phase 2 stub)

Phase 1: Returns empty list — no memory context injected.
Phase 2: Replace get_memory_context() implementation in domain/memory/service.py.
         This file (pipeline/memory.py) never changes — it only calls the service.
"""

from app.domain.memory.service import get_memory_context
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def inject_memory(customer_phone: str) -> list[dict]:
    """
    Retrieve memory context for this customer and return as
    OpenAI-compatible message dicts.

    Phase 1: Returns []
    Phase 2: Returns summarized customer history from memory store.

    The returned list is prepended to conversation history before
    the AI call, giving the model customer context without re-reading
    the entire message archive.
    """
    context = await get_memory_context(customer_phone)

    logger.debug(
        "memory_stage_called",
        phone=customer_phone,
        context_items=len(context),
    )

    return context
