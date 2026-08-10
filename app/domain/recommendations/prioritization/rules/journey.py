from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class JourneyStateRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "JourneyStateRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        journey_state = context.get("journey_state")
        
        if journey_state == "decision_making":
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="relevance",
                adjustment_value=0.3,
                reason="Customer is in decision-making journey state"
            ))
        return adjustments
