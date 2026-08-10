from __future__ import annotations

import dataclasses
from typing import Optional

from app.domain.recommendations.models import Recommendation
from app.domain.recommendations.views.base import BaseRecommendationView

@dataclasses.dataclass(frozen=True)
class SalesRecommendationView(BaseRecommendationView):
    priority: str
    suggested_action: Optional[str]

    @classmethod
    def from_recommendation(cls, recommendation: Recommendation) -> SalesRecommendationView:
        return cls(
            id=recommendation.id,
            type=str(recommendation.type),
            status=str(recommendation.status),
            title=recommendation.title,
            priority=str(recommendation.priority),
            suggested_action=recommendation.metadata.get("suggested_action") if recommendation.metadata else None,
        )
