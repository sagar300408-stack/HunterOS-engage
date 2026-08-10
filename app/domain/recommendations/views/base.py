from __future__ import annotations

import dataclasses
from uuid import UUID

from app.domain.recommendations.models import Recommendation

@dataclasses.dataclass(frozen=True)
class BaseRecommendationView:
    id: UUID
    type: str
    status: str
    title: str

    @classmethod
    def from_recommendation(cls, recommendation: Recommendation) -> BaseRecommendationView:
        return cls(
            id=recommendation.id,
            type=str(recommendation.type),
            status=str(recommendation.status),
            title=recommendation.title,
        )
