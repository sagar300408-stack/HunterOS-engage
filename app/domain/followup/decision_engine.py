from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from app.domain.followup.schemas import FollowUpDecision, FollowUpExplainability

def evaluate(
    customer_id: UUID,
    conversation_id: Optional[UUID],
    last_outgoing_at: Optional[datetime],
    last_incoming_at: Optional[datetime],
    last_followup_sent_at: Optional[datetime],
    followup_attempt_count: int,
    buying_stage: Optional[str],
    urgency: Optional[str],
    has_open_proposal: bool,
    has_confirmed_meeting: bool,
    next_meeting_at: Optional[datetime],
    has_missed_meeting: bool,
    callback_requested: bool,
    approval_pending: bool,
    budget_mentioned: bool,
    budget_paused: bool,
    max_attempts: int,
) -> FollowUpDecision:
    """
    Evaluates whether a lead needs a follow-up.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[TRACE] Decision Engine: evaluate() executed for customer_id: {customer_id}")
    now = datetime.now(tz=timezone.utc)
    factors = {
        "buying_stage": buying_stage,
        "followup_attempts": followup_attempt_count,
        "max_attempts": max_attempts,
    }

    if has_confirmed_meeting and next_meeting_at and next_meeting_at > now:
        # Don't follow up if they have an upcoming meeting, unless it's a reminder
        logger.info(f"[TRACE] Decision Engine returned: abort, reason: Upcoming meeting scheduled")
        return FollowUpDecision(
            should_follow_up=False,
            reason="Upcoming meeting scheduled",
            explainability=FollowUpExplainability(
                policy_applied="Meeting Scheduled",
                decision_reason="Wait for the meeting",
                factors_considered=factors,
                confidence=95
            )
        )

    if followup_attempt_count >= max_attempts:
        logger.info(f"[TRACE] Decision Engine returned: abort, reason: Max follow-up attempts reached")
        return FollowUpDecision(
            should_follow_up=False,
            reason="Max follow-up attempts reached",
            explainability=FollowUpExplainability(
                policy_applied="Max Attempts Rule",
                decision_reason="Exhausted follow-up cadence",
                factors_considered=factors,
                confidence=100
            )
        )

    # Simplified delay logic for demo
    delay_hours = 24
    if buying_stage in ["Purchase Ready", "Negotiation"]:
        delay_hours = 12
    elif buying_stage == "Research":
        delay_hours = 48

    scheduled_for = now
    if last_outgoing_at:
        # Add delay from last contact
        scheduled_for = last_outgoing_at.replace(tzinfo=timezone.utc) + timedelta(hours=delay_hours)
    
    if scheduled_for < now:
        scheduled_for = now

    factors["delay_hours_applied"] = delay_hours

    logger.info(f"[TRACE] Decision Engine returned: schedule, reason: Follow-up due based on cadence, scheduled_for: {scheduled_for}")
    return FollowUpDecision(
        should_follow_up=True,
        reason="Follow-up due based on cadence",
        priority="high" if delay_hours <= 12 else "normal",
        scheduled_for=scheduled_for,
        risk_score=50,
        explainability=FollowUpExplainability(
            policy_applied="Standard Cadence",
            decision_reason="Lead is inactive, follow-up required",
            factors_considered=factors,
            confidence=85
        )
    )
