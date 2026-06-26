"""
memory_service — Customer memory context for AI conversations.

Phase 1: Returns empty list (no memory injection).
Phase 2: Replace implementation body only.
         The function signature NEVER changes — no other file is touched.

Phase 2 implementation will:
  - Retrieve the customer's past conversation summaries
  - Inject relevant product preferences, past complaints, and purchase history
  - Optionally use a vector store (e.g. Pinecone, pgvector) for semantic recall
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_memory_context(customer_phone: str) -> list[dict]:
    """
    Returns memory context to prepend to the AI conversation history.

    Phase 1: Returns [] — no memory injected.
    Phase 2: Returns a list of OpenAI-compatible message dicts
             representing summarized customer history.

    Example Phase 2 return:
        [
            {
                "role": "system",
                "content": "This customer previously inquired about 3BHK apartments
                            in Baner and expressed urgency to move within 2 months."
            }
        ]
    """
    logger.debug(
        "memory_service_called",
        phone=customer_phone,
        phase="1_stub",
        injected_items=0,
    )
    return []
