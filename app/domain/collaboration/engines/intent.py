from typing import Optional, Dict, Any
import uuid
from app.domain.collaboration.models import ActionableIntent

class IntentEngine:
    """
    Filters raw business events and extracts 'Actionable Intents'.
    Observations (e.g., 'Lead Viewed Website') are ignored.
    Executions (e.g., 'Approve Discount', 'Schedule Meeting') produce an ActionableIntent.
    """
    
    ACTIONABLE_TYPES = {
        "schedule_meeting",
        "approve_discount",
        "assign_lead",
        "generate_proposal",
        "send_followup",
        "escalate_complaint",
        "approve_refund"
    }

    @classmethod
    def evaluate(cls, workspace_id: uuid.UUID, event_type: str, payload: Dict[str, Any]) -> Optional[ActionableIntent]:
        """
        If the event is an actionable intent, return a populated ActionableIntent model.
        Otherwise, return None (meaning no collaboration routing required).
        """
        if event_type not in cls.ACTIONABLE_TYPES:
            return None
            
        return ActionableIntent(
            workspace_id=workspace_id,
            intent_type=event_type,
            context_data=payload
        )
