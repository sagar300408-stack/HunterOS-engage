from typing import Any, List

class EvaluateRulesStage:
    def __init__(self, rule_registry: Any):
        """
        Args:
            rule_registry: A RecommendationDetectionRuleRegistry instance
        """
        self.rule_registry = rule_registry

    def execute(self, context: Any, diagnostics: Any) -> List[Any]:
        """
        Takes the normalized context and calls evaluate_all(context) to get a
        flat list of RecommendationCandidate objects from all registered rules.
        Records rules evaluated/matched into diagnostics.
        
        Args:
            context: The normalized RecommendationDetectionContext
            diagnostics: DetectionDiagnostics instance to record stats
            
        Returns:
            List[RecommendationCandidate]: The matched candidates
        """
        # evaluate_all should return a flat list of RecommendationCandidate
        candidates = self.rule_registry.evaluate_all(context)
        
        # Diagnostics updates
        if hasattr(diagnostics, "rules_evaluated") and hasattr(self.rule_registry, "get_all_rules"):
            diagnostics.rules_evaluated += len(self.rule_registry.get_all_rules())
            
        if hasattr(diagnostics, "rules_matched"):
            # Count unique rules that produced candidates
            matched_rules = set(getattr(c, "rule_id") for c in candidates if hasattr(c, "rule_id"))
            diagnostics.rules_matched += len(matched_rules)
            
        return candidates
