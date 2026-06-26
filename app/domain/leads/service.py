"""
lead_service — Lead qualification and stage management.

Phase 3 partial activation:
    qualify_lead() — reads latest IntentHistory and syncs buying_stage to customer profile.

Phase 5 will add:
    create_lead()      — CRM record creation and sync
    update_lead_stage() — full pipeline stage management

No other files change when Phase 5 activates these methods.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import get_logger

logger = get_logger(__name__)


async def qualify_lead(
    session: AsyncSession,
    customer_id: UUID,
    conversation_id: UUID,
) -> Optional[dict]:
    """
    Phase 3: Evaluate the customer's current lead quality based on latest intent.

    Reads the most recent IntentHistory row, evaluates key qualification signals,
    and returns a structured qualification summary consumed by Phase 5/6 automation.

    Qualification signals:
        - buying_stage (Research → Purchase Ready)
        - urgency level
        - presence of budget
        - presence of timeline
        - intent category

    Returns None if no intent history exists yet.
    """
    from app.domain.intent import service as intent_service

    latest = await intent_service.get_latest_intent(session, customer_id)

    if not latest:
        logger.debug(
            "qualify_lead_no_intent_found",
            customer_id=str(customer_id),
        )
        return None

    # ── Compute a simple qualification score (0–100) ──────────────────────────
    score = 0

    # Buying stage weight
    stage_scores = {
        "Purchase Ready":       50,
        "Negotiation":          40,
        "Ready to Schedule":    30,
        "Comparing Options":    20,
        "Research":             10,
        "Existing Customer":    15,
    }
    score += stage_scores.get(latest.buying_stage or "", 0)

    # Urgency weight
    urgency_scores = {"high": 25, "medium": 15, "low": 5, "unknown": 0}
    score += urgency_scores.get(str(latest.urgency), 0)

    # Budget present
    if latest.budget:
        score += 15

    # Timeline present
    if latest.timeline:
        score += 10

    qualification = {
        "customer_id":   str(customer_id),
        "score":         score,
        "grade":         _score_to_grade(score),
        "buying_stage":  latest.buying_stage,
        "urgency":       str(latest.urgency),
        "intent":        str(latest.detected_intent),
        "budget":        latest.budget,
        "timeline":      latest.timeline,
        "next_action":   latest.next_action,
        "qualified":     score >= 30,
    }

    logger.info(
        "lead_qualified",
        customer_id=str(customer_id),
        score=score,
        grade=qualification["grade"],
        qualified=qualification["qualified"],
    )

    return qualification


async def create_lead(
    session: AsyncSession,
    customer_id: UUID,
    source: str = "whatsapp",
) -> None:
    """
    Phase 5: Create a lead record and sync to CRM.
    Currently a no-op — activated in Phase 5.
    """
    logger.debug(
        "lead_service_create_stub",
        customer_id=str(customer_id),
        source=source,
        note="Phase 5 will implement CRM sync",
    )


async def update_lead_stage(
    session: AsyncSession,
    lead_id: str,
    stage: str,
) -> None:
    """
    Phase 5: Move a lead through CRM pipeline stages.
    Currently a no-op — activated in Phase 5.
    """
    logger.debug(
        "lead_service_update_stage_stub",
        lead_id=lead_id,
        stage=stage,
        note="Phase 5 will implement pipeline stage management",
    )


def _score_to_grade(score: int) -> str:
    """Convert numeric score to letter grade for human readability."""
    if score >= 70:
        return "A"
    if score >= 50:
        return "B"
    if score >= 30:
        return "C"
    if score >= 15:
        return "D"
    return "F"
