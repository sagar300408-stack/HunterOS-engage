from typing import Any, Dict
from pydantic import BaseModel
from typing import List

class RecommendationExplanation(BaseModel):
    recommendation_id: str
    summary: str
    reason: str
    sections: List[Dict[str, Any]]
    
    class Config:
        frozen = True  # Immutable

def generate_result(data: Dict[str, Any]) -> RecommendationExplanation:
    """
    Stage 7: Produces immutable RecommendationExplanation.
    """
    sections = [s.dict() for s in data.get('explanation_sections', [])]
    
    return RecommendationExplanation(
        recommendation_id=data['recommendation_id'],
        summary=data['composed_summary'],
        reason=data['composed_reason'],
        sections=sections
    )
