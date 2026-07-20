from typing import Tuple
from app.domain.impact.models import ImpactEvent

class ProductivityCalculator:
    """
    Calculates improvements in team productivity.
    """

    @classmethod
    def calculate(cls, event: ImpactEvent) -> Tuple[float, str]:
        payload = event.payload
        
        if event.event_type == "task.completed":
            return 1.0, "tasks_completed"
            
        elif event.event_type == "meeting.scheduled":
            return 1.0, "meetings_scheduled"
            
        return 0.0, "productivity_units"
