from __future__ import annotations

import dataclasses
from typing import Optional
from datetime import datetime

from app.domain.recommendations.models import Recommendation
from app.domain.recommendations.views.base import BaseRecommendationView

@dataclasses.dataclass(frozen=True)
class OperationsRecommendationView(BaseRecommendationView):
    priority: str
    created_at: datetime

    @classmethod
    def from_recommendation(cls, recommendation: Recommendation) -> OperationsRecommendationView:
        return cls(
            id=recommendation.id,
            type=str(recommendation.type),
            status=str(recommendation.status),
            title=recommendation.title,
            priority=str(recommendation.priority),
            created_at=recommendation.created_at,
        )
