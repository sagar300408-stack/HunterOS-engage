from .base import BaseRecommendationView
from typing import Optional

class ExecutiveView(BaseRecommendationView):
    """
    DTO model for executive projection.
    """
    summary: Optional[str] = None
    confidence_score: Optional[float] = None
    business_impact: Optional[str] = None
