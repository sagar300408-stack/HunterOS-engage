"""
Pipeline Stage 2 — Intent Classification (Phase 3 stub)

Phase 1: Returns a default pass-through intent. No logic.
Phase 3: Replace the body of classify_intent() with:
  - OpenAI function-calling or a fine-tuned classifier
  - Intent categories: inquiry | complaint | booking | lead | support | other
  - Confidence score and extracted entities
  - Results feed into routing logic (different pipeline branches per intent)

No other files change when Phase 3 is activated.
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def classify_intent(content: str, from_phone: str) -> dict:
    """
    Phase 1: Returns a default general intent.
    Phase 3: Returns structured classification from the intent model.

    Returns:
        {
            "intent":     str,   e.g. "inquiry" | "complaint" | "booking"
            "confidence": float, e.g. 0.95
            "entities":   dict,  e.g. {"property_type": "2BHK", "location": "Baner"}
        }
    """
    logger.debug(
        "intent_stage_stub",
        phase="1",
        from_phone=from_phone,
        content_preview=content[:60],
    )
    return {
        "intent": "general",
        "confidence": 1.0,
        "entities": {},
    }
