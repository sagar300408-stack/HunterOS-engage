from __future__ import annotations

import dataclasses
from typing import Optional

from app.domain.recommendations.models import Recommendation
from app.domain.recommendations.views.base import BaseRecommendationView

@dataclasses.dataclass(frozen=True)
class ExecutiveRecommendationView(BaseRecommendationView):
    priority: str
    business_impact: Optional[str]

    @classmethod
    def from_recommendation(cls, recommendation: Recommendation) -> ExecutiveRecommendationView:
        return cls(
            id=recommendation.id,
            type=str(recommendation.type),
            status=str(recommendation.status),
            title=recommendation.title,
            priority=str(recommendation.priority),
            business_impact=recommendation.metadata.get("business_impact") if recommendation.metadata else None,
        )
