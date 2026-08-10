"""
HunterOS Engage V1 — Customer Journey Intelligence
Phase 2.4.4: Journey Analytics Engine

Descriptive, deterministic, read-only analytics aggregating patterns
across journeys, stages, transitions, maturity, momentum, stability,
residency, velocity, and historical outcomes.

STRICT ARCHITECTURAL INVARIANTS:
- DESCRIPTIVE ONLY: Never predicts future stages.
- NO RECOMMENDATIONS: Does not generate next-best-actions.
- NO MUTATIONS: Reads journey state; never writes it.
- WORKSPACE-SCOPED: Cross-workspace aggregation is forbidden.
- DETERMINISTIC: Same inputs produce same outputs.
"""

from app.domain.journey.analytics.models import (
    JourneyAnalyticsResult,
    JourneyDistributionMetrics,
    StageAnalytics,
    TransitionAnalytics,
    JourneyFunnelMetrics,
    JourneyFunnelStageMetrics,
    JourneyDurationMetrics,
    StageResidencyAnalytics,
    MaturityAnalytics,
    MomentumAnalytics,
    StabilityAnalytics,
    VelocityAnalytics,
    JourneyHealthAnalytics,
    ProgressionPatternAnalytics,
    ObservedStageOutcomeAnalytics,
    JourneyTrendPoint,
    JourneyTrendAnalytics,
    JourneyCohortDefinition,
    JourneyCohortComparison,
    JourneyAnalyticsDiagnostics,
    JourneyAnalyticsProvenance,
    AnalyticsObservationWindow,
    AnalyticsScope,
    ResidencyCategory,
    ProgressionPattern,
    TrendGranularity,
)

__all__ = [
    "JourneyAnalyticsResult",
    "JourneyDistributionMetrics",
    "StageAnalytics",
    "TransitionAnalytics",
    "JourneyFunnelMetrics",
    "JourneyFunnelStageMetrics",
    "JourneyDurationMetrics",
    "StageResidencyAnalytics",
    "MaturityAnalytics",
    "MomentumAnalytics",
    "StabilityAnalytics",
    "VelocityAnalytics",
    "JourneyHealthAnalytics",
    "ProgressionPatternAnalytics",
    "ObservedStageOutcomeAnalytics",
    "JourneyTrendPoint",
    "JourneyTrendAnalytics",
    "JourneyCohortDefinition",
    "JourneyCohortComparison",
    "JourneyAnalyticsDiagnostics",
    "JourneyAnalyticsProvenance",
    "AnalyticsObservationWindow",
    "AnalyticsScope",
    "ResidencyCategory",
    "ProgressionPattern",
    "TrendGranularity",
]
