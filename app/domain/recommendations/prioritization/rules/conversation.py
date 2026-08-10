from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class ConversationDeadlineRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "ConversationDeadlineRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        has_deadline = context.get("has_explicit_deadline", False)
        
        if has_deadline:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="urgency",
                adjustment_value=0.8,
                reason="Explicit conversation deadline detected"
            ))
        return adjustments
