from app.domain.impact.models import FinancialConfig, ImpactCategory

class ROICalculator:
    """
    Converts raw operational metrics into estimated financial value.
    """

    @classmethod
    def calculate_financial_value(
        cls, 
        category: ImpactCategory, 
        raw_value: float, 
        config: FinancialConfig
    ) -> float:
        
        if category == ImpactCategory.TIME_SAVINGS:
            # raw_value is minutes saved
            hours_saved = raw_value / 60.0
            return hours_saved * config.average_hourly_cost
            
        elif category == ImpactCategory.REVENUE_PROTECTION:
            # raw_value is assumed to be the deal value protected
            return raw_value
            
        elif category == ImpactCategory.OPPORTUNITY_RECOVERY:
            # raw_value is number of opportunities recovered
            return raw_value * config.average_deal_value * config.conversion_rate
            
        elif category == ImpactCategory.COST_REDUCTION:
            # raw_value is direct cost reduction
            return raw_value
            
        return 0.0
