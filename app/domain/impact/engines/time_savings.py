from typing import Tuple, Dict, Any
from app.domain.impact.models import ImpactEvent, FinancialConfig

class TimeSavingsCalculator:
    """
    Calculates operational time saved by HunterOS automations.
    """

    @classmethod
    def calculate(cls, event: ImpactEvent) -> Tuple[float, str]:
        """
        Returns (minutes_saved, raw_metric_name) based on the event payload.
        """
        payload = event.payload
        
        # Example heuristic logic based on event type
        if event.event_type == "task.automated":
            # Assume 15 mins saved per automated task if not specified
            return payload.get("minutes_saved", 15.0), "minutes_saved"
            
        elif event.event_type == "approval.accelerated":
            # E.g. saved from waiting in a queue
            return payload.get("minutes_saved", 30.0), "minutes_saved"
            
        return 0.0, "minutes_saved"
