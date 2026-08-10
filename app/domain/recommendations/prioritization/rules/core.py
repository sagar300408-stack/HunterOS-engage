from typing import Dict, Any, List
from .base import AbstractPrioritizationRule, FactorAdjustment

class TimeSensitiveRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "TimeSensitiveRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        is_time_sensitive = candidate.metadata.get("is_time_sensitive", False) if hasattr(candidate, "metadata") else False
        
        if is_time_sensitive:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="urgency",
                adjustment_value=0.5,
                reason="Candidate is marked as time sensitive"
            ))
        return adjustments

class ExplicitCustomerRequestRule(AbstractPrioritizationRule):
    @property
    def rule_name(self) -> str:
        return "ExplicitCustomerRequestRule"

    def evaluate(self, candidate: Any, context: Dict[str, Any], factor_results: Dict[str, float]) -> List[FactorAdjustment]:
        adjustments = []
        is_explicit_request = candidate.metadata.get("is_explicit_request", False) if hasattr(candidate, "metadata") else False
        
        if is_explicit_request:
            adjustments.append(FactorAdjustment(
                rule_name=self.rule_name,
                factor_name="relevance",
                adjustment_value=1.0,
                reason="Candidate addresses an explicit customer request"
            ))
        return adjustments
