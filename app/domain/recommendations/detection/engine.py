import uuid
from typing import List, Any

class RecommendationDetectionEngine:
    """
    RecommendationDetectionEngine is responsible for detecting recommendations
    based on a strictly deterministic rules engine without any AI/LLM predictions.
    """
    
    def detect(self, workspace_id: str, target: Any, context_provider: Any, rule_registry: Any):
        """
        Orchestrates the 6-stage pipeline (load, normalize, evaluate, validate, deduplicate, generate_result).
        """
        # 1. Load
        context = context_provider.load(workspace_id, target)
        
        # 2. Normalize
        normalized_context = context_provider.normalize(context)
        
        # 3. Evaluate
        rules = rule_registry.get_applicable_rules(normalized_context)
        candidates = []
        for rule in rules:
            rule_candidates = rule.evaluate(normalized_context)
            candidates.extend(rule_candidates)
            
        # 4. Validate
        validated = self._validate(candidates)
        
        # 5. Deduplicate
        deduplicated = self._deduplicate(validated)
        
        # 6. Generate Result
        # Assuming RecommendationDetectionResult is defined in the models module
        return self._generate_result(workspace_id, target, deduplicated)
        
    def _validate(self, candidates: List[Any]) -> List[Any]:
        valid = []
        for c in candidates:
            # Ensure triggers and evidence are present
            if c.triggers and c.evidence:
                valid.append(c)
        return valid

    def _deduplicate(self, candidates: List[Any]) -> List[Any]:
        seen = set()
        deduped = []
        for c in candidates:
            # Signature based on type and target
            sig = (c.recommendation_type, c.target_id if hasattr(c, 'target_id') else getattr(c, 'id', None))
            if sig not in seen:
                seen.add(sig)
                deduped.append(c)
        return deduped

    def _generate_result(self, workspace_id: str, target: Any, candidates: List[Any]) -> Any:
        from app.domain.recommendations.models import RecommendationDetectionResult
        return RecommendationDetectionResult(
            workspace_id=workspace_id,
            target_id=getattr(target, 'id', None),
            candidates=candidates
        )
