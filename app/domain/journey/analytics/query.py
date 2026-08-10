"""
HunterOS Engage V1 — Journey Analytics
Phase 2.4.4: Analytics Query Engine

Read-only descriptive query operations over persisted analytics results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import uuid

from app.domain.journey.analytics.models import (
    JourneyAnalyticsResult,
    JourneyDistributionMetrics,
    StageAnalytics,
    TransitionSummaryMetrics,
    JourneyFunnelMetrics,
    JourneyDurationMetrics,
    StageResidencyAnalytics,
    MaturityAnalytics,
    MomentumAnalytics,
    StabilityAnalytics,
    VelocityAnalytics,
    JourneyHealthAnalytics,
    ProgressionPatternAnalytics,
    ObservedStageOutcomeAnalytics,
    JourneyTrendAnalytics,
    JourneyCohortComparison,
)
from app.domain.journey.analytics.repository import JourneyAnalyticsReadRepository


class JourneyAnalyticsQueryEngine:
    """Read-only query engine over persisted JourneyAnalyticsResults."""

    def __init__(self, repository: JourneyAnalyticsReadRepository) -> None:
        self._repo = repository

    def _get_latest(self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None) -> Optional[JourneyAnalyticsResult]:
        return self._repo.get_latest_result(workspace_id, journey_type)

    def get_overview(self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None) -> Optional[JourneyAnalyticsResult]:
        return self._get_latest(workspace_id, journey_type)

    def get_distribution(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyDistributionMetrics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.distribution if result else None

    def get_stage_analytics(
        self, workspace_id: Union[uuid.UUID, str], stage: Optional[str] = None, journey_type: Optional[str] = None
    ) -> Optional[Dict[str, StageAnalytics]]:
        result = self._get_latest(workspace_id, journey_type)
        if result is None:
            return None
        if stage:
            sa = result.stage_analytics.get(stage)
            return {stage: sa} if sa else {}
        return result.stage_analytics

    def get_transition_analytics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[TransitionSummaryMetrics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.transition_metrics if result else None

    def get_funnel(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyFunnelMetrics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.funnel if result else None

    def get_duration_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyDurationMetrics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.duration_metrics if result else None

    def get_residency_metrics(
        self, workspace_id: Union[uuid.UUID, str], stage: Optional[str] = None, journey_type: Optional[str] = None
    ) -> Optional[Dict[str, StageResidencyAnalytics]]:
        result = self._get_latest(workspace_id, journey_type)
        if result is None:
            return None
        if stage:
            ra = result.residency_analytics.get(stage)
            return {stage: ra} if ra else {}
        return result.residency_analytics

    def get_maturity_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[MaturityAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.maturity_analytics if result else None

    def get_momentum_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[MomentumAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.momentum_analytics if result else None

    def get_stability_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[StabilityAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.stability_analytics if result else None

    def get_velocity_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[VelocityAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.velocity_analytics if result else None

    def get_health_metrics(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyHealthAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.health_analytics if result else None

    def get_outcome_metrics(
        self, workspace_id: Union[uuid.UUID, str], stage: Optional[str] = None, journey_type: Optional[str] = None
    ) -> Optional[Dict[str, ObservedStageOutcomeAnalytics]]:
        result = self._get_latest(workspace_id, journey_type)
        if result is None:
            return None
        if stage:
            oa = result.outcome_analytics.get(stage)
            return {stage: oa} if oa else {}
        return result.outcome_analytics

    def get_trends(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[JourneyTrendAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.trend_analytics if result else None

    def get_progression_patterns(
        self, workspace_id: Union[uuid.UUID, str], journey_type: Optional[str] = None
    ) -> Optional[ProgressionPatternAnalytics]:
        result = self._get_latest(workspace_id, journey_type)
        return result.progression_patterns if result else None


default_analytics_query_engine: JourneyAnalyticsQueryEngine = JourneyAnalyticsQueryEngine(
    repository=default_analytics_repository
)
