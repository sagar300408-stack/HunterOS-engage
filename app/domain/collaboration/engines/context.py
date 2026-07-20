from typing import Tuple, List, Dict, Any
from app.domain.collaboration.models import ActionableIntent

class OperationalContextEngine:
    """
    Evaluates business context variables that affect routing and risk.
    Examples: Customer VIP status, high deal value, strategic project importance.
    """

    VIP_THRESHOLD_VALUE = 1000000 # E.g., 1 Million

    @classmethod
    def evaluate(cls, intent: ActionableIntent) -> Tuple[Dict[str, Any], List[str]]:
        """
        Returns (enriched_context, list_of_context_factors).
        This can elevate the baseline risk or bypass automation based on value.
        """
        context_factors = []
        enriched_context = dict(intent.context_data)
        
        # 1. Evaluate Deal Value
        deal_value = float(intent.context_data.get("deal_value", 0))
        if deal_value >= cls.VIP_THRESHOLD_VALUE:
            context_factors.append(f"High Opportunity Value (>= {cls.VIP_THRESHOLD_VALUE})")
            enriched_context["is_high_value"] = True
            
        # 2. Evaluate Customer Status
        customer_tags = intent.context_data.get("customer_tags", [])
        if "VIP" in customer_tags:
            context_factors.append("Customer is VIP")
            enriched_context["is_vip"] = True
            
        # 3. Relationship History
        returning_customer = intent.context_data.get("is_returning_customer", False)
        if returning_customer:
            context_factors.append("Returning Customer")
            
        return enriched_context, context_factors
