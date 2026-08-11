from .base import BaseRecommendationView
from typing import List, Optional

class SalesView(BaseRecommendationView):
    """
    DTO model for sales projection.
    """
    action_items: List[str] = []
    talking_points: List[str] = []
    opportunity_value: Optional[float] = None
