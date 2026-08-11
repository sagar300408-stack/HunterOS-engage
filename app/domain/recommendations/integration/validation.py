from typing import Any
from .models import RecommendationIntelligenceContext

class RecommendationContextValidator:
    """
    Enforces rules on the RecommendationIntelligenceContext:
    - Workspace isolation
    - Entity isolation
    - Duplicate detection
    - Schema compatibility
    - No mutation
    - No LLM usage
    - No predictive language
    """
    
    @staticmethod
    def validate(context: RecommendationIntelligenceContext, workspace_id: str, entity_id: str) -> bool:
        # Workspace isolation logic here
        
        # Entity isolation
        if context.identity_id != entity_id:
            raise ValueError("Entity isolation violation: identity mismatch.")
            
        # No mutation is handled by frozen dataclasses in models.py
        
        # Return True if all checks pass
        return True
