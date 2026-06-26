"""
Pipeline Stage 5 — Follow-up Scheduling (Phase 4 stub)

Phase 1: No-op — returns immediately.
Phase 4: Replace the body of schedule_followup() to:
  - Analyze the AI response for signals (booking intent, urgency, unresolved issue)
  - Schedule WhatsApp follow-up messages via a task queue (Celery / APScheduler)
  - Trigger CRM pipeline stage changes
  - Escalate to human agents if needed

No other files change when Phase 4 is activated.
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def schedule_followup(
    conversation_id: str,
    from_phone: str,
    ai_response: str,
) -> None:
    """
    Phase 1: No-op.
    Phase 4: Analyze response signals and schedule follow-up actions.

    Args:
        conversation_id: Active conversation UUID string.
        from_phone:      Customer phone number.
        ai_response:     The AI's reply text (analyzed for intent signals).
    """
    logger.debug(
        "followup_stage_stub",
        phase="1",
        conversation_id=conversation_id,
        phone=from_phone,
    )
    return None
