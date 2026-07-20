from typing import Tuple
from app.domain.impact.models import ImpactEvent

class OpportunityRecoveryCalculator:
    """
    Tracks opportunities that HunterOS recovered.
    """

    @classmethod
    def calculate(cls, event: ImpactEvent) -> Tuple[float, str]:
        payload = event.payload
        
        if event.event_type == "lead.recovered":
            return 1.0, "leads_recovered"
            
        elif event.event_type == "proposal.completed.delayed":
            return 1.0, "proposals_recovered"
            
        return 0.0, "opportunities_recovered"
