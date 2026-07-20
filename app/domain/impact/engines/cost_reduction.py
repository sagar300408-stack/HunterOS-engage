from typing import Tuple
from app.domain.impact.models import ImpactEvent

class CostReductionCalculator:
    """
    Estimates hard operational cost reductions (outside of raw time savings).
    """

    @classmethod
    def calculate(cls, event: ImpactEvent) -> Tuple[float, str]:
        payload = event.payload
        
        if event.event_type == "duplicate.task.prevented":
            return payload.get("cost_saved", 0.0), "cost_saved"
            
        elif event.event_type == "sla.penalty.avoided":
            return payload.get("penalty_value", 0.0), "penalty_saved"
            
        return 0.0, "cost_reduction"
