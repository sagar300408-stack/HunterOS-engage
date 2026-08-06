"""
HunterOS Engage V1 - Insight Views Package
Phase 2.2.3: Conversation Intelligence - Conversation Insight Engine
"""

from app.domain.conversations.insight.views.base import AbstractInsightView
from app.domain.conversations.insight.views.registry import (
    InsightViewRegistry,
    default_insight_view_registry,
)
from app.domain.conversations.insight.views.standard import (
    AuditInsightView,
    ExecutiveInsightView,
    OperationsInsightView,
    SalesInsightView,
    register_standard_insight_views,
)

__all__ = [
    "AbstractInsightView",
    "InsightViewRegistry",
    "default_insight_view_registry",
    "ExecutiveInsightView",
    "SalesInsightView",
    "OperationsInsightView",
    "AuditInsightView",
    "register_standard_insight_views",
]
