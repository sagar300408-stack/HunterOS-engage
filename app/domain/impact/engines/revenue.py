from typing import Tuple
from app.domain.impact.models import ImpactEvent

class RevenueProtectionCalculator:
    """
    Calculates estimated revenue protected by preventing friction.
    """

    @classmethod
    def calculate(cls, event: ImpactEvent) -> Tuple[float, str]:
        payload = event.payload
        
        if event.event_type == "sla.breach.prevented":
            return payload.get("at_risk_value", 0.0), "deal_value_protected"
            
        elif event.event_type == "escalation.prevented":
            return payload.get("deal_value", 0.0), "deal_value_protected"
            
        return 0.0, "revenue_protected"
