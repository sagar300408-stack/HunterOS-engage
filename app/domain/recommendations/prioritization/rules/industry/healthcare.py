from typing import Dict, Any, List
from ..base import AbstractPrioritizationRule, FactorAdjustment

class OperationalHealthcareRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "OperationalHealthcareRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        # Conservative healthcare rules: prioritize operational tasks (e.g., appointment scheduling), no diagnosis
        candidate_type = candidate.metadata.get("type") if hasattr(candidate, "metadata") else None
        
        # In a real scenario, we might actively penalize diagnosis intents
        if candidate_type == "diagnosis":
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="feasibility",
                adjustment_value=-1.0,
                reason="Medical diagnosis is strictly prohibited"
            ))
        elif candidate_type == "appointment_scheduling":
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="priority",
                adjustment_value=0.8,
                reason="Operational task prioritized in healthcare"
            ))
            
        return adjustments
