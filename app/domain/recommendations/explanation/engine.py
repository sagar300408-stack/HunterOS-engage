from typing import Any, Dict
from .stages.load_recommendation import load_recommendation
from .stages.validate_input import validate_input
from .stages.collect_evidence import collect_evidence
from .stages.explain_factors import explain_factors
from .stages.compose_explanation import compose_explanation
from .stages.validate_explanation import validate_explanation
from .stages.generate_result import generate_result, RecommendationExplanation

class RecommendationExplanationEngine:
    """
    Orchestrates the 7 pipeline stages for generating recommendation explanations.
    """
    
    def generate_explanation(self, recommendation_id: str, context: Dict[str, Any], workspace_id: str, identity_id: str) -> RecommendationExplanation:
        # Stage 1: Load
        data = load_recommendation(recommendation_id, context)
        
        # Stage 2: Validate Input
        data = validate_input(data, workspace_id, identity_id)
        
        # Stage 3: Collect Evidence
        data = collect_evidence(data)
        
        # Stage 4: Explain Factors
        data = explain_factors(data)
        
        # Stage 5: Compose Explanation
        data = compose_explanation(data)
        
        # Stage 6: Validate Explanation
        data = validate_explanation(data)
        
        # Stage 7: Generate Result
        result = generate_result(data)
        
        return result
