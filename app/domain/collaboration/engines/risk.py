from typing import Tuple, List, Dict, Any
from app.domain.collaboration.models import ActionableIntent, RiskLevel

class RiskAssessmentEngine:
    """
    Calculates the business risk of an intent, elevated by operational context.
    """
    
    BASE_RISK_MAP = {
        "schedule_meeting": RiskLevel.LOW,
        "assign_lead": RiskLevel.LOW,
        "send_followup": RiskLevel.LOW,
        "generate_proposal": RiskLevel.MEDIUM,
        "approve_discount": RiskLevel.HIGH,
        "escalate_complaint": RiskLevel.HIGH,
        "approve_refund": RiskLevel.CRITICAL
    }

    @classmethod
    def evaluate(cls, intent: ActionableIntent, enriched_context: Dict[str, Any]) -> Tuple[RiskLevel, List[str]]:
        """
        Returns (RiskLevel, list_of_risk_factors).
        """
        factors = []
        base_risk = cls.BASE_RISK_MAP.get(intent.intent_type, RiskLevel.MEDIUM)
        current_risk = base_risk
        
        factors.append(f"Base risk for {intent.intent_type} is {base_risk.value}")

        # Elevate risk based on context
        if enriched_context.get("is_vip") or enriched_context.get("is_high_value"):
            factors.append("Risk elevated to CRITICAL due to VIP or High Value Context")
            current_risk = RiskLevel.CRITICAL
            
        if intent.intent_type == "approve_discount" and float(enriched_context.get("discount_amount", 0)) > 50000:
            factors.append("Risk elevated to CRITICAL due to discount > 50,000")
            current_risk = RiskLevel.CRITICAL

        return current_risk, factors
