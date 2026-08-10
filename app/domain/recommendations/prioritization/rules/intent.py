from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class BookingIntentRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "BookingIntentRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        intents = context.get("intents", [])
        
        if "booking" in intents:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="actionability",
                adjustment_value=0.4,
                reason="Customer shows booking intent"
            ))
        return adjustments

class NegotiationIntentRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "NegotiationIntentRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        intents = context.get("intents", [])
        
        if "negotiation" in intents:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="priority",
                adjustment_value=0.3,
                reason="Customer shows negotiation intent"
            ))
        return adjustments
