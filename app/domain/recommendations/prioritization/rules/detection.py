from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class HighConfidenceDetectionRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "HighConfidenceDetectionRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        detection_confidence = candidate.metadata.get("detection_confidence", 0.0) if hasattr(candidate, "metadata") else 0.0
        
        if detection_confidence > 0.9:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="confidence",
                adjustment_value=0.2,
                reason="High confidence detection metadata present"
            ))
        return adjustments
