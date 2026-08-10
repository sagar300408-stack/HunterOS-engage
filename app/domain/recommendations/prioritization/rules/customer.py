from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class CustomerConstraintRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "CustomerConstraintRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        constraints = context.get("customer_constraints", {})
        
        if constraints.get("budget_strict", False):
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="feasibility",
                adjustment_value=-0.5,
                reason="Customer has strict budget constraints affecting feasibility"
            ))
        return adjustments
