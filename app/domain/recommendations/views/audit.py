from __future__ import annotations

import dataclasses
from datetime import datetime

from app.domain.recommendations.models import Recommendation
from app.domain.recommendations.views.base import BaseRecommendationView

@dataclasses.dataclass(frozen=True)
class AuditRecommendationView(BaseRecommendationView):
    created_at: datetime
    updated_at: datetime
    workspace_id: str
    customer_id: str

    @classmethod
    def from_recommendation(cls, recommendation: Recommendation) -> AuditRecommendationView:
        return cls(
            id=recommendation.id,
            type=str(recommendation.type),
            status=str(recommendation.status),
            title=recommendation.title,
            created_at=recommendation.created_at,
            updated_at=recommendation.updated_at,
            workspace_id=str(recommendation.workspace_id),
            customer_id=str(recommendation.customer_id),
        )
