from __future__ import annotations

from app.domain.recommendations.views.base import BaseRecommendationView
from app.domain.recommendations.views.executive import ExecutiveRecommendationView
from app.domain.recommendations.views.sales import SalesRecommendationView
from app.domain.recommendations.views.operations import OperationsRecommendationView
from app.domain.recommendations.views.audit import AuditRecommendationView

__all__ = [
    "BaseRecommendationView",
    "ExecutiveRecommendationView",
    "SalesRecommendationView",
    "OperationsRecommendationView",
    "AuditRecommendationView",
]
