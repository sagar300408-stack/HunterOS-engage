from typing import Dict, Any, List
from ..base import AbstractPrioritizationRule, FactorAdjustment

class PropertyViewingPriorityRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "PropertyViewingPriorityRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        # Check candidate type or other metadata
        candidate_type = candidate.metadata.get("type") if hasattr(candidate, "metadata") else None
        if candidate_type == "schedule_viewing":
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="actionability",
                adjustment_value=0.6,
                reason="Property viewing is high priority in real estate"
            ))
        return adjustments
