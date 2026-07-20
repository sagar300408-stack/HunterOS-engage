from typing import Tuple, List
from app.domain.collaboration.models import ActionableIntent

class ExceptionHandlingEngine:
    """
    Detects if an actionable intent contains factors that immediately disqualify it from AI automation.
    Examples: Legal threats, angry sentiment, fraud indicators.
    """
    
    # In a real system, these would use NLP, sentiment analysis, or pattern matching.
    LEGAL_KEYWORDS = ["sue", "lawyer", "legal", "court", "breach"]
    ANGRY_KEYWORDS = ["angry", "upset", "furious", "unacceptable", "terrible"]
    FRAUD_KEYWORDS = ["fraud", "scam", "stolen", "unauthorized"]

    @classmethod
    def evaluate(cls, intent: ActionableIntent) -> Tuple[bool, List[str]]:
        """
        Returns (has_exception, list_of_exception_reasons).
        If has_exception is True, the task must be routed to a Human.
        """
        exceptions = []
        
        # We assume context_data might have some text like "customer_message" or "description"
        text_to_scan = str(intent.context_data.get("customer_message", "")).lower()
        text_to_scan += " " + str(intent.context_data.get("description", "")).lower()

        if any(keyword in text_to_scan for keyword in cls.LEGAL_KEYWORDS):
            exceptions.append("Legal risk detected")
            
        if any(keyword in text_to_scan for keyword in cls.ANGRY_KEYWORDS):
            exceptions.append("High negative sentiment (angry customer)")
            
        if any(keyword in text_to_scan for keyword in cls.FRAUD_KEYWORDS):
            exceptions.append("Potential fraud indicator detected")
            
        # Exception type specific hardstops
        if intent.intent_type == "approve_refund" and intent.context_data.get("is_disputed", False):
             exceptions.append("Disputed refund must be handled manually")
             
        return len(exceptions) > 0, exceptions
