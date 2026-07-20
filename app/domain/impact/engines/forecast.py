from typing import List, Dict, Any
from app.domain.impact.models import ValueAttribution

class ForecastEngine:
    """
    Projects current performance into future savings/revenue based on 
    the rate of impact generated over the recent period.
    """

    @classmethod
    def generate_quarterly_forecast(cls, recent_attributions: List[ValueAttribution], days_in_period: int) -> float:
        """
        Calculates projected financial savings for a full quarter (90 days)
        based on the average daily savings in the recent period.
        """
        if not recent_attributions or days_in_period <= 0:
            return 0.0
            
        total_recent_impact = sum([a.estimated_financial_value for a in recent_attributions])
        daily_average = total_recent_impact / days_in_period
        
        projected_quarterly = daily_average * 90
        return round(projected_quarterly, 2)
