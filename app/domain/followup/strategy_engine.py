from typing import Optional, List
from uuid import UUID
from app.domain.followup.schemas import StrategyDecision
from app.domain.followup.policy_engine import Policy

def select_strategy(
    reason: str,
    buying_stage: Optional[str],
    health_band: Optional[str],
    follow_up_attempt: int,
    days_since_last_contact: int,
    has_proposal: bool,
    has_budget: bool,
    has_meeting: bool,
    objections_detected: List[str],
    policy: Policy,
    workspace_id: UUID,
) -> StrategyDecision:
    """Selects the best messaging strategy."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[TRACE] Strategy Engine: select_strategy() executed")
    
    if has_proposal and follow_up_attempt == 1:
        return StrategyDecision(
            strategy="proposal_reminder",
            instructions="Gently check if they reviewed the proposal. Offer to answer any questions."
        )
    
    if buying_stage == "Purchase Ready" and follow_up_attempt > 1:
        return StrategyDecision(
            strategy="urgency_followup",
            instructions="Politely emphasize that time is of the essence or ask what is holding them back."
        )
        
    if follow_up_attempt >= 3:
        return StrategyDecision(
            strategy="breakup_email",
            instructions="Politely mention this is your last message for a while, leave the door open."
        )
        
    return StrategyDecision(
        strategy="friendly_checkin",
        instructions="Keep it brief and friendly. Just checking in to see if they need help."
    )
