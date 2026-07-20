from typing import Dict, Any, Tuple
from app.domain.impact.models import ImpactEvent, ImpactCategory

from app.domain.impact.engines.time_savings import TimeSavingsCalculator
from app.domain.impact.engines.productivity import ProductivityCalculator
from app.domain.impact.engines.revenue import RevenueProtectionCalculator
from app.domain.impact.engines.opportunity import OpportunityRecoveryCalculator
from app.domain.impact.engines.cost_reduction import CostReductionCalculator

class ValueAttributionEngine:
    """
    Categorizes the raw metric and attributes it to the correct business dimension.
    """

    @classmethod
    def attribute(cls, event: ImpactEvent) -> Tuple[ImpactCategory, float, str]:
        """
        Returns (ImpactCategory, raw_metric_value, raw_metric_name).
        """
        # A simple rules engine to map events to their primary impact category.
        
        if event.event_type.startswith("task.") or event.event_type.startswith("approval."):
            val, name = TimeSavingsCalculator.calculate(event)
            return ImpactCategory.TIME_SAVINGS, val, name
            
        if event.event_type in ["meeting.scheduled", "task.completed"]:
            val, name = ProductivityCalculator.calculate(event)
            return ImpactCategory.PRODUCTIVITY, val, name
            
        if event.event_type in ["sla.breach.prevented", "escalation.prevented"]:
            val, name = RevenueProtectionCalculator.calculate(event)
            return ImpactCategory.REVENUE_PROTECTION, val, name
            
        if event.event_type in ["lead.recovered", "proposal.completed.delayed"]:
            val, name = OpportunityRecoveryCalculator.calculate(event)
            return ImpactCategory.OPPORTUNITY_RECOVERY, val, name
            
        if event.event_type in ["duplicate.task.prevented", "sla.penalty.avoided"]:
            val, name = CostReductionCalculator.calculate(event)
            return ImpactCategory.COST_REDUCTION, val, name
            
        return ImpactCategory.STRATEGIC, 1.0, "strategic_event"
